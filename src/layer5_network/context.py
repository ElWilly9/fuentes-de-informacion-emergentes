"""
context.py — Resultados de la Capa 5 como texto para el LLM
===========================================================
El LLM no calcula nada: recibe aquí las cifras ya calculadas y solo redacta.

Criterio de "frente/tema emergente" (relativo al corpus, porque el campo entero crece):
crecimiento anual mayor que el del corpus, tendencia significativa (p < 0,05) Y mayor
participación de los últimos años que la del corpus, con al menos EMERGING_MIN_ARTICLES artículos.
"Señal débil": cumple lo mismo salvo la significancia (temas muy recientes con pocos artículos).
"""

import os
import re

from src.layer5_network.communities import analyze
from src.layer5_network.networks import load_corpus
from src.layer5_network.trends import annual_series, growth_indicators, arima_forecast, RECENT_YEARS

EMERGING_MIN_ARTICLES = int(os.getenv("EMERGING_MIN_ARTICLES", "3"))

# ── Detección de la intención (determinista, antes del clasificador LLM) ─────

_GRAPH = re.compile(r"puente|coautor|co-autor|colaboraci|colabora|red(es)? de (autores|colaboraci|coautor|citas|acoplamiento)|"
                    r"centralidad|intermediaci|betweenness|m[aá]s conectad|nodos? central", re.IGNORECASE)
_FORECAST = re.compile(r"pron[oó]stic|predic|proyecci|series? de tiempo|serie temporal|arima|tendencia|"
                       r"evoluci[oó]n|evolucionad|crecimiento|crecer[aá]|crece|futuro|pr[oó]ximos a[nñ]os", re.IGNORECASE)
_COMMUNITY = re.compile(r"frentes?|comunidad|cl[uú]ster|agrupaci|grupos? tem[aá]tic|l[ií]neas? de investigaci|"
                        r"emergente|temas? (principales|de investigaci)|mapa tem[aá]tico|subtemas?", re.IGNORECASE)


def detect_network_intent(query: str) -> str | None:
    """graph / forecast / community si la pregunta pide un análisis de redes o de tendencias."""
    if _GRAPH.search(query):
        return "graph"
    if _COMMUNITY.search(query) and not _FORECAST.search(query):
        return "community"
    if _FORECAST.search(query):
        # "¿qué frentes emergentes crecen más?" mezcla ambas: los frentes ya llevan su tendencia
        return "community" if _COMMUNITY.search(query) else "forecast"
    return None


# ── Utilidades de formato ────────────────────────────────────────────────────

def _pct(x) -> str:
    return "N/D" if x is None else f"{x * 100:+.0f} %/año"


def _trend_line(t: dict) -> str:
    sig = "" if t.get("p_value") is None else (" (significativo, p<0,05)" if t["p_value"] < 0.05
                                                else f" (no significativo, p={t['p_value']})")
    share = "N/D" if t.get("recent_share") is None else f"{t['recent_share'] * 100:.0f} %"
    return (f"{t['total']} artículos ({t['first_year']}–{t['last_year']}), año medio {t['mean_year']}, "
            f"{share} en los últimos {RECENT_YEARS} años, crecimiento {_pct(t.get('growth_rate'))}{sig}")


def _series_line(series: dict) -> str:
    return ", ".join(f"{y}: {n}" for y, n in series.items())


def _grows_faster(t: dict, corpus: dict) -> bool:
    return (t["total"] >= EMERGING_MIN_ARTICLES and t.get("growth_rate") is not None
            and corpus.get("growth_rate") is not None and t["growth_rate"] > corpus["growth_rate"]
            and (t.get("recent_share") or 0) > (corpus.get("recent_share") or 0))


def _is_emerging(t: dict, corpus: dict) -> bool:
    return _grows_faster(t, corpus) and t.get("p_value") is not None and t["p_value"] < 0.05


def _is_weak_signal(t: dict, corpus: dict) -> bool:
    return _grows_faster(t, corpus) and not _is_emerging(t, corpus)


def _tag(t: dict, corpus: dict) -> str:
    """Clasificación explícita (sin ella, glm4 inventaba la etiqueta EMERGENTE en grupos que no lo son)."""
    if _is_emerging(t, corpus):
        return " — Clasificación: EMERGENTE"
    if _is_weak_signal(t, corpus):
        return " — Clasificación: SEÑAL DÉBIL (crece más que el corpus, pero sin significancia estadística)"
    if t["total"] < EMERGING_MIN_ARTICLES:
        why = f"menos de {EMERGING_MIN_ARTICLES} artículos"
    elif t.get("growth_rate") is None or t["growth_rate"] <= (corpus.get("growth_rate") or 0):
        why = "no crece más rápido que el corpus"
    else:
        why = "su peso en los últimos años no supera al del corpus"
    return f" — Clasificación: NO EMERGENTE ({why})"


def _forecast_lines(fc: dict) -> list[str]:
    if not fc["ok"]:
        return [f"  Pronóstico ARIMA: no se calcula, {fc['reason']}."]
    lines = [f"  Pronóstico ARIMA{fc['order']} (elegido por AIC={fc['aic']}), intervalo de confianza 95 %:"]
    lines += [f"    {f['year']}: {f['mean']} artículos (entre {f['low']} y {f['high']})" for f in fc["forecast"]]
    return lines


# ── Contextos por intención ──────────────────────────────────────────────────

_ASKS_THEMES = re.compile(r"palabras? clave|keywords?|\btemas?\b|tem[aá]tic", re.IGNORECASE)
_ASKS_FRONTS = re.compile(r"frentes?|comunidad|cl[uú]ster|agrupaci|acoplamiento|l[ií]neas? de investigaci", re.IGNORECASE)


def community_context(db_path: str, query: str = "") -> tuple[str, list[dict]]:
    """
    Frentes (acoplamiento) y/o temas (palabras clave). Si la pregunta nombra solo uno de los dos,
    se pasa solo ese: con ambos, glm4 los mezclaba (llamaba "frentes" a los temas).
    """
    r = analyze(db_path)
    corpus = r["total_trend"]
    c = r["coupling"]
    want_themes = bool(_ASKS_THEMES.search(query)) and not _ASKS_FRONTS.search(query)
    want_fronts = not want_themes
    lines = [
        "MÉTODO: " + ("frentes de investigación = comunidades Louvain sobre la red de acoplamiento bibliográfico "
                      "(dos artículos se unen si citan referencias en común). " if want_fronts else "") +
        ("temas = comunidades Louvain sobre la red de coocurrencia de palabras clave de autor. " if want_themes else "") +
        f"EMERGENTE = crece más rápido que el corpus, con tendencia significativa, y tiene más peso en los "
        f"últimos {RECENT_YEARS} años que el corpus. Usa la clasificación tal como aparece en cada grupo.",
        f"CORPUS: {_trend_line(corpus)}.",
    ]
    shown = []
    if want_themes:
        lines += ["", "TEMAS (palabras clave):"]
        for t in r["themes"][:8]:
            lines.append(f"Tema {t['id']}{_tag(t['trend'], corpus)}")
            lines.append(f"  Palabras clave: {', '.join(t['keywords'])}")
            lines.append(f"  Tendencia: {_trend_line(t['trend'])}")
        return "\n".join(lines), shown

    lines += [
        f"RED DE ACOPLAMIENTO: {c['connected_articles']} de {r['n_articles']} artículos comparten referencias "
        f"con otro ({c['isolated']} quedan aislados y no pertenecen a ningún frente); modularidad {c['modularity']}.",
        "",
        "FRENTES DE INVESTIGACIÓN (acoplamiento):",
    ]
    for f in r["fronts"]:
        tag = _tag(f["trend"], corpus)
        lines.append(f"Frente {f['id']}{tag}")
        lines.append(f"  {f['size']} artículos, {f['citations']} citas en total.")
        lines.append(f"  Palabras clave características: {', '.join(f['keywords']) or 'N/D'}")
        lines.append(f"  Tendencia: {_trend_line(f['trend'])}")
        if f["tos_branches"]:
            lines.append("  Ubicación en el Tree of Science: " +
                         ", ".join(f"{k}: {v}" for k, v in f["tos_branches"].items()))
        lines.append("  Artículos más citados:")
        for a in f["articles"][:3]:
            lines.append(f"    - {a['title']} ({a['year']}, {a['cited_by']} citas)")
            shown.append({"sr": a["sr"], "title": a["title"]})
    return "\n".join(lines), shown


def graph_context(db_path: str) -> tuple[str, list[dict]]:
    r = analyze(db_path)
    co, c = r["coauthorship"], r["coupling"]
    lines = [
        "MÉTODO: red de coautoría (autores unidos si firman un artículo juntos) y red de acoplamiento "
        "bibliográfico entre artículos. Autor puente = autor con artículos en dos o más frentes de "
        "investigación distintos. Intermediación (betweenness) = cuántos caminos más cortos de la red pasan por el nodo.",
        f"RED DE COAUTORÍA: {co['authors']} autores, {co['edges']} vínculos, {co['components']} grupos "
        f"desconectados; el grupo más grande tiene {co['largest_component']} autores. Solo {co['authors_2plus']} "
        "autores tienen 2 o más artículos en el corpus.",
        f"RED DE ACOPLAMIENTO: {c['connected_articles']} de {r['n_articles']} artículos conectados, "
        f"{c['edges']} vínculos, {len(r['fronts'])} frentes.",
        "",
        "AUTORES PUENTE (artículos en 2 o más frentes):",
    ]
    if r["bridge_authors"]:
        for a in r["bridge_authors"][:10]:
            lines.append(f"  - {a['name']}: {a['articles']} artículos, frentes {a['fronts']}, "
                         f"{a['coauthors']} coautores, países {', '.join(a['countries']) or 'N/D'}")
    else:
        lines.append("  Ninguno: ningún autor publica en dos frentes distintos de este corpus.")
    lines.append("INTERMEDIARIOS EN LA RED DE COAUTORÍA (intermediación > 0):")
    if r["brokers"]:
        for a in r["brokers"][:8]:
            lines.append(f"  - {a['name']}: intermediación {a['betweenness']}, {a['articles']} artículos, "
                         f"{a['coauthors']} coautores")
    else:
        lines.append("  Ninguno: la coautoría está fragmentada en grupos que no se conectan entre sí.")
    lines.append("AUTORES CON MÁS ARTÍCULOS:")
    for a in r["top_authors"][:8]:
        lines.append(f"  - {a['name']}: {a['articles']} artículos, {a['coauthors']} coautores, "
                     f"países {', '.join(a['countries']) or 'N/D'}")
    lines.append("ARTÍCULOS PUENTE (mayor intermediación en la red de acoplamiento):")
    shown = []
    for a in r["bridge_articles"][:6]:
        lines.append(f"  - {a['title']} ({a['year']}): intermediación {a['betweenness']}, enlazado con "
                     f"{a['degree']} artículos, conecta los frentes {a['connects_fronts']}")
        shown.append({"sr": a["sr"], "title": a["title"]})
    return "\n".join(lines), shown


# Palabras de la propia pregunta de tendencia que no son el tema
_NOT_TOPIC = {"TREND", "TRENDS", "FORECAST", "FORECASTING", "PREDICTION", "GROWTH", "EVOLUTION", "FUTURE",
              "NUMBER", "ARTICLES", "PUBLICATIONS", "RESEARCH", "YEARS", "TIME SERIES", "CORPUS"}


def _stem(word: str) -> str:
    """Quita la 'S' final para que GREENHOUSES encuentre también GREENHOUSE."""
    return word[:-1] if word.endswith("S") and len(word) > 5 else word


def _plain(text: str) -> str:
    """Mayúsculas, sin signos, cada palabra sin plural; agrovoltaic(s) → agrivoltaic (variante ortográfica)."""
    words = re.sub(r"[^A-Z0-9 ]", " ", str(text).upper().replace("AGROVOLTAIC", "AGRIVOLTAIC")).split()
    return " " + " ".join(_stem(w) for w in words) + " "


def _topic_articles(query: str, db_path: str) -> tuple[list[str], list[dict]]:
    """
    Tema de una pregunta de tendencia y los artículos que lo tratan.

    El tema son las palabras clave del corpus que aparecen en la pregunta traducida al inglés
    (las palabras clave están en inglés). Un artículo trata el tema si todas esas frases aparecen
    en su título, abstract o palabras clave; si así quedan menos de 3, basta con una.
    """
    import sqlite3
    from src.layer3_rag.retriever import to_search_query

    text = _plain(to_search_query(query))
    data = load_corpus(db_path)
    kws = {kw for a in data.articles.values() for kw in a["keywords"]} - _NOT_TOPIC
    found = [kw for kw in sorted(kws, key=len, reverse=True) if len(kw) > 3 and _plain(kw) in text]
    # quita las contenidas en otra más larga ya encontrada ("SOLAR" dentro de "SOLAR DRYING")
    # y las variantes de la misma (AGRIVOLTAIC / AGRIVOLTAICS)
    topic, seen = [], set()
    for kw in found:
        if _plain(kw) in seen or any(_plain(kw) in _plain(o) for o in topic):
            continue
        seen.add(_plain(kw))
        topic.append(kw)
    if not topic:
        return [], []

    conn = sqlite3.connect(db_path)
    abstracts = dict(conn.execute("SELECT SR, abstract FROM Article WHERE ismainarticle = 1"))
    conn.close()
    docs = {sr: _plain(f"{a['title']} {abstracts.get(sr) or ''} {' '.join(a['keywords'])}")
            for sr, a in data.articles.items()}
    stems = [_plain(t) for t in topic]

    def match(test):
        return [{"sr": sr, **data.articles[sr]} for sr, doc in docs.items()
                if data.articles[sr]["year"] and test(s in doc for s in stems)]
    arts = match(all)
    if len(arts) < EMERGING_MIN_ARTICLES and len(stems) > 1:
        arts = match(any)
    return topic, arts


def forecast_context(db_path: str, query: str) -> tuple[str, list[dict]]:
    """
    Serie anual y pronóstico. Si la pregunta trae un tema, solo se pasan las cifras de ese tema
    (del corpus solo la tendencia, como comparación): con el pronóstico del corpus al lado, glm4
    lo presentaba como si fuera el del tema.
    """
    r = analyze(db_path)
    corpus = r["total_trend"]
    method = ("MÉTODO: series de tiempo anuales del número de artículos. Crecimiento = regresión de Poisson del "
              "número de artículos por año. Pronóstico = ARIMA con orden elegido por AIC e intervalo de confianza "
              "del 95 %; solo se calcula con al menos 10 años y 20 artículos. Las series son cortas: los "
              "pronósticos son orientativos.")
    topic, arts = _topic_articles(query, db_path)
    if topic:
        series = annual_series([a["year"] for a in arts], *r["years"])
        t = growth_indicators(series)
        lines = [method, "",
                 f"TEMA DE LA PREGUNTA: {' + '.join(topic)} (buscado en título, abstract y palabras clave)",
                 f"  {_trend_line(t) if arts else '0 artículos'}" + (_tag(t, corpus) if arts else ""),
                 f"  Artículos del tema por año: {_series_line(series)}",
                 *[ln.replace("Pronóstico ARIMA", "Pronóstico ARIMA DEL TEMA") for ln in _forecast_lines(arima_forecast(series))],
                 "  Artículos más recientes del tema:",
                 *[f"    - {a['title']} ({a['year']})" for a in sorted(arts, key=lambda a: -a["year"])[:5]],
                 "",
                 f"SOLO COMO COMPARACIÓN, CORPUS COMPLETO (no son cifras del tema): {_trend_line(corpus)}."]
        shown = [{"sr": a["sr"], "title": a["title"]} for a in sorted(arts, key=lambda a: -a["year"])[:10]]
        return "\n".join(lines), shown

    lines = [
        method,
        f"CORPUS COMPLETO: {_trend_line(corpus)}.",
        f"  Artículos por año: {_series_line(r['total_series'])}",
        *_forecast_lines(arima_forecast(r["total_series"])),
    ]
    if _TOPIC_HINT.search(query):
        lines += ["", "La pregunta parece referirse a un tema concreto, pero no se encontró en las palabras clave "
                      "del corpus: las cifras son del corpus completo. Dilo así en la respuesta."]

    ranked = sorted(r["keyword_trends"], key=lambda k: (-(k["recent_share"] or 0), -(k["growth_rate"] or 0), k["keyword"]))
    emerging = [k for k in ranked if _is_emerging(k, corpus)]
    weak = [k for k in ranked if _is_weak_signal(k, corpus)]
    lines += ["", f"PALABRAS CLAVE EMERGENTES (crecen más que el corpus, tendencia significativa, "
                  f"≥{EMERGING_MIN_ARTICLES} artículos):"]
    lines += [f"  - {k['keyword']}: {_trend_line(k)}" for k in emerging[:10]] or ["  Ninguna."]
    lines += ["SEÑALES DÉBILES (recientes y en crecimiento, pero sin significancia estadística):"]
    lines += [f"  - {k['keyword']}: {_trend_line(k)}" for k in weak[:8]] or ["  Ninguna."]
    lines += ["", "FRENTES DE INVESTIGACIÓN ORDENADOS POR CRECIMIENTO:"]
    for f in sorted(r["fronts"], key=lambda f: -(f["trend"].get("growth_rate") or -9)):
        lines.append(f"  Frente {f['id']} ({', '.join(f['keywords'][:4])}): {_trend_line(f['trend'])}{_tag(f['trend'], corpus)}")
    return "\n".join(lines), []


# "sobre X", "de X", "del X": la pregunta nombra un tema
_TOPIC_HINT = re.compile(r"\b(sobre|acerca de|en el [aá]rea de|del tema)\b", re.IGNORECASE)


def network_context(intent: str, db_path: str, query: str) -> tuple[str, list[dict]]:
    """Texto con los resultados calculados para la intención dada y los artículos mencionados."""
    if intent == "graph":
        return graph_context(db_path)
    if intent == "forecast":
        return forecast_context(db_path, query)
    return community_context(db_path, query)
