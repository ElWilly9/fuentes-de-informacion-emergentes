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
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))  # tope de tokens de salida: corta los bucles de texto basura de glm4
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

# Reglas del corpus bibliométrico. Solo se añaden si el esquema es el nuestro (tabla article):
# en otras BD (Spider) el LIMIT 10 por defecto, los CAST y el LIKE causaron 36 de 53 pérdidas.
BIBLIO_RULES = """

REGLAS DEL CORPUS BIBLIOMÉTRICO:
7. La base de datos es un corpus bibliométrico; las preguntas llegan en español.
8. Para texto, usa LIKE con % para búsquedas parciales.
9. Siempre incluye LIMIT si la pregunta pide "top", "más", "mejores" (default LIMIT 10).
10. cited_by puede ser TEXT — usa CAST(cited_by AS INTEGER) para ordenar numéricamente.
11. year puede ser TEXT — usa CAST(year AS INTEGER) para filtros numéricos."""


def is_bibliometric(ctx: SchemaContext) -> bool:
    return any(t.lower() == "article" for t in ctx.relevant_tables)


def system_prompt(ctx: SchemaContext) -> str:
    return SQL_SYSTEM_PROMPT.format(domain_rules=BIBLIO_RULES if is_bibliometric(ctx) else "")

SQL_USER_TEMPLATE = """Genera la consulta SQL para responder esta pregunta:

PREGUNTA: {query}

ESQUEMA DISPONIBLE (usa SOLO estas tablas y columnas):
{schema}
{hints}
SQL:"""


def _build_schema_text(ctx: SchemaContext) -> str:
    """Construye el texto del esquema para el prompt del LLM."""
    lines = []
    for table in ctx.relevant_tables:
        cols = ctx.relevant_columns.get(table, [])
        types = ctx.column_types.get(table, {})
        # "tabla: col, col" y no "tabla(col, col)": con paréntesis el LLM escribía alias(columna).
        # El tipo va como "col INTEGER", sin paréntesis, por la misma razón.
        cols = [f"{c} {types[c.lower()]}" if types.get(c.lower()) else c for c in cols]
        lines.append(f"  {table}: {', '.join(cols)}")

    if "ismainarticle" in ctx.relevant_columns.get("article", []):
        lines.append("")
        lines.append("SIGNIFICADO DE COLUMNAS:")
        lines.append("  article.ismainarticle: 1 = artículo principal del corpus (los que se analizan); "
                     "0 = referencia citada por esos artículos. La tabla article mezcla ambos: cuando la "
                     "pregunta habla del corpus o de 'los artículos' (conteos, rankings, años, países, autores, "
                     "revistas) filtra article.ismainarticle = 1, salvo que pida explícitamente las referencias. "
                     "(Si olvidas el filtro, el sistema limita article a los artículos principales.)")

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


def generate_sql(ctx: SchemaContext, history: list[dict] | None = None, feedback: str | None = None, evidence: str | None = None) -> str:
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
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
        num_predict=OLLAMA_NUM_PREDICT,
    )

    schema_text = _build_schema_text(ctx)

    hints = f"\n### PISTAS:\n{evidence}\n" if evidence else ""

    user_msg = _format_history(ctx.query, history or [])
    if feedback:
        user_msg += (
            f"IMPORTANTE: un intento previo NO respondió bien la pregunta. "
            f"Crítica: {feedback}. Genera una consulta SQL DISTINTA que la responda mejor.\n\n"
        )
    user_msg += SQL_USER_TEMPLATE.format(
        query=ctx.query,
        schema=schema_text,
        hints=hints,
    )

    response = llm.invoke([
        {"role": "system", "content": system_prompt(ctx)},
        {"role": "user",   "content": user_msg},
    ])

    sql = extract_sql_from_response(response.content)
    return sql


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
