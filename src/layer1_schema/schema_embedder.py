"""
schema_embedder.py — Embeddings del esquema SQL
================================================
Genera y almacena embeddings de cada tabla/columna de la BD para que
el schema linker pueda encontrar las tablas relevantes dado una query
en lenguaje natural.

Cada tabla se representa como un documento de texto que describe:
  - Nombre de la tabla
  - Qué información contiene (descripción semántica)
  - Sus columnas con descripción de cada una
  - Sus relaciones FK

Estos documentos se embeben con nomic-embed-text (vía Ollama) y se
guardan en ChromaDB para búsqueda por similitud coseno.

Uso:
    # Indexar el esquema (se corre UNA vez o al cambiar la BD)
    python src/layer1_schema/schema_embedder.py

    # Buscar tablas relevantes para una query
    python src/layer1_schema/schema_embedder.py --query "autor mas citado"

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import argparse
import os
import sys
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuración (leída desde .env con fallbacks)
# ─────────────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL",   "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_DIR        = os.getenv("CHROMA_DIR",        "chroma_db")
SCHEMA_COLLECTION = "bibliometric_schema"   # colección separada de abstracts


# ─────────────────────────────────────────────────────────────────────────────
# Definición del esquema con descripciones semánticas
# ─────────────────────────────────────────────────────────────────────────────
# Cada entrada es un dict con:
#   id          → identificador único del documento en ChromaDB
#   table       → nombre exacto de la tabla en SQLite
#   text        → texto que se va a embeber (descripción rica en español)
#   metadata    → metadatos para filtrado posterior

SCHEMA_DOCUMENTS = [
    {
        "id":    "table_article",
        "table": "article",
        "text": (
            "Tabla article: contiene los artículos científicos del corpus bibliométrico. "
            "Cada fila es un paper único identificado por sr (clave primaria). "
            "Columnas principales: sr (identificador único del artículo), title (título del paper), "
            "abstract (resumen del artículo), year (año de publicación), "
            "cited_by (número de citas recibidas, útil para medir impacto e influencia), "
            "author_keywords (palabras clave del autor), doi (identificador digital), "
            "document_type (tipo: article, review, etc), "
            "source_title (nombre abreviado de la revista), "
            "ismainarticle (1 si es artículo principal del corpus). "
            "Usar para: contar artículos, filtrar por año, buscar por tipo de documento, "
            "obtener los más citados, analizar tendencias temporales."
        ),
        "metadata": {
            "table": "article",
            "pk": "sr",
            "type": "main",
            "keywords": "articulo paper titulo abstract año citado impacto revista journal"
        }
    },
    {
        "id":    "table_author",
        "table": "author",
        "text": (
            "Tabla author: contiene los investigadores y autores del corpus. "
            "Columnas: authorid (clave primaria, ID de Scopus), "
            "authorname (nombre corto: Apellido Iniciales), "
            "authorfullname (nombre completo del investigador), "
            "orcid (identificador ORCID del investigador). "
            "Usar para: buscar un autor específico por nombre, listar todos los autores, "
            "identificar investigadores por país, buscar por ORCID."
        ),
        "metadata": {
            "table": "author",
            "pk": "authorid",
            "type": "entity",
            "keywords": "autor investigador nombre orcid investigador colombiano"
        }
    },
    {
        "id":    "table_articleauthor",
        "table": "articleauthor",
        "text": (
            "Tabla articleauthor: tabla de relación many-to-many entre artículos y autores. "
            "Conecta cada artículo con sus autores. "
            "Columnas: sr (FK a article), authorid (FK a author), "
            "authororder (posición del autor: 1 = primer autor, 2 = segundo, etc), "
            "correspondingauthor (1 si es el autor de correspondencia). "
            "Usar para: saber cuántos artículos tiene un autor, quién es el primer autor, "
            "encontrar colaboraciones, contar publicaciones por autor, "
            "identificar el autor más prolífico o más citado."
        ),
        "metadata": {
            "table": "articleauthor",
            "pk": "sr,authorid",
            "type": "relation",
            "keywords": "autor articulo relacion coautoria prolífico primer autor"
        }
    },
    {
        "id":    "table_affiliation",
        "table": "affiliation",
        "text": (
            "Tabla affiliation: contiene las afiliaciones institucionales de los autores. "
            "Columnas: sr (FK a article), authorid (FK a author), "
            "affiliation (nombre de la universidad, empresa o institución), "
            "country (país de la afiliación). "
            "Usar para: buscar autores de un país específico, "
            "identificar universidades o instituciones más productivas, "
            "analizar colaboración internacional."
        ),
        "metadata": {
            "table": "affiliation",
            "pk": "id",
            "type": "entity",
            "keywords": "afiliacion universidad pais institución Colombia internacional"
        }
    },
    {
        "id":    "table_scimagodb",
        "table": "scimagodb",
        "text": (
            "Tabla scimagodb: contiene métricas de calidad de las revistas científicas según Scimago. "
            "Columnas: sr (FK a article), sjr (SCImago Journal Rank), "
            "sjr_best_quartile (cuartil: Q1, Q2, Q3, Q4 — Q1 es el mejor), "
            "h_index (índice H de la revista), "
            "citations_doc_2years (citas promedio por documento en 2 años). "
            "Usar para: filtrar artículos por cuartil (Q1, Q2), "
            "encontrar revistas de alto impacto, analizar calidad de las publicaciones, "
            "listar journals Q1, comparar impacto de revistas."
        ),
        "metadata": {
            "table": "scimagodb",
            "pk": "sr",
            "type": "metrics",
            "keywords": "cuartil Q1 Q2 impacto sjr scimago revista calidad indice"
        }
    },
    {
        "id":    "table_journal",
        "table": "journal",
        "text": (
            "Tabla journal: catálogo de revistas científicas del corpus. "
            "Columnas: journal_id (clave primaria autoincremental), "
            "source_title (nombre abreviado de la revista), "
            "journal (nombre completo de la revista). "
            "Usar para: buscar por nombre de revista, "
            "obtener el nombre completo de una revista abreviada, "
            "listar todas las revistas del corpus."
        ),
        "metadata": {
            "table": "journal",
            "pk": "journal_id",
            "type": "entity",
            "keywords": "revista journal fuente publicacion nombre"
        }
    },
    {
        "id":    "table_citation",
        "table": "citation",
        "text": (
            "Tabla citation: red de citas internas entre artículos del corpus. "
            "Columnas: sr (artículo citante, FK a article), "
            "sr_ref (artículo citado, FK a article). "
            "Cada fila indica que el artículo sr cita al artículo sr_ref. "
            "Usar para: analizar redes de citación, encontrar artículos semilla, "
            "calcular in-degree (veces citado dentro del corpus), "
            "identificar artículos altamente referenciados internamente."
        ),
        "metadata": {
            "table": "citation",
            "pk": "sr,sr_ref",
            "type": "network",
            "keywords": "citas red citacion referencia semilla impacto interno"
        }
    },
    {
        "id":    "table_treeofscience",
        "table": "treeofscience",
        "text": (
            "Tabla treeofscience: resultados del algoritmo Tree of Science del profesor Robledo. "
            "Clasifica los artículos en tres roles dentro de la estructura del conocimiento. "
            "Columnas: sr (FK a article), "
            "tos (clasificación: 'root' = artículos fundacionales, "
            "'trunk' = artículos estructurales, "
            "'leaf' = artículos de frontera), "
            "author (autor del artículo según ToS), title (título), "
            "doi (identificador), author_keywords (palabras clave). "
            "Usar para: encontrar artículos fundacionales (root), "
            "identificar la estructura del campo, artículos de frontera (leaf), "
            "análisis del árbol de la ciencia."
        ),
        "metadata": {
            "table": "treeofscience",
            "pk": "sr",
            "type": "analysis",
            "keywords": "tree of science raiz tronco hoja fundacional frontera robledo algoritmo"
        }
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Relaciones FK (para inyectar en el prompt del LLM)
# ─────────────────────────────────────────────────────────────────────────────
FOREIGN_KEYS = [
    "articleauthor.sr → article.sr",
    "articleauthor.authorid → author.authorid",
    "affiliation.sr → article.sr",
    "affiliation.authorid → author.authorid",
    "scimagodb.sr → article.sr",
    "citation.sr → article.sr",
    "citation.sr_ref → article.sr",
    "treeofscience.sr → article.sr",
]

# Mapa de FK por tabla (para el schema linker)
FK_MAP: dict[str, list[str]] = {}
for fk in FOREIGN_KEYS:
    tabla = fk.split(".")[0]
    FK_MAP.setdefault(tabla, []).append(fk)
# Article también aparece como destino
FK_MAP["article"] = [fk for fk in FOREIGN_KEYS if "→ article.sr" in fk]


# ─────────────────────────────────────────────────────────────────────────────
# Cliente ChromaDB
# ─────────────────────────────────────────────────────────────────────────────

def get_chroma_collection(chroma_dir: str = CHROMA_DIR) -> chromadb.Collection:
    """
    Crea o recupera la colección ChromaDB para el esquema SQL.
    Usa OllamaEmbeddingFunction para que todos los embeddings pasen
    por el mismo modelo (nomic-embed-text).
    """
    client = chromadb.PersistentClient(path=chroma_dir)


    embed_fn = OllamaEmbeddingFunction(
        url=f"{OLLAMA_BASE_URL}/api/embeddings",
        model_name=OLLAMA_EMBED_MODEL,
    )

    collection = client.get_or_create_collection(
        name=SCHEMA_COLLECTION,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},   # similitud coseno
    )
    return collection


# ─────────────────────────────────────────────────────────────────────────────
# Indexación
# ─────────────────────────────────────────────────────────────────────────────

def index_schema(chroma_dir: str = CHROMA_DIR, force: bool = False) -> chromadb.Collection:
    """
    Embebe los documentos del esquema y los guarda en ChromaDB.

    Parámetros
    ----------
    chroma_dir : str
        Ruta al índice de ChromaDB.
    force : bool
        Si True, borra y re-indexa aunque ya existan los documentos.

    Retorna
    -------
    chromadb.Collection
        Colección lista para búsqueda.
    """
    collection = get_chroma_collection(chroma_dir)


    # Verificar si ya están indexados
    existing = collection.count()
    if existing > 0 and not force:
        print(f"   Esquema ya indexado ({existing} documentos). "
              f"Usa --force para re-indexar.")
        return collection

    if force and existing > 0:
        print(f"   Borrando {existing} documentos existentes...")
        collection.delete(ids=[d["id"] for d in SCHEMA_DOCUMENTS])

    print(f"   Indexando {len(SCHEMA_DOCUMENTS)} tablas con {OLLAMA_EMBED_MODEL}...")
    for doc in SCHEMA_DOCUMENTS:
        collection.upsert(
            ids=[doc["id"]],
            documents=[doc["text"]],
            metadatas=[doc["metadata"]],
        )
        print(f"   [OK] {doc['table']}")

    print(f"\n   Total en coleccion '{SCHEMA_COLLECTION}': {collection.count()} docs")
    return collection


# ─────────────────────────────────────────────────────────────────────────────
# Búsqueda
# ─────────────────────────────────────────────────────────────────────────────

def search_schema(query: str, chroma_dir: str = CHROMA_DIR, top_k: int = 4) -> list[dict]:
    """
    Busca las tablas más relevantes para una query en lenguaje natural.

    Parámetros
    ----------
    query : str
        Pregunta del usuario en español.
    chroma_dir : str
        Ruta al índice de ChromaDB.
    top_k : int
        Número de tablas a retornar.

    Retorna
    -------
    list[dict]
        Lista de resultados ordenados por relevancia, cada uno con:
        {table, text, score, metadata}
    """
    collection = get_chroma_collection(chroma_dir)


    if collection.count() == 0:
        raise RuntimeError(
            "El esquema no está indexado. "
            "Corre primero: python src/layer1_schema/schema_embedder.py"
        )

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        output.append({
            "rank":     i + 1,
            "table":    meta["table"],
            "score":    round(1 - dist, 4),   # distancia coseno → similitud
            "text":     doc[:120] + "...",
            "metadata": meta,
        })

    return output


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Indexa el esquema SQL en ChromaDB con embeddings"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Forzar re-indexación aunque ya existan los embeddings"
    )
    parser.add_argument(
        "--query", type=str, default=None,
        help="Query de prueba para buscar tablas relevantes"
    )
    parser.add_argument(
        "--top-k", type=int, default=4,
        help="Número de tablas a retornar en la búsqueda (default: 4)"
    )
    args = parser.parse_args()

    print("=== Schema Embedder ===\n")

    # Paso 1: indexar
    print("1. Indexando esquema...")
    index_schema(force=args.force)

    # Paso 2: buscar si se pasó una query
    if args.query:
        print(f"\n2. Buscando tablas para: '{args.query}'")
        resultados = search_schema(args.query, top_k=args.top_k)
        print(f"\n{'Rank':<5} {'Tabla':<20} {'Score':<8} Descripcion")
        print("-" * 70)
        for r in resultados:
            print(f"{r['rank']:<5} {r['table']:<20} {r['score']:<8} {r['text']}")
