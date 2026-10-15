"""
export.py — Redes de la Capa 5 como nodos y enlaces para visualizarlas
======================================================================
Devuelve {"nodes", "links", "legend", "summary"} listo para force-graph (2D) o 3d-force-graph (3D).
Los colores salen de la misma pertenencia que usa el agente (frentes Louvain, temas, autores puente),
así lo que se ve coincide con lo que responde el chat.
"""

import html
import math

from src.layer5_network.communities import analyze
from src.layer5_network.networks import load_corpus, coupling_graph, keyword_graph, coauthor_graph

# Paleta categórica (frentes/temas 1..10); gris = sin grupo; dorado = autor puente
PALETTE = ["#2563eb", "#e8590c", "#16a34a", "#9333ea", "#dc2626", "#0891b2", "#ca8a04", "#db2777",
           "#4f46e5", "#65a30d"]
NO_GROUP = "#9ca3af"
BRIDGE = "#f59e0b"

KINDS = {
    "frentes": "Frentes de investigación (acoplamiento bibliográfico)",
    "temas": "Temas (coocurrencia de palabras clave)",
    "coautoria": "Coautoría (autores puente)",
}


def _color(group: int | None) -> str:
    return PALETTE[(group - 1) % len(PALETTE)] if group else NO_GROUP


def _esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def graph_data(db_path: str, kind: str, min_weight: int = 1, hide_isolated: bool = True) -> dict:
    r = analyze(db_path)
    data = load_corpus(db_path)
    if kind == "frentes":
        g, legend = coupling_graph(data), []
        for f in r["fronts"]:
            legend.append({"label": f"Frente {f['id']}: {', '.join(f['keywords'][:3]).lower()} ({f['size']} art.)",
                           "color": _color(f["id"]), "group": f["id"]})
        legend.append({"label": "Sin frente (aislado o grupo < 3)", "color": NO_GROUP, "group": 0})
        bridges = {b["sr"] for b in r["bridge_articles"][:6]}
        nodes = []
        for sr in g:
            a = data.articles[sr]
            front = r["front_of"].get(sr)
            nodes.append({
                "id": sr, "name": a["title"][:60], "group": front or 0, "color": _color(front),
                "val": 1 + math.sqrt(a["cited_by"]), "bridge": sr in bridges,
                "label": (f"<b>{_esc(a['title'])}</b><br>{_esc(a['year'])} · {a['cited_by']} citas<br>"
                          f"{'Frente ' + str(front) if front else 'Sin frente'}"
                          f"{' · <b>artículo puente</b>' if sr in bridges else ''}<br>"
                          f"Referencias compartidas con {g.degree(sr)} artículos"),
            })
        summary = (f"{r['coupling']['connected_articles']} de {r['n_articles']} artículos comparten referencias · "
                   f"{len(r['fronts'])} frentes · modularidad {r['coupling']['modularity']}. "
                   "Tamaño = citas. Borde blanco = artículo puente.")
    elif kind == "temas":
        g, legend = keyword_graph(data), []
        for t in r["themes"]:
            legend.append({"label": f"Tema {t['id']}: {', '.join(t['keywords'][:3]).lower()} ({t['n_articles']} art.)",
                           "color": _color(t["id"]), "group": t["id"]})
        legend.append({"label": "Sin tema", "color": NO_GROUP, "group": 0})
        nodes = []
        for kw in g:
            theme = r["theme_of"].get(kw)
            freq = g.nodes[kw]["freq"]
            nodes.append({"id": kw, "name": kw.lower(), "group": theme or 0, "color": _color(theme),
                          "val": freq, "bridge": False,
                          "label": f"<b>{_esc(kw)}</b><br>{freq} artículos<br>"
                                   f"{'Tema ' + str(theme) if theme else 'Sin tema'}"})
        summary = (f"{g.number_of_nodes()} palabras clave (en ≥2 artículos) · {len(r['themes'])} temas. "
                   "Tamaño = número de artículos. Enlace = aparecen juntas en un artículo.")
    elif kind == "coautoria":
        g, legend = coauthor_graph(data), []
        for f in r["fronts"]:
            legend.append({"label": f"Autores del frente {f['id']}", "color": _color(f["id"]), "group": f["id"]})
        legend += [{"label": "Autor puente (≥2 frentes)", "color": BRIDGE, "group": None},
                   {"label": "Sin frente", "color": NO_GROUP, "group": 0}]
        nodes = []
        for aid in g:
            fr = r["author_fronts"].get(aid, [])
            is_bridge = len(fr) >= 2
            n = g.nodes[aid]
            nodes.append({
                "id": aid, "name": n.get("name", aid), "group": fr[0] if fr else 0,
                "color": BRIDGE if is_bridge else _color(fr[0] if fr else None),
                "val": n.get("articles", 1) ** 1.5, "bridge": is_bridge,
                "label": (f"<b>{_esc(n.get('name', aid))}</b><br>{n.get('articles', 0)} artículos · "
                          f"{g.degree(aid)} coautores<br>{_esc(', '.join(n.get('countries', [])) or 'País N/D')}<br>"
                          f"{'Frentes ' + ', '.join(map(str, fr)) if fr else 'Sin frente'}"
                          f"{' · <b>autor puente</b>' if is_bridge else ''}"),
            })
        co = r["coauthorship"]
        summary = (f"{co['authors']} autores · {co['components']} grupos desconectados · "
                   f"{len(r['bridge_authors'])} autores puente. Tamaño = artículos en el corpus.")
    else:
        raise ValueError(f"Red desconocida: {kind}")

    links = [{"source": a, "target": b, "weight": w}
             for a, b, w in sorted(g.edges(data="weight", default=1)) if w >= min_weight]
    if hide_isolated:
        linked = {l["source"] for l in links} | {l["target"] for l in links}
        nodes = [n for n in nodes if n["id"] in linked]
    return {"nodes": nodes, "links": links, "legend": legend, "summary": summary,
            "max_weight": max((w for *_, w in g.edges(data="weight", default=1)), default=1)}
