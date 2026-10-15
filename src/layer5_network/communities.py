"""
communities.py — Comunidades, centralidad y puentes
===================================================
- Frentes de investigación: comunidades Louvain sobre la red de acoplamiento bibliográfico.
- Temas: comunidades Louvain sobre la red de coocurrencia de palabras clave.
- Artículos puente: mayor intermediación (betweenness) en la red de acoplamiento.
- Autores puente: autores cuyos artículos están en dos o más frentes distintos, y autores
  con intermediación > 0 en la red de coautoría (en estos corpus la coautoría está muy
  fragmentada, así que la intermediación suele ser 0 para casi todos).

Louvain usa una semilla fija (LOUVAIN_SEED) para que el resultado sea reproducible.
"""

import os
from collections import Counter
from functools import lru_cache
from pathlib import Path

import networkx as nx

from src.layer5_network.networks import (
    CorpusData, load_corpus, coupling_graph, keyword_graph, coauthor_graph,
)
from src.layer5_network.trends import annual_series, growth_indicators

LOUVAIN_SEED = int(os.getenv("LOUVAIN_SEED", "42"))
LOUVAIN_RESOLUTION = float(os.getenv("LOUVAIN_RESOLUTION", "1.0"))
MIN_COMMUNITY_SIZE = int(os.getenv("MIN_COMMUNITY_SIZE", "3"))   # frentes más pequeños se agrupan como "otros"


def louvain(g: nx.Graph) -> list[set]:
    """Comunidades Louvain de los nodos con al menos una arista, de mayor a menor tamaño."""
    sub = g.subgraph([n for n in g if g.degree(n) > 0])
    if sub.number_of_edges() == 0:
        return []
    comms = nx.community.louvain_communities(sub, weight="weight", resolution=LOUVAIN_RESOLUTION,
                                             seed=LOUVAIN_SEED)
    return sorted(comms, key=lambda c: (-len(c), sorted(c)[0]))


def _distinctive_keywords(members: set, data: CorpusData, top: int = 6) -> list[str]:
    """
    Palabras clave más frecuentes en el grupo, ponderadas por cuánto se concentran en él.
    Se omiten las que están en más del 30 % del corpus (p. ej. PROJECT MANAGEMENT en la sesión ai):
    describen el corpus entero, no el frente.
    """
    inside = Counter(kw for sr in members for kw in data.articles[sr]["keywords"])
    overall = Counter(kw for art in data.articles.values() for kw in art["keywords"])
    common = {kw for kw, n in overall.items() if n > 0.3 * len(data.articles)}
    scored = sorted((kw for kw in inside if kw not in common),
                    key=lambda kw: (-(inside[kw] * inside[kw] / overall[kw]), kw))
    return [kw for kw in scored if inside[kw] >= 2][:top] or scored[:top]


def _front_summary(idx: int, members: set, data: CorpusData, start: int, end: int) -> dict:
    arts = sorted(members, key=lambda sr: (-data.articles[sr]["cited_by"], sr))
    series = annual_series([data.articles[sr]["year"] for sr in members], start, end)
    tos = Counter(data.articles[sr]["tos"] for sr in members if data.articles[sr]["tos"])
    return {
        "id": idx,
        "size": len(members),
        "keywords": _distinctive_keywords(members, data),
        "articles": [{"sr": sr, "title": data.articles[sr]["title"], "year": data.articles[sr]["year"],
                      "cited_by": data.articles[sr]["cited_by"]} for sr in arts],
        "citations": sum(data.articles[sr]["cited_by"] for sr in members),
        "trend": growth_indicators(series),
        "series": series,
        "tos_branches": dict(tos.most_common()),
    }


@lru_cache(maxsize=8)
def _analyze(db_path: str, mtime: float) -> dict:
    data = load_corpus(db_path)
    years = [a["year"] for a in data.articles.values() if a["year"]]
    start, end = (min(years), max(years)) if years else (None, None)

    # ── Frentes (acoplamiento) ──
    cg = coupling_graph(data)
    comms = louvain(cg)
    fronts, others = [], set()
    for c in comms:
        if len(c) >= MIN_COMMUNITY_SIZE:
            fronts.append(_front_summary(len(fronts) + 1, c, data, start, end))
        else:
            others |= c
    front_of = {a["sr"]: f["id"] for f in fronts for a in f["articles"]}
    isolated = [sr for sr in cg if cg.degree(sr) == 0]
    modularity = None
    if comms:
        sub = cg.subgraph(set().union(*comms))
        modularity = round(nx.community.modularity(sub, comms, weight="weight"), 3)

    # Artículos puente: intermediación en la red de acoplamiento
    btw = nx.betweenness_centrality(cg, weight=None, normalized=True)
    bridge_articles = []
    for sr, b in sorted(btw.items(), key=lambda kv: -kv[1]):
        if b <= 0 or len(bridge_articles) >= 10:
            break
        neigh_fronts = {front_of[n] for n in cg.neighbors(sr) if n in front_of}
        bridge_articles.append({"sr": sr, "title": data.articles[sr]["title"],
                                "year": data.articles[sr]["year"], "betweenness": round(b, 3),
                                "degree": cg.degree(sr), "front": front_of.get(sr),
                                "connects_fronts": sorted(neigh_fronts)})

    # ── Temas (palabras clave) ──
    kg = keyword_graph(data)
    theme_sets = [c for c in louvain(kg) if len(c) >= MIN_COMMUNITY_SIZE]
    # Cada artículo se asigna al tema con el que comparte más palabras clave (si no, una palabra
    # muy común como PROJECT MANAGEMENT metería casi todo el corpus en un solo tema)
    theme_articles = {i: [] for i in range(len(theme_sets))}
    for sr, a in data.articles.items():
        overlap = [len(set(a["keywords"]) & c) for c in theme_sets]
        if overlap and max(overlap) > 0:
            theme_articles[overlap.index(max(overlap))].append(sr)
    themes, theme_of = [], {}
    for i, c in enumerate(theme_sets):
        arts = theme_articles[i]
        if len(arts) < MIN_COMMUNITY_SIZE:  # temas con menos artículos no se reportan (numeración sin huecos)
            continue
        kws = sorted(c, key=lambda k: (-kg.nodes[k]["freq"], k))
        series = annual_series([data.articles[sr]["year"] for sr in arts], start, end)
        themes.append({"id": len(themes) + 1, "keywords": kws[:8], "n_keywords": len(c),
                       "n_articles": len(arts), "trend": growth_indicators(series), "series": series})
        theme_of.update({kw: themes[-1]["id"] for kw in c})

    # Palabras clave individuales con su tendencia (para "temas emergentes")
    kw_trends = []
    for kw in kg:
        arts = [a["year"] for a in data.articles.values() if kw in a["keywords"]]
        kw_trends.append({"keyword": kw, **growth_indicators(annual_series(arts, start, end))})

    # ── Coautoría y autores puente ──
    ag = coauthor_graph(data)
    comps = sorted(nx.connected_components(ag), key=len, reverse=True)
    abtw = nx.betweenness_centrality(ag, weight=None, normalized=True) if ag.number_of_nodes() else {}
    author_fronts: dict[str, set] = {}
    for sr, aids in data.authors.items():
        if sr in front_of:
            for aid in aids:
                author_fronts.setdefault(aid, set()).add(front_of[sr])
    def author_row(aid):
        return {"author_id": aid, "name": ag.nodes[aid].get("name", aid),
                "articles": ag.nodes[aid].get("articles", 0),
                # con cientos de autores la intermediación normalizada es muy pequeña: 2 cifras significativas
                "fronts": sorted(author_fronts.get(aid, set())), "betweenness": float(f"{abtw.get(aid, 0):.2g}"),
                "coauthors": ag.degree(aid), "countries": ag.nodes[aid].get("countries", [])}

    # Autor puente: publica en dos o más frentes distintos
    bridge_authors = sorted((author_row(a) for a in ag if len(author_fronts.get(a, ())) >= 2),
                            key=lambda a: (-len(a["fronts"]), -a["articles"], a["name"]))
    # Intermediarios de colaboración: intermediación > 0 en la red de coautoría
    brokers = sorted((author_row(a) for a in ag if abtw.get(a, 0) > 0),
                     key=lambda a: (-a["betweenness"], a["name"]))
    top_authors = sorted(ag.nodes, key=lambda a: (-ag.nodes[a].get("articles", 0), -ag.degree(a)))[:10]

    total_series = annual_series(years, start, end)
    return {
        "n_articles": len(data.articles),
        "years": (start, end),
        "total_series": total_series,
        "total_trend": growth_indicators(total_series),
        "coupling": {"nodes": cg.number_of_nodes(), "edges": cg.number_of_edges(),
                     "connected_articles": cg.number_of_nodes() - len(isolated),
                     "isolated": len(isolated), "modularity": modularity,
                     "small_groups_articles": len(others)},
        "fronts": fronts,
        "bridge_articles": bridge_articles,
        "keywords": {"nodes": kg.number_of_nodes(), "edges": kg.number_of_edges()},
        "themes": themes,
        "keyword_trends": kw_trends,
        "coauthorship": {"authors": ag.number_of_nodes(), "edges": ag.number_of_edges(),
                         "components": len(comps), "largest_component": len(comps[0]) if comps else 0,
                         "authors_2plus": sum(1 for a in ag if ag.nodes[a].get("articles", 0) >= 2)},
        "bridge_authors": bridge_authors[:15],
        "brokers": brokers[:10],
        "top_authors": [{"author_id": a, "name": ag.nodes[a].get("name", a),
                         "articles": ag.nodes[a].get("articles", 0), "coauthors": ag.degree(a),
                         "countries": ag.nodes[a].get("countries", [])} for a in top_authors],
        # Pertenencia de cada nodo (para colorear la visualización)
        "front_of": front_of,
        "theme_of": theme_of,
        "author_fronts": {a: sorted(f) for a, f in author_fronts.items()},
        "article_betweenness": btw,
        "author_betweenness": abtw,
    }


def analyze(db_path: str) -> dict:
    """Análisis de redes de la sesión (cacheado mientras la BD no cambie)."""
    return _analyze(str(db_path), Path(db_path).stat().st_mtime)
