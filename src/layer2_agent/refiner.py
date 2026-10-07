"""
refiner.py — Ciclo de auto-corrección de SQL
=============================================
Si el SQL generado falla al ejecutarse, este módulo le muestra
el error al LLM y le pide que corrija la consulta. Máximo 3 intentos.

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from src.layer1_schema.models import SchemaContext
from src.layer2_agent.sql_generator import generate_sql, _build_schema_text
from src.layer2_agent.sql_validator import execute_sql, SQLResult

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "glm4:9b")
SQL_MAX_RETRIES = int(os.getenv("SQL_MAX_RETRIES", "3"))

# ── Prompt para corrección ────────────────────────────────────────────────────

REFINE_SYSTEM_PROMPT = """Eres un experto en SQL para SQLite. Tu consulta anterior falló.
Corrige el SQL basándote en el mensaje de error.

REGLAS:
1. Genera SOLO el SQL corregido, sin explicaciones.
2. Usa SOLO las tablas y columnas del esquema proporcionado.
3. Presta atención al error — probablemente usaste una columna que no existe
   o un JOIN incorrecto.
4. cited_by y year son TEXT — usa CAST() para operaciones numéricas.
5. Responde ÚNICAMENTE con el SQL corregido."""

REFINE_USER_TEMPLATE = """Tu SQL anterior falló. Corrígelo.

PREGUNTA ORIGINAL: {query}

SQL QUE FALLÓ:
{failed_sql}

ERROR:
{error}

ESQUEMA DISPONIBLE (usa SOLO estas tablas y columnas):
{schema}

SQL CORREGIDO:"""


def refine_sql(ctx: SchemaContext, failed_sql: str, error: str) -> str:
    """
    Pide al LLM que corrija un SQL que falló.

    Parámetros
    ----------
    ctx : SchemaContext
        Contexto de la Capa 1.
    failed_sql : str
        El SQL que causó el error.
    error : str
        Mensaje de error de SQLite.

    Retorna
    -------
    str
        SQL corregido por el LLM.
    """
    from src.layer2_agent.sql_generator import extract_sql_from_response

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.0,
    )

    schema_text = _build_schema_text(ctx)

    user_msg = REFINE_USER_TEMPLATE.format(
        query=ctx.query,
        failed_sql=failed_sql,
        error=error,
        schema=schema_text,
    )

    response = llm.invoke([
        {"role": "system", "content": REFINE_SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ])

    return extract_sql_from_response(response.content)


def generate_and_validate(ctx: SchemaContext, db_path: str = None) -> SQLResult:
    """
    Genera SQL con el LLM, lo ejecuta, y si falla lo corrige hasta 3 veces.

    Este es el flujo principal que combina sql_generator + sql_validator + refiner.

    Parámetros
    ----------
    ctx : SchemaContext
        Contexto de la Capa 1.
    db_path : str
        Ruta a la BD (opcional, usa .env por defecto).

    Retorna
    -------
    SQLResult
        Resultado exitoso o el último intento fallido.
    """
    # Paso 1: Generar SQL inicial
    sql = generate_sql(ctx)

    # Paso 2: Ejecutar y validar
    kwargs = {"db_path": db_path} if db_path else {}
    result = execute_sql(sql, **kwargs)

    if result.success:
        return result

    # Paso 3: Ciclo de refinamiento
    for attempt in range(1, SQL_MAX_RETRIES + 1):
        print(f"      Intento {attempt}/{SQL_MAX_RETRIES}: corrigiendo SQL...")
        print(f"      Error: {result.error}")

        refined_sql = refine_sql(ctx, result.query, result.error)
        result = execute_sql(refined_sql, **kwargs)

        if result.success:
            print(f"      SQL corregido exitosamente en intento {attempt}")
            return result

    # Si agotó los intentos
    print(f"      No se pudo corregir después de {SQL_MAX_RETRIES} intentos")
    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.layer1_schema.schema_linker import link_schema

    import argparse
    parser = argparse.ArgumentParser(description="Generar + validar + corregir SQL")
    parser.add_argument("--query", "-q", type=str, required=True)
    args = parser.parse_args()

    print(f"\n  Query: '{args.query}'\n")

    print("  [1] Schema linking...")
    ctx = link_schema(args.query)
    print(f"      Canal: {ctx.query_type} | Tablas: {ctx.relevant_tables}")

    print("  [2] Generando y validando SQL...")
    result = generate_and_validate(ctx)

    if result.success:
        print(f"\n  ✓ SQL exitoso ({result.execution_time_ms}ms, {result.row_count} filas)")
        print(f"  SQL: {result.query}\n")
        for i, row in enumerate(result.rows[:5], 1):
            print(f"  [{i}] {row}")
        if result.row_count > 5:
            print(f"  ... y {result.row_count - 5} filas más")
    else:
        print(f"\n  ✗ Falló después de todos los intentos")
        print(f"  Error: {result.error}")
        print(f"  SQL: {result.query}")
