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

    embed_fn = OllamaEmbeddingFunction(
        url=f"{OLLAMA_BASE_URL}/api/embeddings",
        model_name=OLLAMA_EMBED_MODEL,
    )

    import httpx
    embed_fn._session = httpx.Client(timeout=120.0)

    collection = client.get_or_create_collection(
        name="bibliometric_abstracts",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def index_abstracts(
    db_path: Path,
    chroma_dir: Path,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> chromadb.Collection:
    """
    Toma los artículos de la BD SQLite y los indexa en ChromaDB.
    """
    collection = get_abstracts_collection(chroma_dir)

    # Cargar artículos desde la BD proporcionada
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT SR, title, abstract, author_keywords
        FROM Article
        WHERE (abstract IS NOT NULL AND abstract != '')
           OR (author_keywords IS NOT NULL AND author_keywords != '')
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
