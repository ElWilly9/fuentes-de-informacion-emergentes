"""
build_citas_word.py — Word original con los pasajes de las 32 preguntas resaltados
==================================================================================
Toma el Word de los estudiantes y, sin cambiar su texto, resalta el pasaje de donde sale
cada pregunta de preguntas_32.json y le pone la etiqueta [Qxx] al lado. Antepone un índice
con pregunta ↔ pasaje. Colores: amarillo = SQL, turquesa = híbrida, verde = RAG.

Uso (desde demo_limpio):  python benchmark/agrovoltaics/build_citas_word.py
Salida: benchmark/agrovoltaics/Articulo_con_citas_resaltadas.docx
"""

import copy
import json
import re
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.text.run import Run

HERE = Path(__file__).resolve().parent
SRC = HERE / "Version_español_Sci_25_2S_G1_agrovoltaicos_.docx"
OUT = HERE / "Articulo_con_citas_resaltadas.docx"

COLOR = {"SQL puro": WD_COLOR_INDEX.YELLOW, "Híbrida": WD_COLOR_INDEX.TURQUOISE,
         "RAG puro": WD_COLOR_INDEX.BRIGHT_GREEN}

# Tablas del Word: 1 = Tabla II (países), 2 = Tabla III (revistas), 3 = Tabla IV (autores)
T = lambda s, e=None: {"kind": "text", "start": s, "end": e}          # noqa: E731
R = lambda t, row: {"kind": "row", "table": t, "row": row}            # noqa: E731

ANCHORS = {
    "Q01": [T("reduciendo el total de 124 artículos a 77 publicaciones únicas")],
    "Q02": [T("en el año de mayor productividad (2024)")],
    "Q03": [T("solo 9 de los 49 artículos publicados en este periodo")],
    "Q04": [R(1, "CHINA")],
    "Q05": [R(1, "GERMANY"), T("Alemania, aunque ha producido únicamente 8 artículos")],
    "Q06": [R(1, "INDIA"), T("Le sigue India con 10 publicaciones (10,64 %)")],
    "Q07": [R(2, "Acta Horticulturae"), T("con valores 4, 3 y 3 artículos, respectivamente")],
    "Q08": [R(2, "AIP Conference Proceedings"), T("AIP Conference Proceedings (3 Scopus)")],
    "Q09": [R(3, "C. Agert Carsten"), T("C. Agert Carsten, M Vehse Martin y K. Gehrke Kai", "tres publicaciones cada uno")],
    "Q10": [R(3, "J.A. Carlyon Jason A."), T("J.A Carlyon, con una menor productividad", "26 citas")],
    "Q11": [T("ocho investigadores registran tres publicaciones")],
    "Q12": [R(1, "BANGLADESH")],
    "Q13": [T("se publicaron únicamente cinco artículos que acumularon 46 citas")],
    "Q14": [T("104 en 2015"), T("por ser el año con mayor número de artículos publicados (5 artículos)")],
    "Q15": [T("78 en 2014")],
    "Q16": [T("Scopus registró 12 artículos")],
    "Q17": [T("China es el mayor contribuyente a nivel mundial", "22,34 % de la producción total de artículos")],
    "Q18": [T("publicado en Egipto en 2024", "68 citaciones")],
    "Q19": [R(2, "Journal of Food Process Engineering"),
            T("Journal of Food Process Engineering muestra equilibrio entre WoS y Scopus", "2 y 2 registros")],
    "Q20": [T("(Hassanein et al., 2015)")],
    "Q21": [T("cuenta con tres artículos publicados recientemente (2022, 2023 y 2024)", "a esta temática")],
    "Q22": [R(1, "THAILAND")],
    "Q23": [T("(Chen et al., 2014)", "para el manejo de lodos")],
    "Q24": [T("este artículo analiza un secador de invernadero híbrido", "sin necesidad de energía externa")],
    "Q25": [T("Bangladesh en colaboración con Japón publicaron", "países en desarrollo")],
    "Q26": [T("Otro artículo que aborda el tema de agrovoltaicos", "maximicen simultáneamente la producción")],
    "Q27": [T("La colaboración más representativa de este grupo", "al campo agrovoltaico")],
    "Q28": [T("Un ejemplo representativo es el estudio (10.1109/IPEC57296.2023.00043)", "sistemas agrovoltaicos")],
    "Q29": [T("10.3969/j.issn.1002-6819.2009.09.037")],
    "Q30": [T("10.1016/j.jada.2008.03.013")],
    "Q31": [T("Donde los autores proponen un sistema en el que la energía solar térmica", "producción de biogás")],
    "Q32": [T("La mayoría de los trabajos se concentra en la implementación de secadores solares",
              "(por ejemplo, biogás)")],
}

# Preguntas cuyo pasaje del Word no contiene todo lo necesario para la respuesta
NOTAS = {
    "Q29": "El Word solo da el DOI y '13 citas'; el contenido del estudio sale del abstract en el corpus.",
    "Q30": "El Word solo da el DOI y '13 citas'; el contenido del estudio sale del abstract en el corpus.",
    "Q31": "Pregunta trampa: el Word describe a Hassanein, pero ese artículo no está en el corpus Scopus.",
    "Q12": "La cifra (3 artículos) está solo en la Tabla II.",
    "Q22": "La cifra (5 artículos) está solo en la Tabla II.",
    "Q04": "La cifra (21 artículos) está en la Tabla II.",
    "Q26": "El Word dice 2020; en el corpus el artículo es de 2024.",
}


def pattern(start, end=None):
    tok = lambda s: r"\s+".join(re.escape(w) for w in s.split())    # noqa: E731
    return re.compile(tok(start) + (r".*?" + tok(end) if end else ""), re.S)


def all_paragraphs(d):
    yield from d.paragraphs
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def par_runs(par) -> list[Run]:
    """Todos los runs del párrafo, incluidos los que están dentro de hipervínculos."""
    return [Run(r, par) for r in par._p.xpath("./w:r | ./w:hyperlink/w:r | ./w:ins/w:r")]


def split_run(run: Run, offset: int) -> None:
    """Parte un run en dos en la posición `offset` (conserva el formato)."""
    text = run.text
    if offset <= 0 or offset >= len(text):
        return
    clone = copy.deepcopy(run._r)
    run._r.addnext(clone)
    run.text = text[:offset]
    Run(clone, run._parent).text = text[offset:]


def runs_for_span(par, a, b) -> list[Run]:
    for edge in (a, b):
        pos = 0
        for r in par_runs(par):
            n = len(r.text)
            if pos < edge < pos + n:
                split_run(r, edge - pos)
                break
            pos += n
    sel, pos = [], 0
    for r in par_runs(par):
        n = len(r.text)
        if n and pos >= a and pos + n <= b:
            sel.append(r)
        pos += n
    return sel


def add_tag(after: Run, qid: str) -> None:
    new_r = copy.deepcopy(after._r)
    after._r.addnext(new_r)
    tag = Run(new_r, after._parent)
    tag.text = f" [{qid}] "
    tag.bold = True
    tag.font.size = Pt(9)
    tag.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    tag.font.highlight_color = None


def mark_text(d, qid, anchor, color):
    pat = pattern(anchor["start"], anchor["end"])
    for par in all_paragraphs(d):
        text = "".join(r.text for r in par_runs(par))
        m = pat.search(text)
        if m:
            sel = runs_for_span(par, m.start(), m.end())
            if not sel:
                continue
            for r in sel:
                r.font.highlight_color = color
            add_tag(sel[-1], qid)
            return text[m.start():m.end()]
    return None


def mark_row(d, qid, anchor, color):
    for row in d.tables[anchor["table"]].rows:
        cells = row.cells
        if cells[0].text.strip().casefold() == anchor["row"].casefold():
            last = None
            for cell in cells:
                for par in cell.paragraphs:
                    for r in par_runs(par):
                        if r.text.strip():
                            r.font.highlight_color = color
                            last = r
            if last is not None:
                add_tag(par_runs(cells[0].paragraphs[0])[-1], qid)
                return " | ".join(c.text.strip() for c in cells)
    return None


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): hexcolor})
    tcPr.append(shd)


def main():
    qs = json.loads((HERE / "preguntas_32.json").read_text(encoding="utf-8"))
    d = docx.Document(SRC)

    found, missing = {}, []
    for q in qs:
        qid, color = q["id"], COLOR[q["tipo"]]
        for anchor in ANCHORS[qid]:
            frag = (mark_text if anchor["kind"] == "text" else mark_row)(d, qid, anchor, color)
            if frag is None:
                missing.append((qid, anchor))
            else:
                found.setdefault(qid, []).append(frag)
    if missing:
        print("NO ENCONTRADOS:", *missing, sep="\n  ")
        sys.exit(1)

    # ── Índice al inicio ──────────────────────────────────────────────────────
    first = d.paragraphs[0]
    title = first.insert_paragraph_before("Pasajes de este artículo usados para las 32 preguntas del benchmark")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(14)
    legend = first.insert_paragraph_before(
        "El texto del artículo no fue modificado: solo se resaltaron los pasajes y se añadió la etiqueta [Qxx]. "
        "Amarillo = pregunta SQL (Q01–Q12) · Turquesa = híbrida (Q13–Q22) · Verde = RAG (Q23–Q32).")
    legend.runs[0].font.size = Pt(9)

    tbl = d.add_table(rows=1, cols=4)
    try:
        tbl.style = "Table Grid"
    except Exception:
        pass
    for c, h in zip(tbl.rows[0].cells, ("ID", "Pregunta", "Pasaje del Word (resaltado)", "Observación")):
        c.text = h
        c.paragraphs[0].runs[0].bold = True
    for q in qs:
        cells = tbl.add_row().cells
        cells[0].text = f"{q['id']}\n{q['tipo']}"
        cells[1].text = q["pregunta"]
        cells[2].text = "\n— ".join([""] + [re.sub(r"\s+", " ", f) for f in found[q["id"]]]).lstrip("\n")
        cells[3].text = NOTAS.get(q["id"], "")
        shade(cells[0], {"SQL puro": "FFF2A8", "Híbrida": "AEEFF0", "RAG puro": "B8F5B8"}[q["tipo"]])
        for c in cells:
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8)
    first._p.addprevious(tbl._tbl)
    sep = first.insert_paragraph_before("")
    sep.add_run().add_break(docx.enum.text.WD_BREAK.PAGE)

    d.save(OUT)
    print(f"OK: {OUT.name} — pasajes marcados para {len(found)} preguntas")


if __name__ == "__main__":
    main()
