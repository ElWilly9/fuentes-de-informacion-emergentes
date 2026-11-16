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
import unicodedata
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
# affiliation y articleauthor también tienen filas de las referencias: "¿cuántos países distintos aparecen en las
# afiliaciones?" sin unir article contaba 112 países en vez de 29 (Agrovoltaics).
for _t in ("Affiliation", "ArticleAuthor"):
    SCOPE_VIEWS[f"corpus_{_t.lower()}"] = (f"SELECT * FROM {_t} WHERE SR IN "
                                           "(SELECT SR FROM Article WHERE ismainarticle = 1)")
    SCOPE_VIEWS[f"reference_{_t.lower()}"] = (f"SELECT * FROM {_t} WHERE SR IN "
                                              "(SELECT SR FROM Article WHERE ismainarticle = 0)")


def scope_to_corpus(sql: str) -> str:
    """
    Lee `article` como la vista `corpus_articles` (solo artículos principales). Se conserva el nombre como
    alias para que `article.sr` siga valiendo. Si el LLM pide referencias (ismainarticle = 0 u otra condición
    que no sea = 1), se respeta tal cual. Con solo "= 1" también se cambia: el filtro suele quedar en la
    consulta externa y no en las subconsultas (ai-H01: `cited_by = (SELECT MAX(cited_by) FROM article)` tomaba
    el máximo de las referencias y daba 0 filas).
    """
    return _swap_to_views(sql, ("article",), {"article": "corpus_articles"})


def scope_links_to_corpus(sql: str) -> str:
    """Igual que scope_to_corpus para affiliation y articleauthor (vistas corpus_affiliation, corpus_articleauthor).
    Va después de link_affiliation_to_article, que busca `JOIN affiliation`."""
    return _swap_to_views(sql, ("affiliation", "articleauthor"),
                          {"affiliation": "corpus_affiliation", "articleauthor": "corpus_articleauthor"})


def _swap_to_views(sql: str, tables: tuple[str, ...], views: dict[str, str]) -> str:
    mentions = re.findall(r"ismainarticle\s*(?:=|==|IS)?\s*'?(\w*)", sql, re.IGNORECASE)
    if any(v != "1" for v in mentions):
        return sql

    def swap(m: re.Match) -> str:
        kw, table, rest, alias = m.group(1), m.group(2).lower(), m.group(3) or "", m.group(4)
        if alias and alias.lower() not in _SQL_KEYWORDS:
            return f"{kw} {views[table]}{rest}"
        return f"{kw} {views[table]} AS {table}{rest}"

    return re.sub(rf"(FROM|JOIN)\s+({'|'.join(tables)})(?!\w)(\s+(?:AS\s+)?(\w+))?", swap, sql, flags=re.IGNORECASE)


# Columnas de texto de article, author, affiliation y journal: en la BD están en MAYÚSCULAS (no así scimagodb ni
# treeofscience). `document_type = 'conference paper'` daba 0 filas.
_UPPER_COLS = (r"document_type|country|source_title|title|authorfullname|authorname|author_keywords|"
               r"index_keywords|affiliation|journal|open_access_indicator")


def uppercase_literals(sql: str) -> str:
    """Pasa a mayúsculas los textos comparados (=, LIKE, IN) con columnas que en la BD están en mayúsculas."""
    def up(m: re.Match) -> str:
        return m.group(1) + re.sub(r"'[^']*'", lambda s: s.group(0).upper(), m.group(2))

    return re.sub(rf"(\b(?:\w+\.)?(?:{_UPPER_COLS})\s*\)?\s*(?:=|<>|!=|(?:NOT\s+)?LIKE|(?:NOT\s+)?IN)\s*)"
                  r"('[^']*'|\((?:\s*'[^']*'\s*,?)+\))", up, sql, flags=re.IGNORECASE)


# Países en español (sin tildes, en mayúsculas) → como están en affiliation.country. El LLM a veces deja el nombre de la
# pregunta (`'%JORDANIA%'`) o lo traduce a medias (`'%THAILANDIA%'`, `'%ESPANIA%'`), y la consulta da 0 filas.
COUNTRY_ES_EN = {
    "ALEMANIA": "GERMANY", "ARABIA SAUDITA": "SAUDI ARABIA", "ARABIA SAUDI": "SAUDI ARABIA", "ARGELIA": "ALGERIA",
    "AUSTRALIA": "AUSTRALIA", "BANGLADES": "BANGLADESH", "BELGICA": "BELGIUM", "BRASIL": "BRAZIL", "CAMERUN": "CAMEROON",
    "CANADA": "CANADA", "COREA DEL SUR": "SOUTH KOREA", "CROACIA": "CROATIA", "DINAMARCA": "DENMARK", "EGIPTO": "EGYPT",
    "EMIRATOS ARABES UNIDOS": "UNITED ARAB EMIRATES", "ESLOVAQUIA": "SLOVAKIA", "ESLOVENIA": "SLOVENIA", "ESPANA": "SPAIN",
    "ESPANIA": "SPAIN", "ESTADOS UNIDOS": "UNITED STATES OF AMERICA", "ETIOPIA": "ETHIOPIA", "FILIPINAS": "PHILIPPINES",
    "FINLANDIA": "FINLAND", "FRANCIA": "FRANCE", "GRECIA": "GREECE", "HUNGRIA": "HUNGARY", "INDONESIA": "INDONESIA",
    "INGLATERRA": "UNITED KINGDOM", "IRAK": "IRAQ", "IRLANDA": "IRELAND", "ITALIA": "ITALY", "JAPON": "JAPAN",
    "JORDANIA": "JORDAN", "KENIA": "KENYA", "LIBANO": "LEBANON", "MALASIA": "MALAYSIA", "MARRUECOS": "MOROCCO",
    "MEXICO": "MEXICO", "NORUEGA": "NORWAY", "NUEVA ZELANDA": "NEW ZEALAND", "PAISES BAJOS": "NETHERLANDS",
    "PAKISTAN": "PAKISTAN", "POLONIA": "POLAND", "REINO UNIDO": "UNITED KINGDOM", "REPUBLICA CHECA": "CZECHIA",
    "RUMANIA": "ROMANIA", "RUSIA": "RUSSIAN FEDERATION", "SUDAFRICA": "SOUTH AFRICA", "SUECIA": "SWEDEN", "SUIZA": "SWITZERLAND",
    "TAILANDIA": "THAILAND", "THAILANDIA": "THAILAND", "TURQUIA": "TURKEY", "UCRANIA": "UKRAINE",
}


def translate_country_literals(sql: str) -> str:
    """Cambia los países en español de los textos comparados con `country` por su nombre en la BD."""
    def literal(s: re.Match) -> str:
        text = unicodedata.normalize("NFKD", s.group(0)).encode("ascii", "ignore").decode().upper()
        for es in sorted(COUNTRY_ES_EN, key=len, reverse=True):
            if re.search(rf"\b{es}\b", text):         # palabra completa: BANGLADES no debe tocar BANGLADESH
                return re.sub(rf"\b{es}\b", COUNTRY_ES_EN[es], text)
        return s.group(0)

    return re.sub(r"(\b(?:\w+\.)?country\s*\)?\s*(?:=|<>|!=|(?:NOT\s+)?LIKE|(?:NOT\s+)?IN)\s*)"
                  r"('[^']*'|\((?:\s*'[^']*'\s*,?)+\))",
                  lambda m: m.group(1) + re.sub(r"'[^']*'", literal, m.group(2)), sql, flags=re.IGNORECASE)


def author_names_to_ids(sql: str) -> str:
    """`authorid IN ('AGERT, CARSTEN', …)`: el LLM usa ahí los nombres de la pista; se busca por nombre en author."""
    def fix(m: re.Match) -> str:
        if "," not in m.group(2) and " " not in m.group(2):
            return m.group(0)                       # un AuthorID real no lleva espacios ni comas
        return f"{m.group(1)} IN (SELECT authorid FROM author WHERE authorfullname IN ({m.group(2)}))"

    return re.sub(r"(\b(?:\w+\.)?authorid)\s+IN\s*\(((?:\s*'[^']*'\s*,?)+)\)", fix, sql, flags=re.IGNORECASE)


_JOIN_END = r"(?=\b(?:JOIN|INNER|LEFT|WHERE|GROUP|ORDER|LIMIT|HAVING|UNION)\b|\)|;|$)"


def link_affiliation_to_article(sql: str) -> str:
    """
    `affiliation` tiene una fila por (artículo, autor). Unida solo por authorid trae las afiliaciones
    del autor en TODOS sus artículos: "artículos con autores de España" devolvía 61 artículos en vez de 4.
    Si el JOIN de affiliation no usa sr, se añade `AND af.sr = <artículo>.sr` (o articleauthor si no hay
    tabla de artículos).
    """
    tables = {t.lower(): (a if a and a.lower() not in _SQL_KEYWORDS else t)
              for t, a in re.findall(r"\b(?:FROM|JOIN)\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?", sql, re.IGNORECASE)}
    target = next((tables[t] for t in ("corpus_articles", "reference_articles", "article", "articleauthor")
                   if t in tables), None)
    if not target:
        return sql

    def fix(m: re.Match) -> str:
        alias = m.group(2) if m.group(2) and m.group(2).lower() not in _SQL_KEYWORDS else m.group(1)
        on = m.group(3)
        if re.search(r"\bsr\b", on, re.IGNORECASE):
            return m.group(0)
        return f"{m.group(0).rstrip()} AND {alias}.sr = {target}.sr "

    return re.sub(rf"\bJOIN\s+(affiliation)(?:\s+(?:AS\s+)?(\w+))?\s+ON\s+(.*?){_JOIN_END}",
                  fix, sql, flags=re.IGNORECASE)


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


_QUALIFIED = r"\b[A-Za-z_]\w*\.(\w+)\b"


def skip_null_journal(sql: str) -> str:
    """Al agrupar por revista, los artículos sin revista no son un grupo (en ai serían el mayor)."""
    c = _top_level_clauses(sql)
    group = (c or {}).get("GROUP BY", "")
    if not re.fullmatch(r"(?:\w+\.)?(?:source_title|journal)", group, re.IGNORECASE) or "UNION" in c:
        return sql
    if re.search(rf"{re.escape(group)}\s+IS\s+NOT\s+NULL", c.get("WHERE", ""), re.IGNORECASE):
        return sql
    c["WHERE"] = f"{c['WHERE']} AND {group} IS NOT NULL" if "WHERE" in c else f"{group} IS NOT NULL"
    order = ("SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT")
    return " ".join(f"{k} {c[k]}" for k in order if k in c)


def _sum_per_article(c: dict[str, str], alias: str) -> dict[str, str] | None:
    """
    SUM/AVG de una columna del artículo con GROUP BY y JOIN: el artículo pesa una vez por grupo.
    Si no, las citas de un artículo se suman una vez por cada afiliación de ese país: se agrega sobre las
    combinaciones distintas (grupo, artículo). None si no aplica o si dos columnas se llaman igual.
    """
    sel = c["SELECT"]
    aggs = re.findall(r"\b(?:SUM|AVG)\s*\(\s*(?:CAST\s*\(\s*)?(?:([A-Za-z_]\w*)\.)?(\w+)", sel, re.IGNORECASE)
    if not aggs or any(q and q.lower() != alias.lower() for q, _ in aggs):
        return None
    outer = {k: c[k] for k in ("SELECT", "GROUP BY", "HAVING", "ORDER BY") if k in c}
    columns = {"sr": f"{alias}.sr"}
    for text in outer.values():
        for q, col in re.findall(r"\b([A-Za-z_]\w*)\.(\w+)\b", text):
            if col.lower() == "sr":
                continue
            if columns.setdefault(col.lower(), f"{q}.{col}").lower() != f"{q}.{col}".lower():
                return None
    for _, col in aggs:
        columns.setdefault(col.lower(), f"{alias}.{col}")
    names = {a.lower() for a in re.findall(r"\bAS\s+(\w+)", sel, re.IGNORECASE)}
    for item in sel.split(",") + c["GROUP BY"].split(","):
        bare = re.match(r"\s*([A-Za-z_]\w*)(?:\s+AS\s+\w+)?\s*$", item, re.IGNORECASE)
        if bare and bare.group(1).lower() not in names:
            columns.setdefault(bare.group(1).lower(), bare.group(1))
    inner = ", ".join(f"{expr} AS {name}" for name, expr in columns.items())
    where = f" WHERE {c['WHERE']}" if "WHERE" in c else ""
    new = {"SELECT": sel, "FROM": f"(SELECT DISTINCT {inner} FROM {c['FROM']}{where})"}
    new.update({k: c[k] for k in ("GROUP BY", "HAVING", "ORDER BY", "LIMIT") if k in c})
    return {k: re.sub(_QUALIFIED, r"\1", v) if k in outer else v for k, v in new.items()}


def dedupe_fanout(sql: str) -> str:
    """
    Evita contar o sumar varias veces el mismo artículo cuando se une con tablas hijas
    (affiliation, articleauthor, author…: un artículo tiene varias filas en cada una).

    - Con GROUP BY: COUNT(*) / COUNT(1) / COUNT(alias.sr) pasa a COUNT(DISTINCT alias.sr), y SUM/AVG de columnas
      del artículo se calculan una vez por grupo y artículo (`_sum_per_article`).
    - Sin GROUP BY, columnas del artículo + SUM(cited_by) ("el más citado de X"): SUM sobra y se quita.
    - Sin GROUP BY y con solo agregados sobre columnas del artículo (SUM de citas, AVG…): se calculan
      sobre los artículos que cumplen las condiciones (semi-join `sr IN (…)`), cada uno una sola vez.
    - Sin GROUP BY y con solo columnas del artículo (un listado): SELECT DISTINCT.
    Lo que ya usa COUNT(DISTINCT …) o agrega columnas de otras tablas no se toca.
    """
    c = _top_level_clauses(sql)
    if not c or "SELECT" not in c or "FROM" not in c or "UNION" in c or c["FROM"].startswith("("):
        return sql
    has_join = re.search(r"\bJOIN\b", c["FROM"], re.IGNORECASE)
    # Solo afiliaciones o autores (sin article): también hay varias filas por artículo, aun sin JOIN
    m_link = re.search(r"^(?:corpus|reference)_(?:affiliation|articleauthor)(?!\w)(?:\s+(?:AS\s+)?(\w+))?",
                       c["FROM"], re.IGNORECASE)
    m = re.search(r"(?:^|\bJOIN\s+)(corpus_articles|reference_articles|article)(?!\w)(?:\s+(?:AS\s+)?(\w+))?",
                  c["FROM"], re.IGNORECASE)
    if m_link and not m and "GROUP BY" in c:
        alias = m_link.group(1) if m_link.group(1) and m_link.group(1).lower() not in _SQL_KEYWORDS \
            else re.match(r"\w+", c["FROM"]).group(0)
        new_sel = re.sub(rf"\bCOUNT\s*\(\s*(?:\*|1|(?:{alias}\.)?sr)\s*\)", f"COUNT(DISTINCT {alias}.sr)",
                         c["SELECT"], flags=re.IGNORECASE)
        if new_sel == c["SELECT"]:
            return sql
        c["SELECT"] = new_sel
        return " ".join(f"{kw} {body}" for kw, body in c.items())
    if not m or not has_join:
        return sql
    name = m.group(1)
    alias = m.group(2) if m.group(2) and m.group(2).lower() not in _SQL_KEYWORDS else name
    sel = c["SELECT"]

    if "GROUP BY" not in c:
        plain = re.sub(rf"\bSUM\s*\(\s*({alias}\.cited_by)\s*\)", r"\1", sel, flags=re.IGNORECASE)
        rest = [s.strip() for s in plain.split(",")]
        if plain != sel and len(rest) > 1 and all(re.fullmatch(rf"{alias}\.\w+(?:\s+AS\s+\w+)?", col, re.IGNORECASE)
                                                  for col in rest):
            sel = c["SELECT"] = plain

    # Listado de artículos (solo columnas del artículo, sin agregados): DISTINCT, para que el LIMIT
    # no se gaste en el mismo artículo repetido por cada autor o afiliación
    cols = [s.strip() for s in sel.split(",")]
    if "GROUP BY" not in c and not re.match(r"DISTINCT\b", sel, re.IGNORECASE) \
            and all(re.fullmatch(rf"{alias}\.\w+(?:\s+AS\s+\w+)?", col, re.IGNORECASE) for col in cols):
        c["SELECT"] = "DISTINCT " + sel
        return " ".join(f"{kw} {body}" for kw, body in c.items())

    if "GROUP BY" in c:
        new_sel = re.sub(rf"\bCOUNT\s*\(\s*(?:\*|1|(?:{alias}\.)?sr)\s*\)", f"COUNT(DISTINCT {alias}.sr)",
                         sel, flags=re.IGNORECASE)
        c["SELECT"] = new_sel
        per_article = _sum_per_article(c, alias)
        if per_article:
            c = per_article
        elif new_sel == sel:
            return sql
    else:
        only_aggs = not re.sub(_AGG, "", sel, flags=re.IGNORECASE).strip(" ,")
        needs_fix = re.search(r"\b(?:SUM|AVG)\s*\(|\bCOUNT\s*\((?!\s*DISTINCT)", sel, re.IGNORECASE)
        other_tables = {t for t in re.findall(r"\b(\w+)\.", sel) if t.lower() != alias.lower()}
        if not (only_aggs and needs_fix) or other_tables or "HAVING" in c:
            return sql
        where = c.get("WHERE", "")
        scope = ("corpus_articles" if re.search(r"ismainarticle\s*=\s*(?:'1'|1)\b", where, re.IGNORECASE)
                 else "reference_articles" if re.search(r"ismainarticle\s*=\s*(?:'0'|0)\b", where, re.IGNORECASE)
                 else name)
        inner = f"SELECT {alias}.sr FROM {c['FROM']}" + (f" WHERE {where}" if where else "")
        c = {"SELECT": sel, "FROM": f"{scope} AS {alias}", "WHERE": f"{alias}.sr IN ({inner})",
             **{k: v for k, v in c.items() if k in ("ORDER BY", "LIMIT")}}

    return " ".join(f"{kw} {body}" for kw, body in c.items())


def clean_sql(sql: str, bibliometric: bool = True) -> str:
    """
    Limpia el SQL extraído de la respuesta del LLM.
    Elimina bloques de código markdown, espacios extra, etc.
    Con bibliometric=False (BD que no es un corpus Robledo: Spider, BIRD) no pasa los literales a mayúsculas:
    en esas BD los valores van en minúsculas y mayúsculas ('The Rise of the Blue Beetle', 'Slovakia').
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
    if bibliometric:
        sql = uppercase_literals(sql)
        sql = translate_country_literals(sql)
        sql = author_names_to_ids(sql)
    sql = scope_to_corpus(sql)
    sql = link_affiliation_to_article(sql)
    sql = scope_links_to_corpus(sql)
    sql = dedupe_fanout(sql)

    return sql.rstrip(";").strip() + ";"


SQL_TIMEOUT_S = float(os.getenv("SQL_TIMEOUT_S", "30"))
_BIBLIO_DB: dict[str, bool] = {}


def is_bibliometric_db(db_path: str) -> bool:
    """True si la BD es un corpus Robledo (tabla Article con ismainarticle)."""
    key = str(db_path)
    if key not in _BIBLIO_DB:
        try:
            conn = sqlite3.connect(key)
            cols = [r[1].lower() for r in conn.execute("PRAGMA table_info(Article)")]
            conn.close()
            _BIBLIO_DB[key] = "ismainarticle" in cols
        except Exception:
            _BIBLIO_DB[key] = True
    return _BIBLIO_DB[key]


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
    sql_clean = clean_sql(sql, bibliometric=is_bibliometric_db(db_path))

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
        # Sin tope, un producto cartesiano del LLM corre sin fin (BIRD se quedó 2 h en una sola consulta)
        deadline = start + SQL_TIMEOUT_S
        conn.set_progress_handler(lambda: time.time() > deadline, 100_000)
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
