"""
retriever.py — Búsqueda semántica sobre abstracts
==================================================
Recibe una query en lenguaje natural y retorna los artículos
más relevantes por similitud semántica de sus abstracts/keywords.

Se usa cuando el canal es "rag" o "hybrid".

Uso:
    python src/layer3_rag/retriever.py --query "redes de colaboracion en startups"

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv

from src.layer3_rag.embedder import get_abstracts_collection

load_dotenv()

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
DB_PATH   = os.getenv("DB_PATH", "data/db/bibliometria.db")
# Los abstracts del corpus están en inglés: con la pregunta en español, nomic-embed-text puntúa más alto
# cualquier texto en español. Medido en Q23–Q31: artículo esperado 1.º en 2/9 (español) vs 9/9 (inglés).
RAG_TRANSLATE_QUERY = os.getenv("RAG_TRANSLATE_QUERY", "1") == "1"
# Los abstracts van completos (antes se cortaban a 300 caracteres: en WikiEval eso dejaba la respuesta fuera
# del contexto). Solo si entre todos pasan este total se recortan por igual, para no superar el contexto de
# 8.192 tokens con el que Ollama carga glm4 (si se supera, recorta el principio del prompt sin avisar).
RAG_CONTEXT_BUDGET = int(os.getenv("RAG_CONTEXT_BUDGET", "20000"))

TRANSLATE_PROMPT = """Translate the user's question into English so it can be used as a semantic
search query over English scientific abstracts. Keep technical terms, names, places and numbers.
Reply with the English translation ONLY: no quotes, no explanations."""

_translation_cache: dict[str, str] = {}

# Las palabras clave (autor + índice) no están en el texto indexado (solo el abstract), y muchas preguntas las
# nombran tal cual. Se fusiona el orden semántico con el de coincidencias de palabras clave (RRF, k = 60).
# Solo cuentan las palabras clave raras (en ≤5 % de los artículos principales): con 10 %, términos como
# DRYING o SOLAR ENERGY bajaban Q30 del 1.º al 8.º puesto. Medido en las 18 RAG de plantillas: en el top-5
# 13 → 17 (la que falta, pendulo-R02, tiene dos artículos con el mismo SR); Q23–Q32 igual salvo Q30 1.º → 2.º.
# APAGADA por defecto (2026-11-03): solo ayuda a las preguntas de plantilla que listan palabras clave. Con preguntas
# en lenguaje natural empeora (artículo esperado en el top-5, con / sin fusión): prueba 11/12 vs 12/12, prueba 2
# 10/12 vs 12/12, corpus coffee (1.102 artículos) 10/14 vs 13/14; plantillas 17/18 vs 15/18.
RAG_KEYWORD_FUSION = os.getenv("RAG_KEYWORD_FUSION", "0") == "1"
RRF_K = 60
_keyword_cache: dict[tuple[str, float], dict[str, set[str]]] = {}


@dataclass
class RAGResult:
    """Resultado de la búsqueda semántica."""
    query: str
    articles: list[dict] = field(default_factory=list)
    total_found: int = 0
    success: bool = False
    error: str | None = None
    search_query: str = ""   # texto con el que se buscó en ChromaDB (traducción al inglés)


def to_search_query(query: str) -> str:
    """Traduce la pregunta al inglés para la búsqueda semántica (la respuesta sigue en español)."""
    if not RAG_TRANSLATE_QUERY or not query.strip():
        return query
    if query not in _translation_cache:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                         model=os.getenv("OLLAMA_MODEL", "glm4:9b"), temperature=0.0,
                         num_predict=int(os.getenv("OLLAMA_NUM_PREDICT", "2048")),
                         num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "8192")))
        try:
            text = llm.invoke([{"role": "system", "content": TRANSLATE_PROMPT},
                               {"role": "user", "content": query}]).content
            text = text.strip().splitlines()[0].strip().strip('"“”\'') if text.strip() else ""
        except Exception as e:
            from src.layer2_agent.answer_synthesizer import log_error
            log_error("traducción de la consulta", e)
            text = ""
        _translation_cache[query] = text or query  # si falla, se busca con la pregunta original
    return _translation_cache[query]


def _enrich_with_db(articles: list[dict], db_path: str) -> list[dict]:
    """
    Enriquece los resultados de ChromaDB con datos completos de la BD.
    ChromaDB guarda metadata limitada — la BD tiene todo.
    """
    if not articles:
        return articles

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # TRIM: el SR de los artículos sin revista termina en espacio ("SILVA JESM, 2024, ") y Chroma guarda el
    # id sin él; con "SR = ?" 160 de 487 principales llegaban al prompt sin abstract, año ni keywords.
    for art in articles:
        sr = art.get("SR", "")
        row = conn.execute(
            "SELECT title, abstract, year, cited_by, author_keywords, "
            "source_title, document_type FROM Article WHERE TRIM(SR) = TRIM(?) "
            "ORDER BY ismainarticle DESC",
            (sr,)
        ).fetchone()

        if row:
            row_dict = dict(row)
            art["title"]           = row_dict.get("title", art.get("title", ""))
            art["abstract"]        = row_dict.get("abstract", "")
            art["year"]            = row_dict.get("year", "")
            art["cited_by"]        = row_dict.get("cited_by", "0")
            art["author_keywords"] = row_dict.get("author_keywords", "")
            art["source_title"]    = row_dict.get("source_title", "")
            art["document_type"]   = row_dict.get("document_type", "")

    conn.close()
    return articles


def _ensure_main_flag(collection, db_path: str) -> None:
    """
    Índices creados antes no guardan ismainarticle en la metadata. Se completa en el
    sitio (sin recalcular embeddings) consultando la BD por SR.
    """
    sample = collection.get(limit=1, include=["metadatas"])
    if not sample["ids"] or "ismainarticle" in (sample["metadatas"][0] or {}):
        return
    conn = sqlite3.connect(db_path)
    flags = {str(sr).strip(): int(m or 0) for sr, m in conn.execute(
        "SELECT SR, MAX(ismainarticle) FROM Article GROUP BY SR")}
    conn.close()
    data = collection.get(include=["metadatas"])
    for i in range(0, len(data["ids"]), 500):
        ids = data["ids"][i:i + 500]
        metas = [{**(m or {}), "ismainarticle": flags.get(sr, 0)}
                 for sr, m in zip(ids, data["metadatas"][i:i + 500])]
        collection.update(ids=ids, metadatas=metas)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", text).strip() + " "


def _rare_keywords(db_path: str) -> dict[str, set[str]]:
    """SR → palabras clave normalizadas de cada artículo principal que están en ≤5 % del corpus."""
    key = (db_path, os.path.getmtime(db_path))
    if key not in _keyword_cache:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT SR, author_keywords, index_keywords FROM Article "
                            "WHERE ismainarticle = 1").fetchall()
        conn.close()
        kws: dict[str, set[str]] = {}
        for sr, a, b in rows:
            words = {_norm(k).strip() for k in f"{a or ''};{b or ''}".split(";")}
            kws.setdefault(str(sr).strip(), set()).update(w for w in words if len(w) >= 4)
        df: dict[str, int] = {}
        for words in kws.values():
            for w in words:
                df[w] = df.get(w, 0) + 1
        max_df = max(2, 0.05 * len(kws))
        _keyword_cache[key] = {sr: {w for w in words if df[w] <= max_df} for sr, words in kws.items()}
    return _keyword_cache[key]


def _fuse_keywords(articles: list[dict], texts: list[str], db_path: str) -> list[dict]:
    """Reordena los artículos (ya ordenados por similitud) fusionando con las coincidencias de palabras clave."""
    kws = _rare_keywords(db_path)
    text = "".join(_norm(t) for t in texts)
    hits = {a["SR"]: sum(f" {w} " in text for w in kws.get(a["SR"], ())) for a in articles}
    lexical = sorted((a["SR"] for a in articles if hits[a["SR"]]), key=lambda sr: -hits[sr])
    score = {a["SR"]: 1 / (RRF_K + i) for i, a in enumerate(articles, 1)}
    for i, sr in enumerate(lexical, 1):
        score[sr] += 1 / (RRF_K + i)
    return sorted(articles, key=lambda a: -score[a["SR"]])


def _query(collection, query: str, n: int, where: dict | None, exclude: set[str]) -> list[dict]:
    """Consulta ChromaDB y devuelve artículos ordenados por similitud, sin los SR excluidos."""
    n = min(n + len(exclude), collection.count())
    if n <= 0:
        return []
    kwargs = {"where": where} if where else {}
    try:
        res = collection.query(query_texts=[query], n_results=n,
                               include=["documents", "metadatas", "distances"], **kwargs)
    except Exception:
        return []  # p. ej. ningún documento cumple el filtro
    out = []
    for sr, doc, meta, dist in zip(res["ids"][0], res["documents"][0],
                                   res["metadatas"][0], res["distances"][0]):
        if sr in exclude:
            continue
        out.append({
            "SR":           sr,
            "score":        round(1 - dist, 4),  # distancia coseno → similitud
            "title":        meta.get("title", ""),
            "year":         meta.get("year", ""),
            "cited_by":     meta.get("cited_by", "0"),
            "source_title": meta.get("source_title", ""),
            "snippet":      doc[:200] if doc else "",
        })
    return out


def search_by_origin(query: str, chroma_dir, db_path, origin: str = "principal",
                     top_k: int = RAG_TOP_K, exclude_srs=()) -> RAGResult:
    """
    Búsqueda semántica restringida a artículos principales del corpus (origin="principal",
    ismainarticle = 1) o a referencias citadas (origin="referencia", ismainarticle = 0).

    No se mezclan por similitud: las preguntas en español puntúan más alto cualquier texto en
    español, así que las referencias en español desplazarían a los artículos principales.
    Cada artículo lleva `origen` para que la respuesta pueda distinguirlos.
    """
    try:
        collection = get_abstracts_collection(chroma_dir)
        if collection.count() == 0:
            return RAGResult(query=query, success=False,
                             error="El índice de abstracts está vacío. Ejecuta: python src/layer3_rag/embedder.py")
        _ensure_main_flag(collection, str(db_path))
        exclude = {str(s).strip() for s in exclude_srs}

        flag = 1 if origin == "principal" else 0
        search_query = to_search_query(query)
        if RAG_KEYWORD_FUSION and origin == "principal":
            # Todos los principales por similitud (son cientos), para que la fusión pueda subir cualquiera
            candidates = _query(collection, search_query, collection.count(), {"ismainarticle": flag}, exclude)
            candidates = _fuse_keywords(candidates, [query, search_query], str(db_path))
        else:
            candidates = _query(collection, search_query, top_k, {"ismainarticle": flag}, exclude)
        articles = [{**a, "origen": origin} for a in candidates[:top_k]]
        for i, a in enumerate(articles, 1):
            a["rank"] = i
        articles = _enrich_with_db(articles, db_path)
        return RAGResult(query=query, articles=articles, total_found=len(articles), success=True,
                         search_query=search_query)
    except Exception as e:
        return RAGResult(query=query, error=str(e), success=False)


def search_articles(query: str, chroma_dir: Path, db_path: Path, top_k: int = RAG_TOP_K) -> RAGResult:
    """
    Busca artículos relevantes por similitud semántica.

    Parámetros
    ----------
    query : str
        Pregunta o tema de búsqueda en lenguaje natural.
    top_k : int
        Número de artículos a retornar.

    Retorna
    -------
    RAGResult
        Con la lista de artículos encontrados y sus metadatos.
    """
    try:
        collection = get_abstracts_collection(chroma_dir)

        if collection.count() == 0:
            return RAGResult(
                query=query,
                error="El índice de abstracts está vacío. "
                      "Ejecuta: python src/layer3_rag/embedder.py",
                success=False,
            )

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        articles = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            score = round(1 - dist, 4)  # distancia coseno → similitud
            articles.append({
                "rank":      i + 1,
                "SR":        results["ids"][0][i],
                "score":     score,
                "title":     meta.get("title", ""),
                "year":      meta.get("year", ""),
                "cited_by":  meta.get("cited_by", "0"),
                "source_title": meta.get("source_title", ""),
                "snippet":   doc[:200] if doc else "",
            })

        # Enriquecer con datos completos de la BD
        articles = _enrich_with_db(articles, db_path)

        return RAGResult(
            query=query,
            articles=articles,
            total_found=len(articles),
            success=True,
        )

    except Exception as e:
        return RAGResult(
            query=query,
            error=str(e),
            success=False,
        )


def format_rag_context(rag_result: RAGResult, budget: int | None = None) -> str:
    """
    Formatea los resultados RAG como contexto para el LLM.
    Este texto se incluye en el prompt del answer_synthesizer
    cuando el canal es rag o hybrid. `budget` (caracteres de abstracts) reemplaza a
    RAG_CONTEXT_BUDGET cuando el contexto comparte el prompt con otras fuentes (híbrido).
    """
    if not rag_result.success or not rag_result.articles:
        return "(sin resultados de búsqueda semántica)"

    budget = budget or RAG_CONTEXT_BUDGET
    total = sum(len(a.get("abstract") or "") for a in rag_result.articles)
    per_article = None if total <= budget else max(300, budget // len(rag_result.articles))

    lines = []
    for art in rag_result.articles:
        origen = {"principal": " [ARTÍCULO PRINCIPAL DEL CORPUS]",
                  "referencia": " [REFERENCIA CITADA: no es artículo principal del corpus]",
                  "anterior": " [MOSTRADO EN LA RESPUESTA ANTERIOR]"}.get(art.get("origen"), "")
        lines.append(f"--- Artículo {art['rank']} (similitud: {art['score']}){origen} ---")
        lines.append(f"Título: {art.get('title', 'N/A')}")
        lines.append(f"Año: {art.get('year', 'N/A')} | Citas: {art.get('cited_by', '0')}")
        lines.append(f"Revista: {art.get('source_title', 'N/A')}")
        if art.get("authors"):
            lines.append(f"Autores: {art['authors']}")
        if art.get("countries"):
            lines.append(f"Países: {art['countries']}")

        kw = art.get("author_keywords", "")
        if kw:
            lines.append(f"Keywords: {kw}")

        abstract = art.get("abstract", "")
        if abstract:
            if per_article and len(abstract) > per_article:
                abstract = abstract[:per_article] + "..."
            lines.append(f"Abstract: {abstract}")

        lines.append("")

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Búsqueda semántica sobre abstracts del corpus"
    )
    parser.add_argument("--query", "-q", type=str, required=True)
    parser.add_argument("--top-k", "-k", type=int, default=RAG_TOP_K)
    args = parser.parse_args()

    print(f"\n=== RAG Retriever — Capa 3 ===")
    print(f"   Query: '{args.query}'")
    print(f"   Top-K: {args.top_k}\n")

    result = search_articles(args.query, top_k=args.top_k)

    if result.success:
        print(f"   {result.total_found} artículos encontrados\n")
        for art in result.articles:
            score_bar = "█" * int(art["score"] * 20) + "░" * (20 - int(art["score"] * 20))
            print(f"   [{art['rank']}] {score_bar} {art['score']}")
            print(f"       {art.get('title', 'N/A')[:80]}")
            print(f"       {art.get('year', '?')} | {art.get('source_title', '?')} | citas: {art.get('cited_by', '0')}")
            kw = art.get("author_keywords", "")
            if kw:
                print(f"       Keywords: {kw[:80]}")
            print()
    else:
        print(f"   Error: {result.error}")
