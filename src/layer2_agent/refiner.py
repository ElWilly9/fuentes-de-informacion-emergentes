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
from src.layer2_agent.sql_generator import OLLAMA_SQL_MODEL, generate_sql, generate_consensus_sql, SQL_ENSEMBLE, _build_schema_text, is_bibliometric
from src.layer2_agent.sql_validator import execute_sql, SQLResult

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "glm4:9b")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))  # tope de tokens de salida: corta los bucles de texto basura de glm4
# Contexto fijo en todas las llamadas (si solo algunas lo cambian, Ollama recarga el modelo). Sin fijarlo, el
# valor por defecto depende de la versión de Ollama y de la VRAM (4.096 en una GPU de 12 GB).
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
SQL_MAX_RETRIES = int(os.getenv("SQL_MAX_RETRIES", "3"))

# ── Prompt para corrección ────────────────────────────────────────────────────

REFINE_SYSTEM_PROMPT = """Eres un experto en SQL para SQLite. Tu consulta anterior falló.
Corrige el SQL basándote en el mensaje de error.

REGLAS:
1. Genera SOLO el SQL corregido, sin explicaciones.
2. Usa SOLO las tablas y columnas del esquema proporcionado.
3. Presta atención al error — probablemente usaste una columna que no existe
   o un JOIN incorrecto.
4. Responde ÚNICAMENTE con el SQL corregido.{domain_rules}"""

# Solo con el esquema bibliométrico (ver sql_generator.BIBLIO_RULES)
REFINE_BIBLIO_RULES = "\n5. cited_by y year son TEXT — usa CAST() para operaciones numéricas."

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
        model=OLLAMA_SQL_MODEL,
        temperature=0.0,
        num_predict=OLLAMA_NUM_PREDICT,
        num_ctx=OLLAMA_NUM_CTX,
    )

    schema_text = _build_schema_text(ctx)

    user_msg = REFINE_USER_TEMPLATE.format(
        query=ctx.query,
        failed_sql=failed_sql,
        error=error,
        schema=schema_text,
    )

    response = llm.invoke([
        {"role": "system", "content": REFINE_SYSTEM_PROMPT.format(
            domain_rules=REFINE_BIBLIO_RULES if is_bibliometric(ctx) else "")},
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
    sql = generate_consensus_sql(ctx, db_path=db_path) if SQL_ENSEMBLE else generate_sql(ctx)

    # Paso 2: Ejecutar y validar
    kwargs = {"db_path": db_path} if db_path else {}
    result = execute_sql(sql, **kwargs)

    if result.success:
        return retry_if_empty(ctx, result, db_path)

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


# Reintento cuando el SQL corre pero no devuelve filas. Un solo intento, y solo se acepta si trae filas.
# APAGADO por defecto (2026-11-03): no aportó. Spider 0,663 con y sin; BIRD 0,417 con, 0,420 sin; 196 preguntas de los
# sets propios con puntajes idénticos.
SQL_EMPTY_RETRY = os.getenv("SQL_EMPTY_RETRY", "0") == "1"
EMPTY_RESULT_ERROR = ("La consulta se ejecutó sin errores pero devolvió 0 filas. Revisa si añadiste filtros, JOIN o "
                      "condiciones que la pregunta no pide, o si los valores no están escritos como en la base de datos.")


def retry_if_empty(ctx: SchemaContext, result: SQLResult, db_path: str = None) -> SQLResult:
    """Si `result` corrió bien pero vino vacío, pide una corrección; la usa solo si devuelve filas."""
    if not (SQL_EMPTY_RETRY and result and result.success and result.row_count == 0):
        return result
    kwargs = {"db_path": db_path} if db_path else {}
    retried = execute_sql(refine_sql(ctx, result.query, EMPTY_RESULT_ERROR), **kwargs)
    return retried if retried.success and retried.row_count > 0 else result


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
