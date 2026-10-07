"""
answer_synthesizer.py — Síntesis de respuesta en español
========================================================
Convierte los resultados crudos de SQL en una respuesta en
lenguaje natural en español, citando los datos concretos.

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os
import math
import httpx

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from src.layer1_schema.models import SchemaContext
from src.layer2_agent.sql_validator import SQLResult

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "glm4:9b")

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
    ctx: SchemaContext, result: SQLResult, history: list[dict] | None = None
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

    user_msg = _format_history(ctx.query, history) + SYNTH_USER_TEMPLATE.format(
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
        # Fallback: respuesta básica sin LLM
        return (f"Se encontraron {result.row_count} resultados. "
                f"Columnas: {', '.join(result.columns)}. "
                f"Primer resultado: {result.rows[0] if result.rows else 'N/A'}")


def synthesize_hybrid(
    ctx: SchemaContext,
    sql_result: SQLResult | None,
    rag_result,
    history: list[dict] | None = None,
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
            return synthesize_answer(ctx, sql_result, history)
        return ("No encontré información para responder esa pregunta, ni por consulta "
                "estructurada ni por búsqueda semántica en el corpus.")

    sql_text = _format_results(sql_result) if has_sql else "(sin resultados estructurados)"
    rag_text = format_rag_context(rag_result) if has_rag else "(sin artículos relevantes)"

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.3,
    )

    user_msg = _format_history(ctx.query, history) + HYBRID_USER_TEMPLATE.format(
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
    except Exception:
        # Fallback: si falla la integración, devolver al menos lo que haya
        if has_sql:
            return synthesize_answer(ctx, sql_result, history)
        return format_rag_context(rag_result)


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

    except Exception:
        # Si el juez falla, no bloquear: aceptar la respuesta
        return True, "reflexión omitida (error del evaluador)"


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
