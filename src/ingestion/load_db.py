"""
load_db.py — Lógica de ingesta de Excel a SQLite
==================================================
Este módulo contiene la lógica para normalizar un archivo Excel de Scopus
en una estructura de base de datos SQLite.
"""

import sqlite3
from pathlib import Path
from typing import Callable, Optional
import pandas as pd
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de parseo
# ─────────────────────────────────────────────────────────────────────────────

def _split(value: str | None, sep: str = ";") -> list[str]:
    """Divide un campo delimitado por sep, limpiando espacios y vacíos."""
    if not value or pd.isna(value):
        return []
    return [v.strip() for v in str(value).split(sep) if v.strip()]


def _parse_authors(row: pd.Series) -> list[dict]:
    """
    Extrae autores desde 'author' (apellido, nombre) y 'author_full_names'.
    Retorna lista de dicts con AuthorID, AuthorName, AuthorFullName.
    """
    short_names = _split(row.get("author", ""))
    full_names  = _split(row.get("author_full_names", ""))
    ids_raw     = _split(row.get("authors_id", ""))

    max_len = max(len(short_names), len(full_names), len(ids_raw), 1)
    short_names += [None] * (max_len - len(short_names))
    full_names  += [None] * (max_len - len(full_names))
    ids_raw     += [None] * (max_len - len(ids_raw))

    authors = []
    for i, (short, full, aid) in enumerate(zip(short_names, full_names, ids_raw)):
        author_id = str(aid).strip() if aid else f"GEN_{row['SR']}_{i}"
        authors.append({
            "AuthorID":       author_id,
            "AuthorName":     short,
            "AuthorFullName": full,
            "Orcid":          None,
            "ResearcherID":   None,
            "Email":          None,
        })
    return authors


def _parse_affiliations(row: pd.Series, authors: list[dict]) -> list[dict]:
    """
    Extrae afiliaciones desde 'authors_with_affiliations'.
    """
    raw = row.get("authors_with_affiliations", "")
    if not raw or pd.isna(raw):
        return []

    affiliations = []
    entries = _split(str(raw), sep=";")

    for i, entry in enumerate(entries):
        parts = [p.strip() for p in entry.split(",")]
        affil_text = ", ".join(parts[1:-1]) if len(parts) > 2 else None
        country    = parts[-1] if len(parts) > 1 else None

        author_id = authors[i]["AuthorID"] if i < len(authors) else None

        affiliations.append({
            "SR":          row["SR"],
            "AuthorID":    author_id,
            "Affiliation": affil_text,
            "Country":     country,
        })
    return affiliations


# ─────────────────────────────────────────────────────────────────────────────
# Esquema SQL
# ─────────────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS Article (
    SR               TEXT PRIMARY KEY,
    title            TEXT,
    abstract         TEXT,
    year             INTEGER,
    cited_by         INTEGER,
    author_keywords  TEXT,
    index_keywords   TEXT,
    doi              TEXT,
    document_type    TEXT,
    source_title     TEXT,
    language         TEXT,
    ismainarticle    INTEGER,
    publisher        TEXT,
    open_access      TEXT
);
CREATE TABLE IF NOT EXISTS Author (
    AuthorID       TEXT PRIMARY KEY,
    AuthorName     TEXT,
    AuthorFullName TEXT,
    Orcid          TEXT,
    ResearcherID   TEXT,
    Email          TEXT
);
CREATE TABLE IF NOT EXISTS ArticleAuthor (
    SR                  TEXT,
    AuthorID            TEXT,
    AuthorOrder         INTEGER,
    CorrespondingAuthor INTEGER DEFAULT 0,
    PRIMARY KEY (SR, AuthorID),
    FOREIGN KEY (SR)       REFERENCES Article(SR),
    FOREIGN KEY (AuthorID) REFERENCES Author(AuthorID)
);
CREATE TABLE IF NOT EXISTS Affiliation (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    SR          TEXT,
    AuthorID    TEXT,
    Affiliation TEXT,
    Country     TEXT,
    FOREIGN KEY (SR)       REFERENCES Article(SR),
    FOREIGN KEY (AuthorID) REFERENCES Author(AuthorID)
);
CREATE TABLE IF NOT EXISTS journal (
    journal_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    source_title TEXT UNIQUE,
    journal      TEXT
);
CREATE TABLE IF NOT EXISTS scimagodb (
    SR                     TEXT PRIMARY KEY,
    SJR                    REAL,
    "SJR Best Quartile"    TEXT,
    "H index"              INTEGER,
    "Citations / Doc. (2years)" REAL,
    FOREIGN KEY (SR) REFERENCES Article(SR)
);
CREATE TABLE IF NOT EXISTS Citation (
    SR     TEXT,
    SR_ref TEXT,
    PRIMARY KEY (SR, SR_ref),
    FOREIGN KEY (SR)     REFERENCES Article(SR),
    FOREIGN KEY (SR_ref) REFERENCES Article(SR)
);
CREATE TABLE IF NOT EXISTS TreeOfScience (
    SR              TEXT PRIMARY KEY,
    tos             TEXT,
    author          TEXT,
    title           TEXT,
    doi             TEXT,
    author_keywords TEXT,
    FOREIGN KEY (SR) REFERENCES Article(SR)
);
CREATE TABLE IF NOT EXISTS egosauthors (
    Source TEXT,
    Target TEXT,
    Type   TEXT,
    Weight REAL,
    PRIMARY KEY (Source, Target)
);
"""


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL)
    conn.commit()


def _to_int(value) -> Optional[int]:
    # El Excel se lee con dtype=str: los booleanos llegan como "True"/"False"
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return 1 if value.strip().lower() == "true" else 0
    try:
        return int(float(str(value))) if value is not None else None
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Lógica de Carga Refactorizada
# ─────────────────────────────────────────────────────────────────────────────

# Hojas que identifican un Excel ya normalizado por el algoritmo Robledo
NORMALIZED_SHEETS = {"Article", "Author", "ArticleAuthor", "Affiliation"}
# Hojas auxiliares del algoritmo que no son tablas del corpus
IGNORED_SHEETS = {"Hoja 1", "Sheet1"}


# Textos que el algoritmo Robledo / pandas dejan en lugar de un dato ausente
PLACEHOLDERS = ("NO COUNTRY", "NO AFFILIATION", "NO ORCID", "NAN", "NONE", "NULL", "N/A", "-", "")


def clean_placeholders(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Convierte los marcadores de dato ausente en NULL y elimina las filas que quedan
    sin información útil, para que no cuenten como un país, revista o autor válido.

    - Todo texto que sea exactamente un marcador (sin distinguir mayúsculas) pasa a NULL.
    - Affiliation sin país se elimina: no puede entrar en ninguna estadística geográfica.
    - journal sin nombre se elimina.
    Los artículos nunca se eliminan (Article.source_title queda NULL si no hay revista).
    Retorna el número de filas afectadas por tipo de cambio.
    """
    marks = ",".join("'" + p + "'" for p in PLACEHOLDERS)
    stats: dict[str, int] = {"celdas_a_null": 0}
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
              if not r[0].startswith("sqlite_")]
    for t in tables:
        for _, col, ctype, *_ in conn.execute(f'PRAGMA table_info("{t}")').fetchall():
            if (ctype or "").upper() not in ("TEXT", ""):
                continue
            cur = conn.execute(
                f'UPDATE "{t}" SET "{col}" = NULL WHERE typeof("{col}")=\'text\' '
                f'AND UPPER(TRIM("{col}")) IN ({marks})')
            stats["celdas_a_null"] += cur.rowcount

    if "Affiliation" in tables:
        stats["affiliation_sin_pais_eliminadas"] = conn.execute(
            "DELETE FROM Affiliation WHERE Country IS NULL").rowcount
    if "journal" in tables:
        stats["journal_sin_nombre_eliminadas"] = conn.execute(
            "DELETE FROM journal WHERE source_title IS NULL").rowcount
    conn.commit()
    return stats


def _load_normalized_sheets(
    xl: pd.ExcelFile,
    db_path: Path,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> None:
    """
    Copia cada hoja del Excel como tabla SQLite del mismo nombre, sin
    re-derivar autores ni afiliaciones. No impone claves primarias: el corpus
    puede traer SR repetidos entre artículos distintos.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    sheets = [s for s in xl.sheet_names if s not in IGNORED_SHEETS]
    for i, sheet in enumerate(sheets):
        if progress_callback:
            progress_callback(f"Cargando hoja {sheet}...", 0.1 + 0.6 * i / len(sheets))
        df = pd.read_excel(xl, sheet_name=sheet)
        df = df.loc[:, ~df.columns.duplicated()]
        df = df.where(pd.notna(df), None)
        df.to_sql(sheet, conn, if_exists="replace", index=False)

    if progress_callback:
        progress_callback("Limpiando valores ausentes (NO COUNTRY, NAN...)", 0.8)
    clean_placeholders(conn)
    conn.close()
    if progress_callback:
        progress_callback("Base de datos creada con éxito.", 1.0)

def load_excel(
    xlsx_path: Path,
    db_path: Path,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> None:
    """
    Lee el Excel de Scopus y lo normaliza en SQLite.
    Usa progress_callback para reportar avances a la UI.
    """
    if progress_callback:
        progress_callback(f"Leyendo archivo Excel...", 0.1)

    # Excel preprocesado por el algoritmo Robledo: cada hoja ya es una tabla
    xl = pd.ExcelFile(xlsx_path)
    if NORMALIZED_SHEETS.issubset(xl.sheet_names):
        _load_normalized_sheets(xl, db_path, progress_callback)
        xl.close()
        return
    xl.close()

    df = pd.read_excel(xlsx_path, dtype=str)
    df = df.where(pd.notna(df), None)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    create_schema(conn)

    seen_authors: dict[str, dict] = {}
    journals_inserted: set[str] = set()
    articles = []
    article_authors = []
    affiliations = []

    if progress_callback:
        progress_callback(f"Procesando {len(df)} filas...", 0.2)

    for i, (_, row) in enumerate(df.iterrows()):
        sr = str(row["SR"]).strip()
        articles.append({
            "SR":             sr,
            "title":          row.get("title"),
            "abstract":       row.get("abstract"),
            "year":           _to_int(row.get("year")),
            "cited_by":       _to_int(row.get("cited_by")),
            "author_keywords":row.get("author_keywords"),
            "index_keywords": row.get("index_keywords"),
            "doi":            row.get("doi"),
            "document_type":  row.get("document_type"),
            "source_title":   row.get("source_title"),
            "language":       row.get("language"),
            "ismainarticle":  _to_int(row.get("ismainarticle")),
            "publisher":      row.get("publisher"),
            "open_access":    row.get("open_access_indicator"),
        })

        authors = _parse_authors(row)
        for order, author in enumerate(authors, start=1):
            aid = author["AuthorID"]
            if aid not in seen_authors:
                seen_authors[aid] = author
            article_authors.append({
                "SR":                 sr,
                "AuthorID":           aid,
                "AuthorOrder":        order,
                "CorrespondingAuthor": 1 if order == 1 else 0,
            })

        affiliations.extend(_parse_affiliations(row, authors))
        st = row.get("source_title")
        if st and st not in journals_inserted:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO journal (source_title, journal) VALUES (?, ?)",
                    (st, row.get("journal"))
                )
                journals_inserted.add(st)
            except sqlite3.Error:
                pass

        if progress_callback and i % 100 == 0:
            perc = 0.2 + (i / len(df)) * 0.4
            progress_callback(f"Analizando datos: {i}/{len(df)}", perc)

    if progress_callback:
        progress_callback("Insertando datos en SQLite...", 0.7)

    conn.executemany(
        """INSERT OR REPLACE INTO Article
           (SR,title,abstract,year,cited_by,author_keywords,index_keywords,
            doi,document_type,source_title,language,ismainarticle,publisher,open_access)
           VALUES (:SR,:title,:abstract,:year,:cited_by,:author_keywords,:index_keywords,
                   :doi,:document_type,:source_title,:language,:ismainarticle,:publisher,:open_access)""",
        articles
    )
    conn.executemany(
        """INSERT OR IGNORE INTO Author
           (AuthorID,AuthorName,AuthorFullName,Orcid,ResearcherID,Email)
           VALUES (:AuthorID,:AuthorName,:AuthorFullName,:Orcid,:ResearcherID,:Email)""",
        list(seen_authors.values())
    )
    conn.executemany(
        """INSERT OR REPLACE INTO ArticleAuthor
           (SR,AuthorID,AuthorOrder,CorrespondingAuthor)
           VALUES (:SR,:AuthorID,:AuthorOrder,:CorrespondingAuthor)""",
        article_authors
    )
    conn.executemany(
        """INSERT INTO Affiliation (SR,AuthorID,Affiliation,Country)
           VALUES (:SR,:AuthorID,:Affiliation,:Country)""",
        affiliations
    )

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    if progress_callback:
        progress_callback("Base de datos creada con éxito.", 1.0)
