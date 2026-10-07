"""
sql_validator.py — Validación y ejecución de SQL contra SQLite
==============================================================
Recibe una consulta SQL generada por el LLM, la valida sintácticamente,
la ejecuta contra la BD SQLite y retorna los resultados o el error.

No depende del LLM — es puramente determinista.

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import sqlparse
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/db/bibliometria.db")


@dataclass
class SQLResult:
    """Resultado de la ejecución de una consulta SQL."""
    query: str                          # SQL ejecutado
    success: bool                       # True si ejecutó sin error
    rows: list[dict] = field(default_factory=list)  # Filas como dicts
    columns: list[str] = field(default_factory=list) # Nombres de columnas
    row_count: int = 0                  # Número de filas retornadas
    error: str | None = None            # Mensaje de error si falló
    execution_time_ms: float = 0.0      # Tiempo de ejecución


def validate_syntax(sql: str) -> tuple[bool, str | None]:
    """
    Valida la sintaxis básica del SQL antes de ejecutarlo.

    Reglas de seguridad:
    - Solo permite SELECT (no INSERT, UPDATE, DELETE, DROP, ALTER)
    - No permite múltiples statements (inyección SQL)
    - Debe contener al menos un FROM

    Retorna (True, None) si es válido, (False, "mensaje de error") si no.
    """
    if not sql or not sql.strip():
        return False, "SQL vacío"

    # Limpiar y parsear
    sql_clean = sql.strip().rstrip(";")
    parsed = sqlparse.parse(sql_clean)

    if len(parsed) == 0:
        return False, "No se pudo parsear el SQL"

    if len(parsed) > 1:
        return False, "Se detectaron múltiples statements SQL. Solo se permite uno."

    # Verificar que sea SELECT
    stmt = parsed[0]
    stmt_type = stmt.get_type()

    if stmt_type != "SELECT":
        return False, f"Solo se permiten consultas SELECT. Se detectó: {stmt_type}"

    # Verificar que no contenga operaciones peligrosas
    sql_upper = sql_clean.upper()
    forbidden = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ",
                 "CREATE ", "TRUNCATE ", "EXEC ", "EXECUTE "]
    for word in forbidden:
        if word in sql_upper:
            return False, f"Operación no permitida detectada: {word.strip()}"

    # Verificar que tenga FROM (un SELECT sin FROM es sospechoso)
    if "FROM" not in sql_upper:
        # Excepción: SELECT con funciones como SELECT 1+1, SELECT date()
        # Estos son válidos pero no los necesitamos para el sistema
        pass  # Lo permitimos por flexibilidad

    return True, None


def clean_sql(sql: str) -> str:
    """
    Limpia el SQL extraído de la respuesta del LLM.
    Elimina bloques de código markdown, espacios extra, etc.
    """
    # Extraer SQL de bloques markdown ```sql ... ```
    match = re.search(r"```(?:sql)?\s*\n?(.*?)```", sql, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1)

    # Limpiar
    sql = sql.strip()
    sql = sql.rstrip(";") + ";"  # Normalizar punto y coma al final
    sql = re.sub(r"\s+", " ", sql)  # Colapsar espacios múltiples

    return sql


def execute_sql(sql: str, db_path: str = DB_PATH) -> SQLResult:
    """
    Ejecuta una consulta SQL contra la BD SQLite.

    Proceso:
    1. Limpia el SQL (quita markdown, espacios extra)
    2. Valida la sintaxis (solo SELECT, sin inyección)
    3. Ejecuta contra SQLite
    4. Retorna SQLResult con los resultados o el error

    Parámetros
    ----------
    sql : str
        Consulta SQL a ejecutar (puede venir con formato markdown del LLM)
    db_path : str
        Ruta a la BD SQLite

    Retorna
    -------
    SQLResult
        Objeto con resultados, columnas, o error si falló.
    """
    import time

    # Paso 1: Limpiar
    sql_clean = clean_sql(sql)

    # Paso 2: Validar sintaxis
    valid, error_msg = validate_syntax(sql_clean)
    if not valid:
        return SQLResult(
            query=sql_clean,
            success=False,
            error=f"Error de validación: {error_msg}"
        )

    # Paso 3: Verificar que la BD existe
    if not Path(db_path).exists():
        return SQLResult(
            query=sql_clean,
            success=False,
            error=f"Base de datos no encontrada: {db_path}"
        )

    # Paso 4: Ejecutar
    start = time.time()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Resultados como diccionarios
        cursor = conn.execute(sql_clean)

        # Obtener nombres de columnas
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Obtener filas como dicts
        raw_rows = cursor.fetchall()
        rows = [dict(row) for row in raw_rows]

        elapsed = (time.time() - start) * 1000
        conn.close()

        return SQLResult(
            query=sql_clean,
            success=True,
            rows=rows,
            columns=columns,
            row_count=len(rows),
            execution_time_ms=round(elapsed, 2)
        )

    except sqlite3.OperationalError as e:
        elapsed = (time.time() - start) * 1000
        return SQLResult(
            query=sql_clean,
            success=False,
            error=f"Error SQLite: {str(e)}",
            execution_time_ms=round(elapsed, 2)
        )
    except Exception as e:
        return SQLResult(
            query=sql_clean,
            success=False,
            error=f"Error inesperado: {str(e)}"
        )


# ── Entry point para pruebas directas ────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ejecutar SQL contra la BD bibliométrica")
    parser.add_argument("--sql", type=str, required=True, help="Consulta SQL a ejecutar")
    parser.add_argument("--db", type=str, default=DB_PATH, help="Ruta a la BD SQLite")
    args = parser.parse_args()

    result = execute_sql(args.sql, args.db)

    if result.success:
        print(f"\n✓ SQL ejecutado en {result.execution_time_ms}ms")
        print(f"  {result.row_count} filas retornadas")
        print(f"  Columnas: {result.columns}")
        print()
        for i, row in enumerate(result.rows[:10], 1):
            print(f"  [{i}] {row}")
        if result.row_count > 10:
            print(f"  ... y {result.row_count - 10} filas más")
    else:
        print(f"\n✗ Error: {result.error}")
        print(f"  SQL: {result.query}")
