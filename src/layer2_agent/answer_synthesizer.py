"""
answer_synthesizer.py — Síntesis de respuesta en español
========================================================
Convierte los resultados crudos de SQL en una respuesta en
lenguaje natural en español, citando los datos concretos.

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os
import re
import math
import traceback
from datetime import datetime
from pathlib import Path

import httpx

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from src.layer1_schema.models import SchemaContext
from src.layer2_agent.sql_validator import SQLResult

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "glm4:9b")

ERROR_LOG = Path(__file__).resolve().parents[2] / "logs" / "agent_errors.log"


def log_error(where: str, exc: Exception) -> None:
    """Registra una excepción que el agente se tragaba para usar un respaldo (antes se perdía en silencio)."""
    print(f"      [ERROR registrado] {where}: {type(exc).__name__}: {exc}", flush=True)
    try:
        ERROR_LOG.parent.mkdir(exist_ok=True)
        with ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} · {where}\n{traceback.format_exc()}\n")
    except OSError:
        pass

SYNTH_SYSTEM_PROMPT = """Eres un asistente experto en bibliometría. Tu trabajo es responder
preguntas sobre un corpus académico de forma clara y concisa en español.

REGLAS:
1. Responde en español, de forma natural y directa.
2. Cita los datos concretos de los resultados (nombres, números, años).
3. Si hay un ranking, presenta los primeros resultados de forma legible.
4. No inventes datos — usa SOLO lo que aparece en los resultados.
5. Si los resultados están vacíos, dilo claramente.
6. Sé conciso — máximo 3-4 oraciones para respuestas simples.
7. Para rankings, usa formato de lista numerada."""

SYNTH_USER_TEMPLATE = """Responde esta pregunta usando los resultados de la consulta SQL.

PREGUNTA DEL USUARIO: {query}

SQL EJECUTADO:
{sql}

RESULTADOS ({row_count} filas):
{results}

RESPUESTA EN ESPAÑOL:"""


# ── Artículos principales vs referencias (búsqueda semántica) ─────────────────

# Juez aparte (no dentro del prompt de respuesta: con glm4, pedir "responde solo X si nada sirve"
# volvía las respuestas mínimas). Decide si hay que pasar a buscar en las referencias citadas.
JUDGE_SYSTEM_PROMPT = """Decides si una lista de artículos científicos contiene información que
responde una pregunta. Responde solo SI o NO."""


def articles_answer_question(query: str, rag_result) -> bool:
    """True si al menos uno de los artículos recuperados responde la pregunta (ante la duda, True)."""
    if not rag_result or not getattr(rag_result, "articles", None):
        return False
    listing = "\n".join(
        f"- {a.get('title', '')}: {(a.get('abstract') or '')[:300]}" for a in rag_result.articles)
    llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0.0)
    try:
        verdict = llm.invoke([
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": f"PREGUNTA: {query}\n\nARTÍCULOS:\n{listing}\n\n¿Alguno responde la pregunta? (SI/NO):"},
        ]).content.strip().upper()
    except Exception as e:
        log_error("juez de artículos", e)
        return True
    return not verdict.startswith("NO")


# ── Prompts para canal hybrid (SQL + RAG) ─────────────────────────────────────

HYBRID_SYSTEM_PROMPT = """Eres un asistente experto en bibliometría. Respondes preguntas
combinando DOS fuentes: (1) resultados exactos de una consulta SQL y (2) artículos
recuperados por búsqueda semántica sobre sus abstracts.

REGLAS:
1. Responde en español, de forma clara y concisa.
2. Usa los datos del SQL para las cifras exactas (conteos, rankings, filtros).
3. Usa los artículos semánticos para el contexto temático (de qué tratan).
4. Integra ambas fuentes en una sola respuesta coherente — no las listes por separado.
5. No inventes datos: usa SOLO lo que aparece en las fuentes.
6. Si una fuente está vacía, apóyate en la otra."""

HYBRID_USER_TEMPLATE = """Responde esta pregunta combinando las dos fuentes.

PREGUNTA DEL USUARIO: {query}

— FUENTE 1: RESULTADOS SQL ({row_count} filas) —
SQL: {sql}
{sql_results}

— FUENTE 2: ARTÍCULOS POR BÚSQUEDA SEMÁNTICA —
{rag_context}

RESPUESTA EN ESPAÑOL:"""

# ── Prompts para preguntas de seguimiento sobre artículos ya mostrados ───────

FOLLOWUP_SYSTEM_PROMPT = """Eres un asistente experto en bibliometría. El usuario pregunta por
artículos que tú ya le mostraste en tu respuesta anterior.

REGLAS:
1. Responde en español, de forma clara y concisa.
2. La respuesta principal se basa SOLO en los ARTÍCULOS DE TU RESPUESTA ANTERIOR: elige,
   compara o describe esos artículos, no otros. Nunca presentes una SUGERENCIA como si fuera
   uno de los artículos anteriores.
3. Si ninguno de los artículos anteriores trata el tema por el que pregunta el usuario, dilo
   claramente ("ninguno de esos artículos trata de ..."). No fuerces ni inventes una relación;
   si acaso, indica cuál es el menos alejado y por qué la relación es débil.
4. Después, en un párrafo aparte que empiece con "Sugerencias adicionales:", puedes mencionar
   como máximo 2 de las SUGERENCIAS si de verdad tienen que ver con lo que pregunta el usuario,
   aclarando que no estaban en la lista anterior. Si ninguna aporta, omite ese párrafo.
5. Si una sugerencia es una referencia citada, dilo: no es un artículo principal del corpus.
6. No inventes datos: usa solo lo que aparece en los artículos."""

FOLLOWUP_USER_TEMPLATE = """PREGUNTA DEL USUARIO: {query}

— ARTÍCULOS DE TU RESPUESTA ANTERIOR (responde con estos) —
{previous}

— SUGERENCIAS (no estaban en la lista anterior; solo como sugerencia) —
{suggestions}

RESPUESTA EN ESPAÑOL:"""


# ── Prompt para auto-reflexión sobre la respuesta ─────────────────────────────

REFLECT_SYSTEM_PROMPT = """Eres un evaluador crítico de respuestas de un sistema bibliométrico.
Tu trabajo es decidir si la respuesta generada REALMENTE responde la pregunta del usuario,
usando los datos disponibles.

Considera INADECUADA una respuesta si:
- No responde lo que se preguntó (responde otra cosa).
- Está vacía, es genérica o evasiva ("no hay datos" cuando sí los hay).
- Contradice los resultados de la consulta.
- Le faltan elementos clave que la pregunta pedía (p.ej. un ranking sin el orden pedido).

Responde EXACTAMENTE en este formato:
VEREDICTO: ADECUADA|INADECUADA
MOTIVO: <una frase explicando por qué>"""

REFLECT_USER_TEMPLATE = """Evalúa si esta respuesta es adecuada.

PREGUNTA DEL USUARIO: {query}

SQL EJECUTADO: {sql}

RESULTADOS ({row_count} filas):
{results}

RESPUESTA GENERADA:
{answer}

EVALUACIÓN:"""


def _get_embedding(text: str) -> list[float]:
    """Obtiene el embedding de un texto usando el modelo de Ollama."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"), "prompt": text},
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
    except Exception:
        return []


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calcula la similitud coseno entre dos vectores."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _get_relevant_history(query: str, history: list[dict], top_k: int = 2) -> list[dict]:
    """
    Busca semánticamente los turnos más relevantes del historial.
    """
    if not history:
        return []

    query_emb = _get_embedding(query)
    if not query_emb:
        return []

    scored_turns = []
    for turn in history:
        # Vectorizamos la pregunta del turno para ver si el tema coincide
        text = f"Usuario: {turn.get('question', '')}\nAsistente: {turn.get('answer', '')}"
        turn_emb = _get_embedding(text)
        if turn_emb:
            score = _cosine_similarity(query_emb, turn_emb)
            scored_turns.append((score, turn))

    # Ordenar por similitud y tomar top_k
    scored_turns.sort(key=lambda x: x[0], reverse=True)
    return [turn for score, turn in scored_turns[:top_k]]


def _format_history(query: str, history: list[dict] | None, max_turns: int = 3) -> str:
    """
    Formatea el contexto de la conversación usando un enfoque híbrido:
    1. Los últimos turnos (memoria a corto plazo para anáforas).
    2. Turnos semánticamente relevantes (RAG sobre historial).
    """
    if not history:
        return ""

    # 1. Memoria a corto plazo (últimos N turnos)
    recent = history[-max_turns:]

    # 2. RAG sobre historial (buscar turnos relevantes que no estén ya en los recientes)
    # Solo buscamos en el resto del historial si hay más turnos que los recientes
    relevant = []
    if len(history) > max_turns:
        old_history = history[:-max_turns]
        relevant = _get_relevant_history(query, old_history, top_k=2)

    lines = []
    if relevant:
        lines.append("CONVERSACIÓN RELEVANTE (recuperada semánticamente):")
        for turn in relevant:
            q = (turn.get("question") or "").strip()
            a = (turn.get("answer") or "").strip()
            if q: lines.append(f"  Usuario: {q}")
            if a: lines.append(f"  Asistente: {a}")
        lines.append("")

    if recent:
        lines.append("CONVERSACIÓN RECIENTE:")
        for turn in recent:
            q = (turn.get("question") or "").strip()
            a = (turn.get("answer") or "").strip()
            if q: lines.append(f"  Usuario: {q}")
            if a: lines.append(f"  Asistente: {a}")

    return "\n".join(lines) + "\n\n" if lines else ""



def _format_results(result: SQLResult, max_rows: int = 15) -> str:
    """Formatea los resultados SQL como texto tabular para el prompt."""
    if not result.rows:
        return "(sin resultados)"

    lines = []
    # Encabezado
    lines.append(" | ".join(result.columns))
    lines.append("-" * len(lines[0]))

    # Filas
    for row in result.rows[:max_rows]:
        values = [str(row.get(col, "")) for col in result.columns]
        lines.append(" | ".join(values))

    if result.row_count > max_rows:
        lines.append(f"... ({result.row_count - max_rows} filas más)")

    return "\n".join(lines)


def synthesize_answer(
    ctx: SchemaContext, result: SQLResult, history: list[dict] | None = None, note: str = ""
) -> str:
    """
    Genera una respuesta en español a partir de los resultados SQL.

    Parámetros
    ----------
    ctx : SchemaContext
        Contexto original con la query del usuario.
    result : SQLResult
        Resultado de la ejecución SQL.
    history : list[dict] | None
        Turnos previos de la conversación {"question", "answer"} para dar
        continuidad multi-turno.
    note : str
        Aviso para el LLM que va antes de la plantilla (p. ej. que los resultados
        salen de las referencias citadas y no de los artículos principales).

    Retorna
    -------
    str
        Respuesta en lenguaje natural en español.
    """
    # Si el SQL falló, dar respuesta de error
    if not result.success:
        return (f"Lo siento, no pude obtener los resultados. "
                f"Hubo un error al consultar la base de datos: {result.error}")

    # Si no hay resultados
    if result.row_count == 0:
        return ("La consulta no retornó resultados. Esto puede significar que "
                "no hay datos que coincidan con los criterios de búsqueda en el corpus.")

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.3,  # Un poco de variabilidad para respuestas naturales
    )

    results_text = _format_results(result)

    user_msg = _format_history(ctx.query, history) + note + SYNTH_USER_TEMPLATE.format(
        query=ctx.query,
        sql=result.query,
        row_count=result.row_count,
        results=results_text,
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": SYNTH_SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ])
        return response.content.strip()

    except Exception as e:
        log_error("synthesize_answer", e)
        # Fallback: respuesta básica sin LLM
        return (f"Se encontraron {result.row_count} resultados. "
                f"Columnas: {', '.join(result.columns)}. "
                f"Primer resultado: {result.rows[0] if result.rows else 'N/A'}")


def synthesize_hybrid(
    ctx: SchemaContext,
    sql_result: SQLResult | None,
    rag_result,
    history: list[dict] | None = None,
    note: str = "",
) -> str:
    """
    Sintetiza una respuesta combinando resultados SQL (cifras exactas) y
    artículos recuperados por búsqueda semántica (contexto temático).

    Se usa en el canal `hybrid`.

    Parámetros
    ----------
    ctx : SchemaContext
        Contexto de la Capa 1.
    sql_result : SQLResult | None
        Resultado de la consulta SQL (puede ser None o fallido).
    rag_result : RAGResult | None
        Resultado de la búsqueda semántica (Capa 3).
    history : list[dict] | None
        Turnos previos de la conversación.

    Retorna
    -------
    str
        Respuesta integrada en español.
    """
    from src.layer3_rag.retriever import format_rag_context

    has_sql = bool(sql_result and sql_result.success and sql_result.row_count > 0)
    has_rag = bool(rag_result and getattr(rag_result, "success", False)
                   and rag_result.articles)

    # Si ninguna fuente aportó nada, delegar al sintetizador SQL (maneja errores/vacíos)
    if not has_sql and not has_rag:
        if sql_result is not None:
            return synthesize_answer(ctx, sql_result, history, note=note)
        return ("No encontré información para responder esa pregunta, ni por consulta "
                "estructurada ni por búsqueda semántica en el corpus.")

    sql_text = _format_results(sql_result) if has_sql else "(sin resultados estructurados)"
    rag_text = format_rag_context(rag_result) if has_rag else "(sin artículos relevantes)"

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.3,
    )

    user_msg = _format_history(ctx.query, history) + note + HYBRID_USER_TEMPLATE.format(
        query=ctx.query,
        row_count=sql_result.row_count if has_sql else 0,
        sql=sql_result.query if sql_result else "(sin SQL)",
        sql_results=sql_text,
        rag_context=rag_text,
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": HYBRID_SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ])
        return response.content.strip()
    except Exception as e:
        log_error("synthesize_hybrid", e)
        # Fallback: si falla la integración, devolver al menos lo que haya
        if has_sql:
            return synthesize_answer(ctx, sql_result, history)
        return format_rag_context(rag_result)


def _authors_and_countries(srs: list[str], db_path: str | None) -> dict[str, tuple[str, str]]:
    """Autores y países de cada artículo, para responder seguimientos sin volver a la BD."""
    if not db_path or not srs:
        return {}
    import sqlite3
    conn = sqlite3.connect(db_path)
    out = {}
    for sr in srs:
        authors = [r[0] for r in conn.execute(
            "SELECT DISTINCT au.AuthorName FROM ArticleAuthor aa JOIN Author au ON au.AuthorID = aa.AuthorID "
            "WHERE aa.SR = ? ORDER BY aa.AuthorOrder", (sr,)) if r[0]]
        countries = [r[0] for r in conn.execute(
            "SELECT DISTINCT Country FROM Affiliation WHERE SR = ? AND Country IS NOT NULL", (sr,))]
        out[sr] = ("; ".join(authors[:8]), ", ".join(countries))
    conn.close()
    return out


def synthesize_followup(ctx: SchemaContext, previous: list[dict], suggestions, db_path: str | None,
                        history: list[dict] | None = None) -> str:
    """
    Responde una pregunta de seguimiento sobre artículos que el agente ya mostró.

    Parámetros
    ----------
    previous : list[dict]
        Artículos del turno anterior, ya enriquecidos con la BD (título, abstract, año…).
    suggestions : RAGResult
        Búsqueda semántica que excluye los artículos anteriores; solo se ofrecen como sugerencia.
    """
    from src.layer3_rag.retriever import format_rag_context, RAGResult

    extra = _authors_and_countries([a["SR"] for a in previous], db_path)
    for a in previous:
        a["authors"], a["countries"] = extra.get(a["SR"], ("", ""))
    previous_text = format_rag_context(RAGResult(query=ctx.query, articles=previous, success=True))
    has_sugg = bool(suggestions and getattr(suggestions, "success", False) and suggestions.articles)
    sugg_text = format_rag_context(suggestions) if has_sugg else "(sin sugerencias)"
    # "Sugerencia N" y no "Artículo N": evita que el modelo las confunda con los artículos anteriores
    sugg_text = re.sub(r"--- Artículo \d+", "--- Sugerencia", sugg_text)

    llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0.3)
    user_msg = _format_history(ctx.query, history) + FOLLOWUP_USER_TEMPLATE.format(
        query=ctx.query, previous=previous_text, suggestions=sugg_text)
    try:
        response = llm.invoke([
            {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ])
        return response.content.strip()
    except Exception as e:
        log_error("synthesize_followup", e)
        return previous_text


def reflect_on_answer(
    ctx: SchemaContext,
    result: SQLResult | None,
    answer: str,
    history: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Auto-reflexión: juzga si `answer` responde realmente la pregunta del usuario,
    más allá de que el SQL haya ejecutado sin error.

    Retorna
    -------
    (adequate, critique) : tuple[bool, str]
        adequate=True si la respuesta es adecuada; critique con el motivo.
        Ante cualquier fallo del juez, retorna (True, ...) para no bloquear el flujo.
    """
    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.0,
    )

    results_text = _format_results(result) if result else "(sin resultados)"
    user_msg = REFLECT_USER_TEMPLATE.format(
        query=ctx.query,
        sql=result.query if result else "(sin SQL)",
        row_count=result.row_count if result else 0,
        results=results_text,
        answer=answer,
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": REFLECT_SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ])
        text = response.content.strip()
        upper = text.upper()
        # Buscar el veredicto; "INADECUADA" tiene prioridad sobre "ADECUADA"
        adequate = "INADECUADA" not in upper
        # Extraer el motivo si viene
        critique = ""
        for ln in text.splitlines():
            if ln.upper().startswith("MOTIVO:"):
                critique = ln.split(":", 1)[1].strip()
                break
        return adequate, critique or text

    except Exception as e:
        log_error("reflect_on_answer", e)
        # Si el juez falla, no bloquear: aceptar la respuesta
        return True, "reflexión omitida (error del evaluador)"


# ── Respuestas de la Capa 5 (redes, comunidades, series de tiempo) ───────────

NETWORK_SYSTEM_PROMPT = """Eres un asistente experto en bibliometría y análisis de redes científicas.
Respondes preguntas sobre redes de coautoría y de citas, frentes de investigación y tendencias de
un corpus académico. Todas las cifras ya fueron calculadas: tú solo las explicas.

REGLAS:
1. Responde en español, de forma clara. Puedes traducir las palabras clave entre paréntesis.
2. Usa SOLO las cifras del ANÁLISIS: no calcules, no redondees de otra forma, no inventes.
3. Explica en una frase el método cuando ayude a entender el resultado (qué es un frente, un autor
   puente, un pronóstico ARIMA).
4. Si el análisis dice "Ninguno", "N/D" o que algo no se calcula, dilo tal cual y por qué.
5. Distingue tendencias significativas de no significativas y "EMERGENTE" de "SEÑAL DÉBIL".
   Los pronósticos van siempre con su intervalo de confianza.
6. Responde a lo que se pregunta: no repitas todo el análisis."""

NETWORK_USER_TEMPLATE = """PREGUNTA DEL USUARIO: {query}

ANÁLISIS ({kind}):
{context}

RESPUESTA EN ESPAÑOL:"""


def synthesize_network(query: str, kind: str, context: str, history: list[dict] | None = None) -> str:
    """Redacta la respuesta de una pregunta de redes, comunidades o tendencias a partir del análisis ya calculado."""
    llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0.2)
    kind_label = {"graph": "redes de coautoría y acoplamiento", "community": "frentes de investigación y temas",
                  "forecast": "series de tiempo y tendencias"}.get(kind, kind)
    user_msg = _format_history(query, history) + NETWORK_USER_TEMPLATE.format(
        query=query, kind=kind_label, context=context)
    try:
        response = llm.invoke([
            {"role": "system", "content": NETWORK_SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ])
        return response.content.strip()
    except Exception as e:
        log_error("synthesize_network", e)
        return context


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.layer1_schema.schema_linker import link_schema
    from src.layer2_agent.refiner import generate_and_validate

    import argparse
    parser = argparse.ArgumentParser(description="Pipeline completo: query → SQL → respuesta")
    parser.add_argument("--query", "-q", type=str, required=True)
    args = parser.parse_args()

    print(f"\n  Query: '{args.query}'\n")

    # Paso 1
    print("  [1] Schema linking...")
    ctx = link_schema(args.query)
    print(f"      Canal: {ctx.query_type} | Tablas: {ctx.relevant_tables}")

    # Paso 2
    print("  [2] Generando y validando SQL...")
    result = generate_and_validate(ctx)

    if result.success:
        print(f"      ✓ {result.row_count} filas en {result.execution_time_ms}ms")
        print(f"      SQL: {result.query}")
    else:
        print(f"      ✗ Error: {result.error}")

    # Paso 3
    print("  [3] Sintetizando respuesta...")
    answer = synthesize_answer(ctx, result)
    print(f"\n{'='*60}")
    print(f"  RESPUESTA:\n")
    print(f"  {answer}")
    print(f"\n{'='*60}")
