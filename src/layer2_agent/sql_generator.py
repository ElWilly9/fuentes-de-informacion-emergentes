"""
sql_generator.py — Generación de SQL con LLM
=============================================
Recibe un SchemaContext de la Capa 1 y genera una consulta SQL
usando el LLM (Ollama) con un prompt especializado.

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os
import re

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from src.layer1_schema.models import SchemaContext
from src.layer2_agent.sql_validator import SQLResult

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "glm4:9b")
# Modelo aparte para generar y corregir SQL; el resto del agente usa OLLAMA_MODEL. qwen2.5-coder fue el mejor generando
# SQL solo (Spider 0,797, BIRD 0,493) y glm4 el mejor redactando. Ver CLAUDE.md, comparación de modelos.
OLLAMA_SQL_MODEL = os.getenv("OLLAMA_SQL_MODEL", "qwen2.5-coder:7b")
# simple: prompt corto en inglés, como el del modelo solo en Spider/BIRD (el coder pierde 8-9 puntos con el del agente).
# ddl: además, esquema en CREATE TABLE y pregunta en el formato del modelo solo; las pistas del corpus van como comentarios.
SQL_PROMPT = os.getenv("SQL_PROMPT", "ddl")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))  # tope de tokens de salida: corta los bucles de texto basura de glm4
# Contexto fijo en todas las llamadas (si solo algunas lo cambian, Ollama recarga el modelo). Sin fijarlo, el
# valor por defecto depende de la versión de Ollama y de la VRAM (4.096 en una GPU de 12 GB).
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# ── Prompt template ───────────────────────────────────────────────────────────

SQL_SYSTEM_PROMPT = """Eres un experto en SQL que genera consultas para SQLite.
Tu trabajo es convertir preguntas en lenguaje natural sobre una base de datos
en consultas SQL correctas y eficientes.

REGLAS ESTRICTAS:
1. Genera SOLO la consulta SQL, sin explicaciones, sin markdown, sin texto extra.
2. Usa SOLO las tablas y columnas que se te proporcionan — NO inventes columnas.
3. Usa JOINs basándote SOLO en las foreign keys proporcionadas.
4. Para conteos usa COUNT(1) o COUNT(*). Para contar elementos distintos usa COUNT(DISTINCT columna).
5. Si la pregunta pide un ranking, usa ORDER BY ... DESC.
6. Responde ÚNICAMENTE con el SQL, nada más.{domain_rules}"""

SIMPLE_SYSTEM_PROMPT = ("You are an expert in SQLite. Write a single SQLite query that answers the question. "
                        "Reply with the SQL only, without explanation or markdown.")

# Reglas del corpus bibliométrico. Solo se añaden si el esquema es el nuestro (tabla article):
# en otras BD (Spider) el LIMIT 10 por defecto, los CAST y el LIKE causaron 36 de 53 pérdidas.
BIBLIO_RULES = """

REGLAS DEL CORPUS BIBLIOMÉTRICO:
7. La base de datos es un corpus bibliométrico; las preguntas llegan en español.
8. Para texto, usa LIKE con % para búsquedas parciales.
9. Siempre incluye LIMIT si la pregunta pide "top", "más", "mejores" (default LIMIT 10).
10. cited_by puede ser TEXT — usa CAST(cited_by AS INTEGER) para ordenar numéricamente.
11. year puede ser TEXT — usa CAST(year AS INTEGER) para filtros numéricos.
12. "Cuántas citas" se responde con la columna cited_by (su valor, o SUM(cited_by) para varios artículos),
    nunca con COUNT.
13. Para contar los artículos de un valor extremo (el primer año, el año con más citas…) calcula ese valor en
    una subconsulta: WHERE year = (SELECT MIN(year) FROM article). MIN(...) y COUNT(*) en el mismo SELECT
    cuentan todo el corpus.
14. No añadas filtros por tema, palabra clave o tipo de documento que la pregunta no pida: si pregunta por un país,
    un autor, un año o una revista, filtra solo por eso.
15. Si la pregunta pide de qué trata, qué estudia o qué propone un artículo, incluye title y abstract en el SELECT."""


# Reglas que solo se añaden cuando la pregunta las necesita (así el prompt del resto de preguntas no cambia).
CONDITIONAL_RULES = [
    (r"(m[aá]xim|mayor|menor|promedio|media).{0,25}(n[uú]mero|cantidad)\s+de\s+\w+|m[aá]s autores|cu[aá]ntos autores por",
     "16. No anides agregados: MAX(COUNT(...)) es inválido en SQLite. Calcula el máximo de un conteo con una subconsulta, "
     "p. ej. SELECT MAX(n) FROM (SELECT COUNT(DISTINCT authorid) AS n FROM articleauthor GROUP BY sr)."),
    (r"un solo autor|[uú]nico autor|solo (tiene|tienen|con) (un|1) autor|m[aá]s autores|menos autores|n[uú]mero de autores",
     "18. Los autores de un artículo se cuentan agrupando articleauthor por sr: artículos con un solo autor = "
     "SELECT COUNT(*) FROM (SELECT sr FROM articleauthor GROUP BY sr HAVING COUNT(DISTINCT authorid) = 1). "
     "El artículo con más autores: SELECT sr FROM articleauthor GROUP BY sr ORDER BY COUNT(DISTINCT authorid) DESC LIMIT 1. "
     "Para mostrar título o abstract, filtra article con sr IN (esa subconsulta)."),
    (r"porcentaje|proporci[oó]n|qu[eé] % |fracci[oó]n",
     "17. Un porcentaje del total se calcula dividiendo entre una subconsulta escalar: "
     "100.0 * (SELECT MAX(cited_by) FROM article WHERE ismainarticle = 1) / (SELECT SUM(cited_by) FROM article WHERE ismainarticle = 1). "
     "Un SUM(...) en la misma fila que cited_by solo suma esa fila y da 100 %."),
]


def conditional_rules(ctx: SchemaContext) -> str:
    q = (ctx.query or "").lower()
    extra = [r for pat, r in CONDITIONAL_RULES if re.search(pat, q)]
    return ("\n" + "\n".join(extra)) if extra else ""


def is_bibliometric(ctx: SchemaContext) -> bool:
    return any(t.lower() == "article" for t in ctx.relevant_tables)


def system_prompt(ctx: SchemaContext, style: str | None = None) -> str:
    style = style or SQL_PROMPT
    rules = (BIBLIO_RULES + conditional_rules(ctx)) if is_bibliometric(ctx) else ""
    if style in ("simple", "ddl"):
        return SIMPLE_SYSTEM_PROMPT + rules
    return SQL_SYSTEM_PROMPT.format(domain_rules=rules)

SQL_USER_TEMPLATE = """Genera la consulta SQL para responder esta pregunta:

PREGUNTA: {query}

ESQUEMA DISPONIBLE (usa SOLO estas tablas y columnas):
{schema}
{hints}
SQL:"""


def _build_schema_text(ctx: SchemaContext, style: str | None = None) -> str:
    """Construye el texto del esquema para el prompt del LLM."""
    style = style or SQL_PROMPT
    lines = []
    ddl = []
    for table in ctx.relevant_tables:
        cols = ctx.relevant_columns.get(table, [])
        types = ctx.column_types.get(table, {})
        # "tabla: col, col" y no "tabla(col, col)": con paréntesis el LLM escribía alias(columna).
        # El tipo va como "col INTEGER", sin paréntesis, por la misma razón.
        cols = [f"{c} {types[c.lower()]}" if types.get(c.lower()) else c for c in cols]
        lines.append(f"  {table}: {', '.join(cols)}")
        ddl.append(f"CREATE TABLE {table} (\n  " + ",\n  ".join(cols) + "\n);")
    if style == "ddl":
        lines = []

    if "ismainarticle" in ctx.relevant_columns.get("article", []):
        lines.append("")
        lines.append("SIGNIFICADO DE COLUMNAS:")
        lines.append("  article.ismainarticle: 1 = artículo principal del corpus (los que se analizan); "
                     "0 = referencia citada por esos artículos. La tabla article mezcla ambos: cuando la "
                     "pregunta habla del corpus o de 'los artículos' (conteos, rankings, años, países, autores, "
                     "revistas) filtra article.ismainarticle = 1, salvo que pida explícitamente las referencias. "
                     "(Si olvidas el filtro, el sistema limita article a los artículos principales.)")
        lines.append("  article.cited_by: número de citas que recibió el artículo (ya es una cifra; para "
                     "'cuántas citas tiene el más citado' devuelve cited_by con ORDER BY cited_by DESC LIMIT 1, "
                     "sin contar filas de otras tablas).")
        lines.append("  article.document_type: tipo de documento en MAYÚSCULAS ('ARTICLE', 'CONFERENCE PAPER', "
                     "'REVIEW'…). Solo dice el tipo, no el acceso abierto.")
        art_cols = ctx.relevant_columns.get("article", [])
        if "publisher" in art_cols:
          lines.append("  article.publisher: casa editorial que publica el artículo (p. ej. 'ELSEVIER LTD'); una pregunta por la "
                     "'editorial' de los artículos se refiere a esta columna, no a document_type. Puede ser NULL.")
        if "language" in art_cols:
          lines.append("  article.language: idioma del texto del artículo en MAYÚSCULAS (p. ej. 'ENGLISH'); para contar idiomas "
                     "usa COUNT(DISTINCT language).")
        if re.search(r"palabras? clave|keyword", (ctx.query or "").lower()):
          lines.append("  article.author_keywords: palabras clave de autor separadas por '; ' (están en article, no en author): "
                     "filtra con UPPER(article.author_keywords) LIKE '%TÉRMINO%'.")
        lines.append("  article.open_access_indicator: NULL = no es de acceso abierto; con texto (p. ej. "
                     "'ALL OPEN ACCESS; GOLD OPEN ACCESS') = sí es de acceso abierto.")

    if getattr(ctx, "value_hints", None):
        lines.append("")
        lines.append("CÓMO ESTÁN ESCRITOS LOS VALORES DE TEXTO:")
        for hint in ctx.value_hints:
            lines.append(f"  {hint}")

    if ctx.foreign_keys:
        lines.append("")
        lines.append("RELACIONES (para JOINs):")
        for fk in ctx.foreign_keys:
            lines.append(f"  {fk}")

    if ctx.entities:
        lines.append("")
        lines.append("ENTIDADES DETECTADAS (usar en filtros WHERE):")
        for k, v in ctx.entities.items():
            lines.append(f"  {k}: {v}")

    if SQL_PROMPT == "ddl":
        return "\n\n".join(ddl) + "\n\n" + "\n".join(f"-- {l.strip()}" for l in lines if l.strip())
    return "\n".join(lines)


def extract_sql_from_response(response: str) -> str:
    """Extrae el SQL de la respuesta del LLM, eliminando texto extra."""
    # Intentar extraer de bloque markdown
    match = re.search(r"```(?:sql)?\s*\n?(.*?)```", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Buscar la primera línea que parezca SQL
    lines = response.strip().split("\n")
    sql_lines = []
    capturing = False

    for line in lines:
        line_upper = line.strip().upper()
        if line_upper.startswith(("SELECT", "WITH")):
            capturing = True
        if capturing:
            sql_lines.append(line)
            if line.strip().endswith(";"):
                break

    if sql_lines:
        return "\n".join(sql_lines).strip()

    # Fallback: devolver todo limpio
    return response.strip()


def generate_sql(ctx: SchemaContext, history: list[dict] | None = None, feedback: str | None = None, evidence: str | None = None,
                 model: str | None = None, style: str | None = None) -> str:
    """
    Genera una consulta SQL a partir del SchemaContext.

    Parámetros
    ----------
    ctx : SchemaContext
        Contexto producido por la Capa 1 con tablas, columnas, FKs y entidades.
    history : list[dict] | None
        Historial de la conversación.
    feedback : str | None
        Crítica de la auto-reflexión para mejorar el SQL.
    evidence : str | None
        Evidencia adicional (pistas) para el LLM.

    Retorna
    -------
    str
        Consulta SQL generada por el LLM.
    """
    from src.layer2_agent.answer_synthesizer import _format_history

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=model or OLLAMA_SQL_MODEL,
        temperature=LLM_TEMPERATURE,
        num_predict=OLLAMA_NUM_PREDICT,
        num_ctx=OLLAMA_NUM_CTX,
    )

    style = style or SQL_PROMPT
    schema_text = _build_schema_text(ctx, style)

    hints = f"\n### PISTAS:\n{evidence}\n" if evidence else ""

    user_msg = _format_history(ctx.query, history or [])
    if feedback:
        user_msg += (
            f"IMPORTANTE: un intento previo NO respondió bien la pregunta. "
            f"Crítica: {feedback}. Genera una consulta SQL DISTINTA que la responda mejor.\n\n"
        )
    if style == "ddl":
        extra = f"\n-- External knowledge: {evidence}" if evidence else ""
        user_msg += f"{schema_text}\n{extra}\n-- Question: {ctx.query}\n-- SQL:"
    else:
        user_msg += SQL_USER_TEMPLATE.format(
            query=ctx.query,
            schema=schema_text,
            hints=hints,
        )

    response = llm.invoke([
        {"role": "system", "content": system_prompt(ctx, style)},
        {"role": "user",   "content": user_msg},
    ])

    sql = extract_sql_from_response(response.content)
    return sql


# ── Consenso por ejecución (V9) ───────────────────────────────────────────────
# Varias candidatas de SQL (modelos y formatos de prompt distintos, todas a temperatura 0) se ejecutan sobre la BD y se
# elige la que comparte resultado con más candidatas. Es una técnica general de Text-to-SQL (self-consistency por
# ejecución): no mira de qué trata la pregunta ni usa reglas por plantilla.
SQL_ENSEMBLE = os.getenv("SQL_ENSEMBLE", "1") == "1"
# (modelo, estilo de prompt); la primera es la candidata de referencia y desempata.
ENSEMBLE_CANDIDATES = [
    (OLLAMA_SQL_MODEL, "ddl"),
    (OLLAMA_MODEL, "ddl"),
    (OLLAMA_MODEL, "orig"),
]


def _signature(res) -> tuple | None:
    """Huella del resultado: filas ordenadas, con floats redondeados. None si falló o vino vacío."""
    if res is None or not res.success or res.row_count == 0:
        return None
    def norm(v):
        if isinstance(v, float):
            return round(v, 3)
        return str(v).strip().upper() if v is not None else None
    return tuple(sorted(tuple(norm(v) for v in r.values()) for r in res.rows))


def generate_consensus_sql(ctx: SchemaContext, history: list[dict] | None = None, feedback: str | None = None,
                           evidence: str | None = None, db_path: str | None = None) -> str:
    """Genera con cada candidata, ejecuta y devuelve el SQL cuyo resultado coincide con más candidatas.

    Si ninguna da filas, o no hay consenso (todas distintas), devuelve la de referencia. Si falla la candidata de
    referencia pero otra corre bien, se prefiere la que corre bien (el ciclo de refinamiento se queda con el resto).
    """
    from src.layer2_agent.sql_validator import execute_sql

    cands = []
    for model, style in ENSEMBLE_CANDIDATES:
        try:
            sql = generate_sql(ctx, history=history, feedback=feedback, evidence=evidence, model=model, style=style)
        except Exception as e:  # una candidata caída no debe tumbar la consulta
            print(f"      [consenso] {model}/{style} falló: {e}")
            continue
        kw = {"db_path": db_path} if db_path else {}
        res = execute_sql(sql, **kw)
        cands.append((sql, res, _signature(res)))
    if not cands:
        return generate_sql(ctx, history=history, feedback=feedback, evidence=evidence)

    groups: dict = {}
    for i, (_, _, sig) in enumerate(cands):
        if sig is not None:
            groups.setdefault(sig, []).append(i)
    if groups:
        # mayor grupo; empate -> el que contiene la candidata de referencia (índice menor)
        best = max(groups.values(), key=lambda idx: (len(idx), -min(idx)))
        pick = best[0]
    else:
        # ninguna dio filas: la primera que ejecutó sin error, si no la de referencia
        ok = [i for i, (_, r, _) in enumerate(cands) if r.success]
        pick = ok[0] if ok else 0
    print(f"      [consenso] {len(cands)} candidatas, grupos {[len(g) for g in groups.values()]}, elegida #{pick}")
    return cands[pick][0]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.layer1_schema.schema_linker import link_schema

    import argparse
    parser = argparse.ArgumentParser(description="Generar SQL desde una query en español")
    parser.add_argument("--query", "-q", type=str, required=True)
    args = parser.parse_args()

    print(f"\n  Query: '{args.query}'\n")

    # Paso 1: Schema linking
    print("  [1] Schema linking...")
    ctx = link_schema(args.query)
    print(f"      Canal: {ctx.query_type} | Tablas: {ctx.relevant_tables}")

    # Paso 2: Generar SQL
    print("  [2] Generando SQL con LLM...")
    sql = generate_sql(ctx)
    print(f"\n  SQL generado:\n  {sql}\n")
