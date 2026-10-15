"""
networks.py — Construcción de redes bibliométricas
==================================================
Todas las redes usan solo los artículos principales del corpus (ismainarticle = 1).

- Acoplamiento bibliográfico: dos artículos se unen si citan referencias en común
  (peso = número de referencias compartidas). Es la red usada para frentes de
  investigación: las citas directas entre artículos del corpus casi no existen
  (Agrovoltaics: 3 de 1.874 citas).
- Coocurrencia de palabras clave (author_keywords): dos palabras se unen si aparecen
  en el mismo artículo (peso = número de artículos).
- Coautoría: dos autores se unen si firman un mismo artículo (peso = número de artículos).
"""

import itertools
import os
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import networkx as nx

# Palabras clave que aparecen en menos artículos se descartan de la red de palabras clave
KEYWORD_MIN_FREQ = int(os.getenv("KEYWORD_MIN_FREQ", "2"))


@dataclass
class CorpusData:
    """Datos del corpus que necesitan las redes, leídos una sola vez de la BD."""
    articles: dict[str, dict] = field(default_factory=dict)       # SR → {title, year, cited_by, keywords, tos}
    references: dict[str, set] = field(default_factory=dict)      # SR → referencias citadas
    authors: dict[str, list[str]] = field(default_factory=dict)   # SR → AuthorID
    author_names: dict[str, str] = field(default_factory=dict)    # AuthorID → nombre
    author_countries: dict[str, set] = field(default_factory=dict)  # AuthorID → países


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


# Términos de indexación genéricos (vienen mezclados en author_keywords de algunos exportes)
GENERIC_KEYWORDS = {"ARTICLE", "REVIEW", "HUMAN", "HUMANS", "ANIMAL", "ANIMALS", "NONHUMAN",
                    "CONTROLLED STUDY", "PRIORITY JOURNAL", "MALE", "FEMALE", "PROCEDURES", "METABOLISM"}


def normalize_keyword(kw: str) -> str:
    return re.sub(r"\s+", " ", kw.strip().upper())


def split_keywords(raw: str | None) -> list[str]:
    if not raw:
        return []
    seen, out = set(), []
    for kw in str(raw).split(";"):
        kw = normalize_keyword(kw)
        if kw and kw not in seen and kw not in GENERIC_KEYWORDS:
            seen.add(kw)
            out.append(kw)
    return out


def load_corpus(db_path: str) -> CorpusData:
    """Lee de la BD los artículos principales con sus referencias, autores y palabras clave."""
    conn = sqlite3.connect(db_path)
    data = CorpusData()
    # SR repetidos: se conserva la primera fila (ver CLAUDE.md, "SR no es único")
    for sr, title, year, cited, kws in conn.execute(
            "SELECT SR, title, year, cited_by, author_keywords FROM Article WHERE ismainarticle = 1"):
        if sr and sr not in data.articles:
            data.articles[sr] = {"title": title or "", "year": _to_int(year, None),
                                 "cited_by": _to_int(cited), "keywords": split_keywords(kws), "tos": None}

    tables = {r[0].lower() for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "citation" in tables:
        for sr, ref in conn.execute("SELECT SR, SR_ref FROM Citation"):
            if sr in data.articles and ref:
                data.references.setdefault(sr, set()).add(ref)
    if "articleauthor" in tables:
        for sr, aid in conn.execute("SELECT SR, AuthorID FROM ArticleAuthor"):
            if sr in data.articles and aid is not None and str(aid) not in data.authors.get(sr, []):
                data.authors.setdefault(sr, []).append(str(aid))
    if "author" in tables:
        for aid, name, full in conn.execute("SELECT AuthorID, AuthorName, AuthorFullName FROM Author"):
            data.author_names.setdefault(str(aid), full or name or str(aid))
    if "affiliation" in tables:
        for sr, aid, country in conn.execute("SELECT SR, AuthorID, Country FROM Affiliation"):
            if sr in data.articles and country:
                data.author_countries.setdefault(str(aid), set()).add(country)
    if "treeofscience" in tables:
        for sr, tos in conn.execute("SELECT SR, tos FROM TreeOfScience"):
            if sr in data.articles and tos:
                data.articles[sr]["tos"] = tos
    conn.close()
    return data


def coupling_graph(data: CorpusData) -> nx.Graph:
    """Red de acoplamiento bibliográfico entre artículos principales."""
    g = nx.Graph()
    for sr, art in data.articles.items():
        g.add_node(sr, **{k: v for k, v in art.items() if k != "keywords"})
    by_ref = defaultdict(set)
    for sr, refs in data.references.items():
        for ref in refs:
            by_ref[ref].add(sr)
    shared = Counter()
    for citing in by_ref.values():
        for a, b in itertools.combinations(sorted(citing), 2):
            shared[(a, b)] += 1
    # Orden fijo de inserción: con conjuntos de texto el orden cambia en cada proceso (hash aleatorio)
    # y Louvain, aun con semilla, daría comunidades distintas en cada corrida
    for (a, b), w in sorted(shared.items()):
        g.add_edge(a, b, weight=w)
    return g


def keyword_graph(data: CorpusData, min_freq: int = KEYWORD_MIN_FREQ) -> nx.Graph:
    """Red de coocurrencia de palabras clave de autor (solo las que aparecen en ≥ min_freq artículos)."""
    freq = Counter(kw for art in data.articles.values() for kw in art["keywords"])
    keep = {kw for kw, n in freq.items() if n >= min_freq}
    g = nx.Graph()
    for kw in sorted(keep):
        g.add_node(kw, freq=freq[kw])
    pairs = Counter()
    for art in data.articles.values():
        kws = sorted(set(art["keywords"]) & keep)
        for a, b in itertools.combinations(kws, 2):
            pairs[(a, b)] += 1
    for (a, b), w in sorted(pairs.items()):
        g.add_edge(a, b, weight=w)
    return g


def coauthor_graph(data: CorpusData) -> nx.Graph:
    """Red de coautoría entre autores de artículos principales."""
    g = nx.Graph()
    n_articles = Counter()
    pairs = Counter()
    for sr, aids in data.authors.items():
        for aid in aids:
            n_articles[aid] += 1
        for a, b in itertools.combinations(sorted(set(aids)), 2):
            pairs[(a, b)] += 1
    for aid in sorted(n_articles):
        g.add_node(aid)
    for (a, b), w in sorted(pairs.items()):
        g.add_edge(a, b, weight=w)
    for aid, n in n_articles.items():
        g.add_node(aid, name=data.author_names.get(aid, aid), articles=n,
                   countries=sorted(data.author_countries.get(aid, [])))
    return g
