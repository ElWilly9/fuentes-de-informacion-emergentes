"""
embedder.py — Indexación de abstracts y keywords en ChromaDB
============================================================
Crea el índice vectorial para un corpus bibliométrico.
"""

import os
import sqlite3
import time
from pathlib import Path
from typing import Callable, Optional

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

# Configuración por defecto (pueden ser sobrescritas por parámetros)
OLLAMA_BASE_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# nomic-embed-text se entrenó con prefijos de tarea: sin ellos la búsqueda pierde calidad.
# Las colecciones indexadas con prefijo llevan EMBED_PREFIX_TAG en su metadata.
EMBED_PREFIX_TAG = "nomic-search-v1"


class PrefixedOllamaEmbeddingFunction(OllamaEmbeddingFunction):
    """OllamaEmbeddingFunction que añade 'search_document: ' a lo indexado y 'search_query: ' a las búsquedas."""

    def _prefixes(self) -> tuple[str, str]:
        if "nomic" in self.model_name:
            return "search_document: ", "search_query: "
        return "", ""

    def __call__(self, input):
        doc, _ = self._prefixes()
        return super().__call__([doc + t for t in input])

    def embed_query(self, input):
        _, query = self._prefixes()
        return super().__call__([query + t for t in input])


def make_embedding_function(base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_EMBED_MODEL):
    return PrefixedOllamaEmbeddingFunction(url=f"{base_url}/api/embeddings", model_name=model, timeout=120)


def collection_metadata() -> dict:
    return {"hnsw:space": "cosine", "embed_prefix": EMBED_PREFIX_TAG}


def has_prefixed_index(collection) -> bool:
    """False si la colección se indexó antes de los prefijos (hay que reindexarla)."""
    return collection.count() == 0 or (collection.metadata or {}).get("embed_prefix") == EMBED_PREFIX_TAG

def _build_document(title: str, abstract: str, keywords: str) -> str:
    """Construye un documento de texto combinando titulo, abstract y keywords."""
    parts = []
    if title: parts.append(f"Title: {title.strip()}")
    if abstract: parts.append(f"Abstract: {abstract.strip()}")
    if keywords:
        kw_clean = ", ".join(k.strip().lower() for k in keywords.split(";") if k.strip())
        parts.append(f"Keywords: {kw_clean}")
    return "\n\n".join(parts)


def get_abstracts_collection(chroma_dir: Path) -> chromadb.Collection:
    """Crea o recupera la colección ChromaDB en la ruta especificada."""
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(
        name="bibliometric_abstracts",
        embedding_function=make_embedding_function(),
        metadata=collection_metadata(),
    )
    if not has_prefixed_index(collection):
        print(f"[embedder] AVISO: el índice de {chroma_dir} se creó sin los prefijos de nomic; "
              f"reindexa con index_abstracts(..., rebuild=True).")
    return collection


def index_abstracts(
    db_path: Path,
    chroma_dir: Path,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    rebuild: bool = False,
) -> chromadb.Collection:
    """
    Toma los artículos de la BD SQLite y los indexa en ChromaDB.
    Con rebuild=True borra antes la colección (p. ej. un índice creado sin los prefijos de nomic).
    """
    if rebuild:
        client = chromadb.PersistentClient(path=str(chroma_dir))
        if "bibliometric_abstracts" in [c.name for c in client.list_collections()]:
            client.delete_collection("bibliometric_abstracts")
    collection = get_abstracts_collection(chroma_dir)

    # Cargar artículos desde la BD proporcionada
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT SR, title, abstract, author_keywords, ismainarticle
        FROM Article
        WHERE (abstract IS NOT NULL AND abstract != '')
           OR (author_keywords IS NOT NULL AND author_keywords != '')
        ORDER BY ismainarticle DESC  -- con SR repetido, se queda el artículo principal
    """).fetchall()
    conn.close()

    articles = [dict(row) for row in rows]

    if not articles:
        if progress_callback:
            progress_callback("No se encontraron artículos para indexar.", 1.0)
        return collection

    # Preparar documentos
    ids = []
    documents = []
    metadatas = []

    seen_ids: set[str] = set()
    for art in articles:
        # Un SR repetido (artículos distintos con el mismo SR) rompe el upsert por lotes
        if str(art["SR"]).strip() in seen_ids:
            continue
        doc_text = _build_document(
            title=art.get("title", ""),
            abstract=art.get("abstract", ""),
            keywords=art.get("author_keywords", "")
        )
        if not doc_text.strip():
            continue

        sr = str(art["SR"]).strip()
        seen_ids.add(sr)
        ids.append(sr)
        documents.append(doc_text)
        metadatas.append({
            "title":         str(art.get("title", ""))[:200],
            "year":          "N/A", # Metadatos simplificados
            "source_title":  str(art.get("source_title", "")),
            "ismainarticle": int(art.get("ismainarticle") or 0),
        })

    # Indexar en batches
    batch_size = 50
    total_docs = len(documents)

    if progress_callback:
        progress_callback(f"Indexando {total_docs} documentos...", 0.0)

    for i in range(0, total_docs, batch_size):
        batch_ids  = ids[i:i+batch_size]
        batch_docs = documents[i:i+batch_size]
        batch_meta = metadatas[i:i+batch_size]

        collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_meta)

        if progress_callback:
            perc = i / total_docs
            progress_callback(f"Indexando: {i}/{total_docs}", perc)

    if progress_callback:
        progress_callback("Indexación vectorial completada.", 1.0)

    return collection
