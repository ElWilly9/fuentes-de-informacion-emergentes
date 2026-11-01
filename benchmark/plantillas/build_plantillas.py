"""
build_plantillas.py — Benchmark por plantillas, igual para cualquier corpus
=============================================================================
Las mismas 20 plantillas de preguntas se instancian en cada corpus con valores sacados de su BD
(el país con más artículos, el autor más productivo, el artículo más citado…) y el gold se calcula
con SQL sobre esa misma BD. Así se mide si el agente generaliza: Agrovoltaics es el corpus de
desarrollo (sobre el que se ajustó el agente) y `ai` y `pendulo` son de prueba.

  S01–S09  SQL      : cifras; se puntúa si la respuesta contiene las cifras (y el país) del gold.
  H01–H05  Híbrida  : localizar artículos con SQL y explicar de qué tratan; se puntúa si nombra los títulos.
  R01–R06  RAG      : "¿qué artículo trata sobre <3 palabras clave distintivas>?"; se puntúa el título.

Solo se puntúa lo verificable de forma automática (cifras y títulos), no la calidad de la explicación.
Se excluyó la revista con más artículos: en el Excel de origen los artículos de conferencia sin revista
traen source_title = 'J FINANC' (en ai y pendulo sería la "revista" principal).

Salida: preguntas_plantillas.json / .md
Uso (desde demo_limpio):  python benchmark/plantillas/build_plantillas.py
"""

import json
import random
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
SESSIONS = HERE.parent.parent / "data" / "sessions"
CORPORA = ["Agrovoltaics", "ai", "pendulo"]
SEED = 42
N_RAG = 6

MAIN = "SR in (select SR from Article where ismainarticle=1)"

PAISES = {"CHINA": "China", "INDIA": "India", "GERMANY": "Alemania", "THAILAND": "Tailandia", "SPAIN": "España",
          "UNITED STATES OF AMERICA": "Estados Unidos", "UNITED STATES": "Estados Unidos", "MALAYSIA": "Malasia",
          "JORDAN": "Jordania", "RUSSIAN FEDERATION": "Rusia", "TURKEY": "Turquía", "VIETNAM": "Vietnam",
          "ITALY": "Italia", "FRANCE": "Francia", "UNITED KINGDOM": "Reino Unido", "BRAZIL": "Brasil",
          "JAPAN": "Japón", "SOUTH KOREA": "Corea del Sur", "KOREA, REPUBLIC OF": "Corea del Sur",
          "EGYPT": "Egipto", "MEXICO": "México", "SAUDI ARABIA": "Arabia Saudita", "IRAN": "Irán",
          "PAKISTAN": "Pakistán", "INDONESIA": "Indonesia", "AUSTRALIA": "Australia", "CANADA": "Canadá",
          "BANGLADESH": "Bangladés", "COLOMBIA": "Colombia", "POLAND": "Polonia", "NETHERLANDS": "Países Bajos", "CROATIA": "Croacia",
          "SWITZERLAND": "Suiza", "PORTUGAL": "Portugal", "GREECE": "Grecia", "NIGERIA": "Nigeria"}

# Términos de palabra clave demasiado genéricos para identificar un artículo
GENERIC_KW = {"ARTICLE", "REVIEW", "HUMAN", "HUMANS", "CONTROLLED STUDY", "SIMULATION", "OPTIMIZATION"}


def q(conn, sql, *args):
    return conn.execute(sql, args).fetchall()


def pais(c):
    return [c, PAISES.get(c, c.title())]


def nombre(full):
    """'VEHSE, MARTIN' → 'Martin Vehse'."""
    if "," in full:
        apellido, nombres = [p.strip() for p in full.split(",", 1)]
        return f"{nombres.title()} {apellido.title()}"
    return full.title()


def titles(conn, where, *args, order="cited_by desc", limit=None):
    sql = f"select title from Article where ismainarticle=1 and {where} order by {order}"
    if limit:
        sql += f" limit {limit}"
    return [r[0] for r in q(conn, sql, *args)]


def distinctive(keywords: list[str], n: int = 3) -> list[str]:
    """Las n primeras palabras clave (ya ordenadas por rareza) sin casi repetidas: se salta una si comparte
    la mitad o más de sus palabras con otra ya elegida ('deep learning neural network' / '... networks')."""
    chosen = []
    for k in keywords:
        words = {w.rstrip("s") for w in k.lower().split()}
        if all(len(words & {w.rstrip("s") for w in c.lower().split()}) < max(1, len(words) / 2) for c in chosen):
            chosen.append(k)
        if len(chosen) == n:
            break
    return chosen if len(chosen) == n else keywords[:n]


def build(corpus: str) -> list[dict]:
    conn = sqlite3.connect(SESSIONS / corpus / "db" / "bibliometria.db")
    out = []

    def add(qid, tipo, pregunta, gold, **extra):
        out.append({"corpus": corpus, "id": f"{corpus}-{qid}", "plantilla": qid, "tipo": tipo,
                    "pregunta": pregunta, "gold": gold, **extra})

    n_main = q(conn, "select count(*) from Article where ismainarticle=1")[0][0]
    max_year = q(conn, "select max(year) from Article where ismainarticle=1")[0][0]
    years = q(conn, "select year, count(*) n from Article where ismainarticle=1 group by year order by n desc, year desc")
    top_n = years[0][1]
    countries = q(conn, f"select Country, count(distinct SR) n from Affiliation where {MAIN} and Country is not null "
                        "group by Country order by n desc, Country")
    authors = q(conn, f"select au.AuthorFullName, count(distinct aa.SR) n from ArticleAuthor aa "
                      f"join Author au on au.AuthorID = aa.AuthorID where aa.{MAIN} and au.AuthorFullName is not null "
                      "group by au.AuthorFullName order by n desc, au.AuthorFullName")
    top_cited = q(conn, "select title, cited_by, year from Article where ismainarticle=1 order by cited_by desc limit 1")[0]

    # ── SQL ──────────────────────────────────────────────────────────────────
    add("S01", "SQL", "¿Cuántos artículos principales hay en el corpus?", {"numeros": [n_main]})
    add("S02", "SQL", "¿En qué año se publicaron más artículos y cuántos?",
        {"numeros": [top_n], "alguno_de": [[str(y)] for y, n in years if n == top_n]})
    y1 = max_year - 4
    n_range = q(conn, "select count(*) from Article where ismainarticle=1 and year between ? and ?", y1, max_year)[0][0]
    add("S03", "SQL", f"¿Cuántos artículos se publicaron entre {y1} y {max_year}?", {"numeros": [n_range]})
    c_top = countries[0][1]
    add("S04", "SQL", "¿Qué país aparece en más artículos y en cuántos?",
        {"numeros": [c_top], "alguno_de": [pais(c) for c, n in countries if n == c_top]})
    c3, n3 = countries[2]
    add("S05", "SQL", f"¿En cuántos artículos participa al menos una institución de {pais(c3)[1]}?",
        {"numeros": [n3]}, valor=c3)
    add("S06", "SQL", "¿Cuántas citas tiene el artículo más citado del corpus?", {"numeros": [top_cited[1]]})
    y_top = years[0][0]
    cites_y = q(conn, "select sum(cited_by) from Article where ismainarticle=1 and year = ?", y_top)[0][0]
    add("S07", "SQL", f"¿Cuántas citas suman los artículos publicados en {y_top}?", {"numeros": [cites_y]})
    a_full, a_n = authors[0]
    a_cites = q(conn, f"select sum(cited_by) from Article where ismainarticle=1 and SR in (select aa.SR from ArticleAuthor aa "
                      "join Author au on au.AuthorID = aa.AuthorID where au.AuthorFullName = ?)", a_full)[0][0]
    add("S08", "SQL", f"¿Cuántos artículos tiene {nombre(a_full)} en el corpus y cuántas citas suman?",
        {"numeros": [a_n, a_cites]}, valor=a_full)
    avg = q(conn, "select round(avg(cited_by), 1) from Article where ismainarticle=1")[0][0]
    add("S09", "SQL", "¿Cuál es el promedio de citas por artículo en el corpus?", {"numeros": [avg]})

    # ── Híbridas ─────────────────────────────────────────────────────────────
    add("H01", "Híbrida", "¿Cuál es el artículo más citado del corpus y de qué trata?",
        {"titulos": [top_cited[0]], "minimo": 1})
    y2 = years[1][0]
    max_c = q(conn, "select max(cited_by) from Article where ismainarticle=1 and year = ?", y2)[0][0]
    add("H02", "Híbrida", f"¿Cuál es el artículo más citado publicado en {y2} y qué estudia?",
        {"titulos": titles(conn, "year = ? and cited_by = ?", y2, max_c), "minimo": 1})
    a_titles = titles(conn, "SR in (select aa.SR from ArticleAuthor aa join Author au on au.AuthorID = aa.AuthorID "
                            "where au.AuthorFullName = ?)", a_full)
    add("H03", "Híbrida", f"¿Qué artículos ha publicado {nombre(a_full)} en el corpus y de qué tratan?",
        {"titulos": a_titles, "minimo": len(a_titles)}, valor=a_full)
    c_small = next(c for c, n in countries if 2 <= n <= 4)
    c_titles = titles(conn, "SR in (select SR from Affiliation where Country = ?)", c_small)
    add("H04", "Híbrida", f"¿Qué artículos tienen autores de {pais(c_small)[1]} y de qué tratan?",
        {"titulos": c_titles, "minimo": len(c_titles)}, valor=c_small)
    rec_c = q(conn, "select max(cited_by) from Article where ismainarticle=1 and year >= ?", max_year - 1)[0][0]
    add("H05", "Híbrida", f"De los artículos publicados desde {max_year - 1}, ¿cuál es el más citado y qué propone?",
        {"titulos": titles(conn, "year >= ? and cited_by = ?", max_year - 1, rec_c), "minimo": 1})

    # ── RAG: 3 palabras clave distintivas de un artículo elegido al azar (semilla fija) ──
    rows = q(conn, "select SR, title, author_keywords from Article where ismainarticle=1 and length(abstract) > 500 "
                   "and author_keywords is not null order by SR")
    df = {}
    for _, _, kws in rows:
        for k in {k.strip() for k in kws.split(";") if k.strip()}:
            df[k] = df.get(k, 0) + 1
    usados = {top_cited[0]}
    candidatos = [r for r in rows if r[1] not in usados
                  and len([k for k in r[2].split(";") if k.strip() and k.strip() not in GENERIC_KW]) >= 4]
    for i, (sr, title, kws) in enumerate(random.Random(SEED).sample(candidatos, N_RAG), 1):
        ks = distinctive(sorted({k.strip() for k in kws.split(";") if k.strip() and k.strip() not in GENERIC_KW},
                                key=lambda k: (df[k], k)))
        add(f"R{i:02d}", "RAG", f"¿Qué artículo del corpus trata sobre {ks[0].lower()}, {ks[1].lower()} y "
                                f"{ks[2].lower()}, y qué propone?", {"titulos": [title], "minimo": 1}, sr=sr)
    conn.close()
    return out


def render_md(items: list[dict]) -> str:
    lines = ["# Benchmark por plantillas — preguntas y gold", ""]
    for corpus in CORPORA:
        lines += [f"## {corpus}", "", "| ID | Tipo | Pregunta | Gold |", "|---|---|---|---|"]
        for it in (i for i in items if i["corpus"] == corpus):
            g = it["gold"]
            gold = "; ".join(filter(None, [
                ", ".join(map(str, g.get("numeros", []))),
                " o ".join("/".join(a) for a in g.get("alguno_de", [])),
                " · ".join(t[:70] for t in g.get("titulos", [])),
            ]))
            lines.append(f"| {it['plantilla']} | {it['tipo']} | {it['pregunta']} | {gold} |")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    items = [it for c in CORPORA for it in build(c)]
    (HERE / "preguntas_plantillas.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "preguntas_plantillas.md").write_text(render_md(items), encoding="utf-8")
    print(f"{len(items)} preguntas en {len(CORPORA)} corpus → preguntas_plantillas.json / .md")
