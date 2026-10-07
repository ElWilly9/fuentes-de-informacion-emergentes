"""
batch_processor.py — Procesamiento masivo de xlsx bibliométricos
================================================================
Toma una carpeta con múltiples archivos .xlsx preprocesados por el
algoritmo Robledo y genera una base de datos SQLite por cada uno.

Cada xlsx tiene hojas que corresponden directamente a tablas:
  Article, Author, ArticleAuthor, Affiliation, journal,
  scimagodb, Citation, TreeOfScience

Uso:
    # Procesar todos los xlsx de una carpeta
    python src/ingestion/batch_processor.py --input data/raw/scopus/ --output data/db/

    # Procesar un solo archivo
    python src/ingestion/batch_processor.py --input data/raw/scopus/ai_Scopus_data.xlsx --output data/db/

    # Ver resumen sin procesar
    python src/ingestion/batch_processor.py --input data/raw/scopus/ --dry-run

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import argparse
import os
import re
import sqlite3
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm


# ── Hojas esperadas y su mapeo a tablas SQL ───────────────────────────────────

EXPECTED_SHEETS = {
    "Article":        "Article",
    "Author":         "Author",
    "ArticleAuthor":  "ArticleAuthor",
    "Affiliation":    "Affiliation",
    "journal":        "journal",
    "scimagodb":      "scimagodb",
    "Citation":       "Citation",
    "TreeOfScience":  "TreeOfScience",
}

# Hojas que ignoramos (metadatos auxiliares del algoritmo Robledo)
IGNORED_SHEETS = {"Hoja 1", "Sheet1", "egosauthors"}


def sanitize_name(filename: str) -> str:
    """
    Convierte el nombre del archivo en un identificador limpio.
    'ai_Scopus_data.xlsx' → 'ai'
    'agrovoltaics_Scopus_data.xlsx' → 'agrovoltaics'
    """
    name = Path(filename).stem  # quitar extensión
    # Quitar sufijos comunes
    for suffix in ["_Scopus_data", "_scopus_data", "_WoS_data", "_wos_data",
                   "_Scopus", "_scopus", "_WoS", "_wos"]:
        name = name.replace(suffix, "")
    # Limpiar caracteres especiales
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_").lower()
    return name


def inspect_xlsx(filepath: Path) -> dict:
    """
    Inspecciona un xlsx y retorna un resumen de sus hojas.
    """
    xl = pd.ExcelFile(filepath)
    info = {
        "filename": filepath.name,
        "corpus_name": sanitize_name(filepath.name),
        "sheets": {},
        "total_rows": 0,
    }

    for sheet in xl.sheet_names:
        if sheet in IGNORED_SHEETS:
            continue
        df = pd.read_excel(xl, sheet_name=sheet, nrows=0)
        row_count = pd.read_excel(xl, sheet_name=sheet).shape[0]
        info["sheets"][sheet] = {
            "columns": list(df.columns),
            "row_count": row_count,
        }
        info["total_rows"] += row_count

    xl.close()
    return info


def xlsx_to_sqlite(filepath: Path, output_dir: Path) -> dict:
    """
    Convierte un xlsx preprocesado a SQLite.

    Cada hoja del xlsx se convierte en una tabla con el mismo nombre.
    El archivo SQLite se nombra según el corpus: ai.db, agrovoltaics.db, etc.

    Retorna dict con estadísticas del procesamiento.
    """
    corpus_name = sanitize_name(filepath.name)
    db_path = output_dir / f"{corpus_name}.db"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Si ya existe, borrar para re-crear
    if db_path.exists():
        db_path.unlink()

    stats = {
        "corpus": corpus_name,
        "source": filepath.name,
        "db_path": str(db_path),
        "tables": {},
        "total_rows": 0,
        "errors": [],
    }

    xl = pd.ExcelFile(filepath)
    conn = sqlite3.connect(db_path)

    for sheet_name in xl.sheet_names:
        if sheet_name in IGNORED_SHEETS:
            continue

        table_name = EXPECTED_SHEETS.get(sheet_name, sheet_name)

        try:
            df = pd.read_excel(xl, sheet_name=sheet_name)

            # Limpiar columnas duplicadas (como AuthorOrder repetido)
            df = df.loc[:, ~df.columns.duplicated()]

            # Limpiar NaN
            df = df.where(pd.notna(df), None)

            # Insertar en SQLite
            df.to_sql(table_name, conn, if_exists="replace", index=False)

            stats["tables"][table_name] = len(df)
            stats["total_rows"] += len(df)

        except Exception as e:
            stats["errors"].append(f"{sheet_name}: {str(e)}")

    conn.close()
    xl.close()

    return stats


def batch_process(input_path: Path, output_dir: Path, dry_run: bool = False) -> list[dict]:
    """
    Procesa todos los xlsx de una carpeta o un solo archivo.

    Parámetros
    ----------
    input_path : Path
        Carpeta con xlsx o un archivo específico.
    output_dir : Path
        Carpeta donde se guardan los .db generados.
    dry_run : bool
        Si True, solo inspecciona sin crear los .db.

    Retorna
    -------
    list[dict]
        Lista de estadísticas por cada archivo procesado.
    """
    # Recolectar archivos
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = sorted(input_path.glob("*.xlsx"))
    else:
        raise FileNotFoundError(f"No se encontró: {input_path}")

    if not files:
        print(f"  No se encontraron archivos .xlsx en {input_path}")
        return []

    print(f"  Encontrados: {len(files)} archivos xlsx\n")

    all_stats = []

    for filepath in tqdm(files, unit="xlsx", desc="  Procesando"):
        if dry_run:
            info = inspect_xlsx(filepath)
            all_stats.append(info)
        else:
            stats = xlsx_to_sqlite(filepath, output_dir)
            all_stats.append(stats)

    return all_stats


def print_summary(all_stats: list[dict], dry_run: bool = False):
    """Imprime un resumen del procesamiento."""
    print(f"\n{'='*65}")
    print(f"  RESUMEN — {len(all_stats)} corpus procesados")
    print(f"{'='*65}\n")

    total_articles = 0
    total_rows = 0

    print(f"  {'Corpus':<25} {'Artículos':>10} {'Autores':>10} {'Total filas':>12}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*12}")

    for s in all_stats:
        name = s.get("corpus", s.get("corpus_name", "?"))
        tables = s.get("tables", s.get("sheets", {}))
        articles = tables.get("Article", {})
        if isinstance(articles, dict):
            articles = articles.get("row_count", 0)
        authors = tables.get("Author", {})
        if isinstance(authors, dict):
            authors = authors.get("row_count", 0)
        total = s.get("total_rows", 0)

        total_articles += articles
        total_rows += total

        print(f"  {name:<25} {articles:>10,} {authors:>10,} {total:>12,}")

    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*12}")
    print(f"  {'TOTAL':<25} {total_articles:>10,} {'':<10} {total_rows:>12,}")

    # Errores
    errors = [e for s in all_stats for e in s.get("errors", [])]
    if errors:
        print(f"\n  Errores ({len(errors)}):")
        for err in errors:
            print(f"    - {err}")

    if not dry_run:
        print(f"\n  Bases de datos generadas en: {all_stats[0].get('db_path', '?').rsplit('/', 1)[0]}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Procesar xlsx bibliométricos en lote a SQLite"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Carpeta con xlsx o un archivo específico"
    )
    parser.add_argument(
        "--output", "-o", default="data/db/",
        help="Carpeta de salida para los .db (default: data/db/)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Solo inspeccionar sin crear las bases de datos"
    )
    args = parser.parse_args()

    print(f"\n=== Batch Processor — RAG Bibliométrico ===\n")

    start = time.time()
    stats = batch_process(
        Path(args.input),
        Path(args.output),
        dry_run=args.dry_run,
    )
    elapsed = time.time() - start

    print_summary(stats, dry_run=args.dry_run)
    print(f"\n  Tiempo total: {elapsed:.1f}s\n")
