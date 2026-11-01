"""
schema_linker.py — Selección del sub-esquema relevante (Capa 1 completa)
========================================================================
Orquesta el schema_embedder y el ner_extractor para producir un objeto
SchemaContext listo para ser consumido por el Router Agent (Capa 2).

Proceso:
  1. Extrae entidades de la query con NER
  2. Busca tablas relevantes por similitud coseno (schema_embedder)
  3. Aplica MMR (Maximal Marginal Relevance) para diversidad
  4. Determina el canal: sql / rag / hybrid
  5. Recopila las FKs relevantes entre las tablas seleccionadas
  6. Retorna SchemaContext completo

Uso:
    python src/layer1_schema/schema_linker.py --query "autor mas citado"
    python src/layer1_schema/schema_linker.py --query "papers sobre redes de colaboracion en startups"

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import argparse
import os
import re

import numpy as np
from dotenv import load_dotenv

from src.layer1_schema.models import SchemaContext
from src.layer1_schema.ner_extractor import extract_entities
from src.layer1_schema.schema_embedder import (
    FK_MAP,
    SCHEMA_DOCUMENTS,
    get_chroma_collection,
    index_schema,
)

load_dotenv()

SCHEMA_TOP_K              = int(os.getenv("SCHEMA_TOP_K", "4"))
SCHEMA_SIMILARITY_THRESHOLD = float(os.getenv("SCHEMA_SIMILARITY_THRESHOLD", "0.3"))

# ─────────────────────────────────────────────────────────────────────────────
# Columnas relevantes por tabla (subconjunto que el LLM necesita conocer)
# ─────────────────────────────────────────────────────────────────────────────

TABLE_COLUMNS: dict[str, list[str]] = {
    "article": [
        "sr", "title", "abstract", "year", "cited_by",
        "author_keywords", "doi", "document_type", "source_title",
        "ismainarticle",
    ],
    "author": ["authorid", "authorname", "authorfullname", "orcid"],
    "articleauthor": ["sr", "authorid", "authororder", "correspondingauthor"],
    "affiliation": ["sr", "authorid", "affiliation", "country"],
    "scimagodb": ["sr", "sjr", "sjr_best_quartile", "h_index",
                  "citations_doc_2years"],
    "journal": ["journal_id", "source_title", "journal"],
    "citation": ["sr", "sr_ref"],
    "treeofscience": ["sr", "tos", "author", "title", "doi", "author_keywords"],
}

def build_value_hints(db_path: str | None, tables: list[str]) -> list[str]:
    """
    Describe cómo están escritos los valores de texto que más se filtran, con ejemplos reales
    de la BD. Sin esto el LLM busca 'Germany', 'Carsten Agert' o 'AIP Conference Proceedings' y
    la BD guarda 'GERMANY', 'AGERT C.' y 'AIP CONF PROC'.
    """
    if not db_path:
        return []
    import sqlite3

    def top(sql: str) -> str:
        return ", ".join(f"'{r[0]}'" for r in conn.execute(sql).fetchall() if r[0])

    hints = []
    try:
        conn = sqlite3.connect(db_path)
        if "affiliation" in tables:
            hints.append("affiliation.country: nombre del país en inglés y MAYÚSCULAS, ej. " + top(
                "SELECT Country FROM Affiliation WHERE Country IS NOT NULL GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 3")
                + ". Traduce el país de la pregunta al inglés.")
        if "author" in tables:
            hints.append("author.authorname viene abreviado, ej. " + top(
                "SELECT DISTINCT AuthorName FROM Author WHERE AuthorName LIKE '% %.' LIMIT 2")
                + "; un mismo autor puede tener varias filas. Busca autores por APELLIDO: "
                "UPPER(author.authorfullname) LIKE '%APELLIDO%'.")
        if "article" in tables:
            hint = "article.source_title es la abreviatura de la revista, ej. " + top(
                "SELECT source_title FROM Article WHERE ismainarticle = 1 AND source_title IS NOT NULL "
                "GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 3") + "."
            if "journal" in tables:
                hint += (" El nombre completo está en journal.journal, ej. " + top(
                    "SELECT journal FROM journal WHERE journal IS NOT NULL LIMIT 2")
                    + ". Para buscar una revista por su nombre: JOIN journal ON article.source_title = "
                    "journal.source_title y filtra UPPER(journal.journal) LIKE '%NOMBRE%'.")
            hints.append(hint)
        conn.close()
    except Exception:
        return []
    if hints:
        hints.append("Compara texto con UPPER(columna) LIKE '%VALOR EN MAYÚSCULAS%', no con =.")
    return hints


_AUTHOR_NAMES: dict[tuple[str, float], list[tuple[str, frozenset]]] = {}


def _name_tokens(text: str) -> list[str]:
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()
    return [t for t in re.split(r"[^A-Z0-9]+", text) if len(t) >= 2]


def author_hints(db_path: str | None, query: str) -> list[str]:
    """
    Si la pregunta nombra a un autor, da sus formas exactas en la BD. Un mismo autor suele tener
    varias filas en author con formatos distintos ('AGERT, CARSTEN' y 'CARSTEN AGERT', 'MURAT PAŞA
    UYSAL'), y el LLM busca LIKE '%CARSTEN AGERT%', que solo encuentra una de ellas.
    Cuenta como mención que todas las palabras del nombre (2+, sin iniciales, sin tildes y en
    cualquier orden) estén en la pregunta.
    """
    if not db_path or not os.path.exists(db_path):
        return []
    import sqlite3

    key = (db_path, os.path.getmtime(db_path))
    if key not in _AUTHOR_NAMES:
        try:
            conn = sqlite3.connect(db_path)
            names = [r[0] for r in conn.execute(
                "SELECT DISTINCT AuthorFullName FROM Author WHERE AuthorFullName IS NOT NULL")]
            conn.close()
        except Exception:
            return []
        _AUTHOR_NAMES[key] = [(n, frozenset(toks)) for n in names
                              if len(toks := _name_tokens(n)) >= 2 and any(len(t) >= 3 for t in toks)]
    words = set(_name_tokens(query))
    forms = sorted(n for n, toks in _AUTHOR_NAMES[key] if toks <= words)
    if not forms:
        return []
    values = ", ".join("'" + f.replace("'", "''") + "'" for f in forms)
    return [f"La pregunta nombra a un autor que en la BD está escrito como {values}. Fíltralo con "
            f"author.authorfullname IN ({values}), no con LIKE sobre el nombre completo."]


def column_types(db_path: str | None, tables: list[str]) -> dict[str, dict[str, str]]:
    """Tipo declarado de cada columna (PRAGMA table_info), para mostrarlo en el esquema del prompt."""
    if not db_path:
        return {}
    import sqlite3

    out = {}
    try:
        conn = sqlite3.connect(db_path)
        for t in tables:
            out[t] = {r[1].lower(): (r[2] or "").upper() for r in conn.execute(f'PRAGMA table_info("{t}")')}
        conn.close()
    except Exception:
        return {}
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Clasificador de canal (sql / rag / hybrid)
# ─────────────────────────────────────────────────────────────────────────────

# Palabras que indican búsqueda semántica → RAG o hybrid
_RAG_SIGNALS = re.compile(
    r"\b(hablan?\s+de|tratan?\s+de|sobre|relacionad[oa]s?\s+con|"
    r"temas?\s+de|similaridad|parecid[oa]s?\s+a|como\s+este|"
    r"papers?\s+de\s+\w+|encontrar\s+papers?)\b",
    re.IGNORECASE,
)

# Palabras que indican consulta estructurada → SQL puro
_SQL_SIGNALS = re.compile(
    r"\b(cu[aá]ntos?|lista|listar|muestra|muéstrame|top\s+\d+|"
    r"m[aá]s\s+citad[oa]s?|promedio|total|contar|ranking|"
    r"cu[aá]l\s+es\s+el|cu[aá]les\s+son|por\s+a[nñ]o)\b",
    re.IGNORECASE,
)


def _classify_channel(query: str, entities: dict) -> str:
    """
    Determina si la query es mejor atendida por SQL, RAG o ambos.

    Lógica:
    - Si hay señales semánticas Y estructuradas → hybrid
    - Si solo hay señales semánticas → rag
    - En cualquier otro caso → sql (default seguro)
    """
    has_rag = bool(_RAG_SIGNALS.search(query))
    has_sql = bool(_SQL_SIGNALS.search(query))

    # La presencia de top_n, year, quartile fuerza SQL
    has_structured = any(k in entities for k in
                         ("year", "year_range", "quartile", "top_n", "tos_class"))

    if has_rag and not has_sql and not has_structured:
        return "rag"
    if has_rag and (has_sql or has_structured):
        return "hybrid"
    return "sql"


# ─────────────────────────────────────────────────────────────────────────────
# MMR — Maximal Marginal Relevance
# ─────────────────────────────────────────────────────────────────────────────

def _mmr(
    query_embedding: list[float],
    candidate_embeddings: list[list[float]],
    candidate_ids: list[str],
    top_k: int,
    lambda_: float = 0.6,
) -> list[str]:
    """
    Selecciona `top_k` candidatos balanceando relevancia y diversidad.

    MMR(di) = λ · sim(query, di) - (1-λ) · max sim(di, dj) para dj ya seleccionado

    Parámetros
    ----------
    lambda_ : float
        0 = máxima diversidad, 1 = máxima relevancia (default 0.6)
    """
    if not candidate_embeddings:
        return []

    q   = np.array(query_embedding)
    E   = np.array(candidate_embeddings)

    # Similitud coseno query-candidato
    rel = (E @ q) / (np.linalg.norm(E, axis=1) * np.linalg.norm(q) + 1e-9)

    selected: list[int] = []
    remaining = list(range(len(candidate_ids)))

    for _ in range(min(top_k, len(remaining))):
        if not selected:
            # Primera iteración: elegir el más relevante
            best = int(np.argmax(rel))
        else:
            # Penalizar por similitud con los ya seleccionados
            sel_emb = E[selected]
            sim_to_selected = np.max(
                (E[remaining] @ sel_emb.T)
                / (np.linalg.norm(E[remaining], axis=1, keepdims=True)
                   * np.linalg.norm(sel_emb, axis=1) + 1e-9),
                axis=1,
            )
            mmr_scores = (lambda_ * rel[remaining]
                          - (1 - lambda_) * sim_to_selected)
            best = remaining[int(np.argmax(mmr_scores))]

        selected.append(best)
        remaining.remove(best)

    return [candidate_ids[i] for i in selected]


# ─────────────────────────────────────────────────────────────────────────────
# Schema Linker principal
# ─────────────────────────────────────────────────────────────────────────────

def link_schema(query: str, chroma_dir: str = None, top_k: int = SCHEMA_TOP_K) -> SchemaContext:
    """
    Produce un SchemaContext dado una query en lenguaje natural.

    Parámetros
    ----------
    query : str
        Pregunta del usuario en español.
    chroma_dir : str
        Ruta al índice de ChromaDB (opcional).
    top_k : int
        Número de tablas a seleccionar.

    Retorna
    -------
    SchemaContext
        Contexto listo para el Router Agent.
    """
    # ── Paso 1: NER ──────────────────────────────────────────────────────────
    entities = extract_entities(query)

    # ── Paso 2: Búsqueda por similitud en ChromaDB ───────────────────────────
    collection = get_chroma_collection(chroma_dir)
    if collection.count() == 0:
        index_schema(chroma_dir=chroma_dir)


    # Pedir más candidatos de los necesarios para poder aplicar MMR
    n_candidates = min(len(SCHEMA_DOCUMENTS), top_k + 3)
    results = collection.query(
        query_texts=[query],
        n_results=n_candidates,
        include=["documents", "metadatas", "distances", "embeddings"],
    )

    candidate_tables  = [m["table"] for m in results["metadatas"][0]]
    candidate_scores  = [round(1 - d, 4) for d in results["distances"][0]]
    candidate_ids     = [m["table"] for m in results["metadatas"][0]]
    candidate_embeddings = results["embeddings"][0] if results["embeddings"] is not None else []

    # Los índices creados antes pueden traer tablas que ya no existen (p. ej. egosauthors)
    keep = [i for i, t in enumerate(candidate_tables) if t in TABLE_COLUMNS]
    candidate_tables = [candidate_tables[i] for i in keep]
    candidate_scores = [candidate_scores[i] for i in keep]
    candidate_embeddings = [candidate_embeddings[i] for i in keep] if len(candidate_embeddings) else []

    # Filtrar por umbral de similitud mínima
    filtered = [
        (t, s, e) for t, s, e in zip(
            candidate_tables, candidate_scores, candidate_embeddings
        )
        if s >= SCHEMA_SIMILARITY_THRESHOLD
    ]

    if not filtered:
        # Fallback: usar las 3 tablas más relevantes sin umbral
        filtered = list(zip(candidate_tables[:3], candidate_scores[:3],
                            candidate_embeddings[:3]))

    f_tables, f_scores, f_embeddings = zip(*filtered) if filtered else ([], [], [])

    # ── Paso 3: MMR para diversidad ──────────────────────────────────────────
    # Embedding de la query (usar el primer resultado como proxy)
    # ChromaDB no expone el embedding de la query directamente;
    # usamos la media de los candidatos como aproximación conservadora.
    if f_embeddings:
        query_emb = np.mean(f_embeddings, axis=0).tolist()
        selected_tables = _mmr(
            query_embedding=query_emb,
            candidate_embeddings=list(f_embeddings),
            candidate_ids=list(f_tables),
            top_k=top_k,
        )
    else:
        selected_tables = list(f_tables)[:top_k]

    # ── Paso 4: Ajuste por entidades detectadas ───────────────────────────────
    # Si hay entidades que implican tablas específicas, forzar su inclusión

    entity_table_hints = {
        "author":    ["author", "articleauthor"],
        "country":   ["affiliation"],
        "quartile":  ["scimagodb", "article"],
        "tos_class": ["treeofscience"],
        "year":      ["article"],
        "year_range":["article"],
    }

    # Hints por palabras clave en la query (independiente del NER)
    query_lower = query.lower()
    if any(w in query_lower for w in ("autor", "autores", "investigador", "author")):
        for t in ["author", "articleauthor"]:
            if t not in selected_tables:
                selected_tables.append(t)
    if any(w in query_lower for w in ("journal", "revista", "fuente")):
        if "journal" not in selected_tables:
            selected_tables.append("journal")
    if any(w in query_lower for w in ("pais", "país", "afiliacion", "universidad")):
        if "affiliation" not in selected_tables:
            selected_tables.append("affiliation")

    for entity_key, hint_tables in entity_table_hints.items():
        if entity_key in entities:
            for ht in hint_tables:
                if ht not in selected_tables:
                    selected_tables.append(ht)

    # Respetar el límite top_k (las forzadas tienen prioridad al final)
    selected_tables = selected_tables[:top_k + 2]   # permitir 1-2 extras por entidades

    # article siempre va: es la única tabla que distingue artículos principales de referencias
    if "article" not in selected_tables:
        selected_tables.insert(0, "article")

    # ── Paso 5: Recopilar columnas y FKs ─────────────────────────────────────
    relevant_columns = {t: TABLE_COLUMNS.get(t, []) for t in selected_tables}

    relevant_fks: list[str] = []
    for table in selected_tables:
        fks = FK_MAP.get(table, [])
        for fk in fks:
            # Incluir FK solo si ambas tablas están seleccionadas
            other_table = fk.split("→")[-1].strip().split(".")[0]
            if other_table in selected_tables and fk not in relevant_fks:
                relevant_fks.append(fk)

    # ── Paso 6: Canal y confianza ─────────────────────────────────────────────
    channel    = _classify_channel(query, entities)
    confidence = round(float(np.mean(f_scores[:top_k])) if f_scores else 0.5, 4)

    return SchemaContext(
        query=query,
        query_type=channel,
        relevant_tables=selected_tables,
        relevant_columns=relevant_columns,
        foreign_keys=relevant_fks,
        entities=entities,
        confidence=confidence,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera un SchemaContext dado una query en español"
    )
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--top-k", type=int, default=SCHEMA_TOP_K)
    args = parser.parse_args()

    print(f"\nQuery: '{args.query}'\n")
    ctx = link_schema(args.query, top_k=args.top_k)

    print(ctx.to_prompt_string())
    print(f"\nCanal    : {ctx.query_type}")
    print(f"Confianza: {ctx.confidence}")
    print(f"Entidades: {ctx.entities}")