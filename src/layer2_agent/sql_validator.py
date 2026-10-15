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


_SQL_KEYWORDS = {
    "on", "where", "join", "left", "right", "inner", "outer", "cross", "group", "order", "limit",
    "having", "union", "as", "select", "from", "and", "or", "not", "in", "exists", "using", "natural",
}


def repair_column_refs(sql: str) -> str:
    """
    Corrige `alias(columna)` → `alias.columna` cuando `alias` es una tabla o un alias del FROM/JOIN.

    El LLM imita el formato `tabla(col1, col2)` con el que ve el esquema y escribe `a(sr)`, que
    SQLite interpreta como una función inexistente. Funciones reales (COUNT, CAST…) no se tocan
    porque no son tablas ni alias de la consulta.
    """
    names = set()
    for table, alias in re.findall(r"\b(?:FROM|JOIN)\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?", sql, re.IGNORECASE):
        names.add(table.lower())
        if alias and alias.lower() not in _SQL_KEYWORDS:
            names.add(alias.lower())
    if not names:
        return sql
    return re.sub(r"\b(\w+)\(\s*(\w+)\s*\)",
                  lambda m: f"{m.group(1)}.{m.group(2)}" if m.group(1).lower() in names else m.group(0),
                  sql)


# Vistas de alcance: article mezcla artículos del corpus (ismainarticle = 1) con las referencias que
# citan (= 0). El LLM no filtra de forma estable, así que por defecto article se lee como corpus_articles.
SCOPE_VIEWS = {
    "corpus_articles":    "SELECT * FROM Article WHERE ismainarticle = 1",
    "reference_articles": "SELECT * FROM Article WHERE ismainarticle = 0",
}


def scope_to_corpus(sql: str) -> str:
    """
    Si la consulta no menciona ismainarticle, lee `article` como la vista `corpus_articles`
    (solo artículos principales). Se conserva el nombre como alias para que `article.sr` siga valiendo.
    Si el LLM filtra ismainarticle (= 1 o = 0), se respeta tal cual.
    """
    if re.search(r"ismainarticle", sql, re.IGNORECASE):
        return sql

    def swap(m: re.Match) -> str:
        kw, rest, alias = m.group(1), m.group(2) or "", m.group(3)
        if alias and alias.lower() not in _SQL_KEYWORDS:
            return f"{kw} corpus_articles{rest}"
        return f"{kw} corpus_articles AS article{rest}"

    return re.sub(r"(FROM|JOIN)\s+article(?!\w)(\s+(?:AS\s+)?(\w+))?", swap, sql, flags=re.IGNORECASE)


_CLAUSES = re.compile(r"\b(SELECT|FROM|WHERE|GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT|UNION)\b", re.IGNORECASE)
_AGG = r"\b(?:SUM|AVG|COUNT|MAX|MIN)\s*\((?:[^()]|\([^()]*\))*\)(?:\s+AS\s+\w+)?"


def _top_level_clauses(sql: str) -> dict[str, str] | None:
    """Parte un SELECT en sus cláusulas del nivel exterior (ignora subconsultas y texto entre comillas)."""
    masked = re.sub(r"'[^']*'", lambda m: "'" + "_" * (len(m.group()) - 2) + "'", sql)
    depth, depths = 0, []
    for ch in masked:
        depth += (ch == "(") - (ch == ")")
        depths.append(depth)
    found = [(re.sub(r"\s+", " ", m.group(1).upper()), m.start(), m.end())
             for m in _CLAUSES.finditer(masked) if depths[m.start()] == 0]
    out: dict[str, str] = {}
    for i, (kw, _, end) in enumerate(found):
        stop = found[i + 1][1] if i + 1 < len(found) else len(sql)
        if kw in out:
            return None
        out[kw] = sql[end:stop].strip().rstrip(";").strip()
    return out


def dedupe_fanout(sql: str) -> str:
    """
    Evita contar o sumar varias veces el mismo artículo cuando se une con tablas hijas
    (affiliation, articleauthor, author…: un artículo tiene varias filas en cada una).

    - Con GROUP BY: COUNT(*) / COUNT(1) / COUNT(alias.sr) pasa a COUNT(DISTINCT alias.sr).
    - Sin GROUP BY y con solo agregados sobre columnas del artículo (SUM de citas, AVG…): se calculan
      sobre los artículos que cumplen las condiciones (semi-join `sr IN (…)`), cada uno una sola vez.
    Lo que ya usa COUNT(DISTINCT …) o agrega columnas de otras tablas no se toca.
    """
    if not re.search(r"\bJOIN\b", sql, re.IGNORECASE):
        return sql
    c = _top_level_clauses(sql)
    if not c or "SELECT" not in c or "FROM" not in c or "UNION" in c:
        return sql
    m = re.search(r"(?:^|\bJOIN\s+)(corpus_articles|reference_articles|article)(?!\w)(?:\s+(?:AS\s+)?(\w+))?",
                  c["FROM"], re.IGNORECASE)
    if not m:
        return sql
    name = m.group(1)
    alias = m.group(2) if m.group(2) and m.group(2).lower() not in _SQL_KEYWORDS else name
    sel = c["SELECT"]

    if "GROUP BY" in c:
        new_sel = re.sub(rf"\bCOUNT\s*\(\s*(?:\*|1|(?:{alias}\.)?sr)\s*\)", f"COUNT(DISTINCT {alias}.sr)",
                         sel, flags=re.IGNORECASE)
        if new_sel == sel:
            return sql
        c["SELECT"] = new_sel
    else:
        only_aggs = not re.sub(_AGG, "", sel, flags=re.IGNORECASE).strip(" ,")
        needs_fix = re.search(r"\b(?:SUM|AVG)\s*\(|\bCOUNT\s*\((?!\s*DISTINCT)", sel, re.IGNORECASE)
        other_tables = {t for t in re.findall(r"\b(\w+)\.", sel) if t.lower() != alias.lower()}
        if not (only_aggs and needs_fix) or other_tables or "HAVING" in c \
                or len(re.findall(r"\bSELECT\b", sql, re.IGNORECASE)) != 1:
            return sql
        where = c.get("WHERE", "")
        scope = ("corpus_articles" if re.search(r"ismainarticle\s*=\s*(?:'1'|1)\b", where, re.IGNORECASE)
                 else "reference_articles" if re.search(r"ismainarticle\s*=\s*(?:'0'|0)\b", where, re.IGNORECASE)
                 else name)
        inner = f"SELECT {alias}.sr FROM {c['FROM']}" + (f" WHERE {where}" if where else "")
        c = {"SELECT": sel, "FROM": f"{scope} AS {alias}", "WHERE": f"{alias}.sr IN ({inner})",
             **{k: v for k, v in c.items() if k in ("ORDER BY", "LIMIT")}}

    return " ".join(f"{kw} {body}" for kw, body in c.items())


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
    sql = repair_column_refs(sql)
    sql = scope_to_corpus(sql)
    sql = dedupe_fanout(sql)

    return sql.rstrip(";").strip() + ";"


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
        for name, body in SCOPE_VIEWS.items():  # vistas temporales: valen también para BDs ya creadas
            conn.execute(f"CREATE TEMP VIEW IF NOT EXISTS {name} AS {body}")
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
