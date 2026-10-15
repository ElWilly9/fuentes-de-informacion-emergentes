"""
build_preguntas_scopus.py — Dataset de 32 preguntas con respuestas SOLO del corpus Scopus
=========================================================================================
Preguntas parecidas a lo que analiza el Word de los estudiantes, pero cuya respuesta esperada
sale únicamente del corpus Scopus (data/sessions/Agrovoltaics), que es lo que consulta el agente.
El Word solo se cita como referencia en `relacion_word`; nunca es la respuesta esperada.

  Q01-Q12  SQL      : una cifra o lista; gold = ejecutar gold_sql sobre la BD.
  Q13-Q22  Híbrida  : localizar artículos con SQL y explicar de qué tratan (abstract).
  Q23-Q32  RAG      : contenido de un artículo o tema, sacado de los abstracts del corpus.

Salida: preguntas_scopus_32.json / .md / .xlsx
Uso (desde demo_limpio):  python benchmark/agrovoltaics/build_preguntas_scopus.py
"""

import json
import sqlite3
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

HERE = Path(__file__).resolve().parent
DB = HERE.parent.parent / "data" / "sessions" / "Agrovoltaics" / "db" / "bibliometria.db"
NAME = "preguntas_scopus_32"

MAIN = "SR in (select SR from Article where ismainarticle=1)"


def country(c):
    return f"select count(distinct SR) from Affiliation where Country='{c}' and {MAIN}"


def arts_where(cond):
    return f"select SR,year,cited_by,title from Article where ismainarticle=1 and {cond} order by cited_by desc"


# ── SQL puro: (id, pregunta, gold_sql, respuesta_esperada, relación con el Word) ──
SQL_Q = [
    ("Q01", "¿Cuántos artículos principales hay en el corpus?",
     "select count(*) from Article where ismainarticle=1",
     "66 artículos principales.", "El Word reporta 77 porque une Scopus y WoS."),
    ("Q02", "¿En qué año se publicaron más artículos y cuántos?",
     "select year,count(*) n from Article where ismainarticle=1 group by year order by n desc limit 1",
     "2024, con 13 artículos.", "El Word: 2024 es el año más productivo (Scopus 12)."),
    ("Q03", "¿Cuántos artículos se publicaron entre 2020 y 2025?",
     "select count(*) from Article where ismainarticle=1 and year between 2020 and 2025",
     "45 artículos.", "El Word: 49 en el periodo 2020–2025 (Scopus + WoS)."),
    ("Q04", "¿Qué país aparece en más artículos y en cuántos?",
     "select Country,count(distinct SR) n from Affiliation where " + MAIN +
     " group by Country order by n desc limit 1",
     "China, en 17 artículos.", "El Word: China lidera con 21 (Scopus + WoS)."),
    ("Q05", "¿En cuántos artículos participa al menos una institución de Alemania?", country("GERMANY"),
     "7 artículos.", "El Word: 8 (Scopus + WoS)."),
    ("Q06", "¿En cuántos artículos participa al menos una institución de India?", country("INDIA"),
     "8 artículos.", "El Word: 10 (Scopus + WoS)."),
    ("Q07", "Entre los artículos que tienen revista registrada, ¿qué revista concentra más artículos y cuántos?",
     "select source_title,count(*) n from Article where ismainarticle=1 and source_title is not null "
     "group by source_title order by n desc limit 1",
     "Acta Horticulturae (ACTA HORTIC), con 4 artículos.",
     "Coincide con el Word. Ojo: 26 artículos no tienen revista registrada (source_title vacío)."),
    ("Q08", "¿Cuántos artículos del corpus se publicaron en AIP Conference Proceedings?",
     "select count(*) from Article where ismainarticle=1 and source_title='AIP CONF PROC'",
     "3 artículos.", "Coincide con el Word."),
    ("Q09", "¿Cuántos artículos tiene Carsten Agert en el corpus y cuántas citas suman?",
     "select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR "
     "where aa.AuthorID like 'C_AGERT%' and a.ismainarticle=1",
     "3 artículos con 38 citas en total.", "Coincide con la Tabla IV del Word."),
    ("Q10", "¿Cuántos artículos tiene Jason A. Carlyon en el corpus y cuántas citas suman?",
     "select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR "
     "where aa.AuthorID like '%CARLYON%' and a.ismainarticle=1",
     "2 artículos con 26 citas en total.", "Coincide con la Tabla IV del Word."),
    ("Q11", "¿Qué autores tienen 3 o más artículos en el corpus?",
     "select au.AuthorName,count(distinct aa.SR) n from ArticleAuthor aa join Author au on au.AuthorID=aa.AuthorID "
     "where aa." + MAIN + " group by aa.AuthorID having n>=3 order by n desc, au.AuthorName",
     "5 autores, todos con 3 artículos: Carsten Agert, Kai Gehrke, Martin Vehse, Nils Neugebohrn y Norbert Osterthun.",
     "El Word dice que ocho autores tienen tres publicaciones (Scopus + WoS)."),
    ("Q12", "¿Cuántas citas suman los artículos publicados en 2014?",
     "select sum(cited_by) from Article where ismainarticle=1 and year=2014",
     "78 citas.", "Coincide con el Word."),
]

# ── Híbridas: (id, pregunta, gold_sql, respuesta_esperada, relación con el Word) ──
HYB_Q = [
    ("Q13", "¿Cuál es el artículo más citado del corpus y de qué trata?",
     arts_where("1=1") + " limit 1",
     "«Powering agriculture: present status, future potential, and challenges of renewable energy applications» "
     "(Rahman et al., 2022, Renewable Energy), con 165 citas. Revisa el uso de energías renovables en la "
     "agricultura para reducir la dependencia de combustibles fósiles (secado de grano, fertilizantes, "
     "maquinaria, electricidad) y sus emisiones.",
     "El Word no lo menciona."),
    ("Q14", "¿Cuál fue el artículo más citado publicado en 2014 y qué estudió?",
     arts_where("year=2014") + " limit 1",
     "Chen et al. (2014, Waste Management), con 59 citas: uso de energía solar en el compostaje de lodos de "
     "depuración; comparó reactores ordinario, de invernadero y solar, y el solar dio calor más estable "
     "(más de 55 °C durante más de 3 días).",
     "El Word atribuye a Chen et al. el impulso de las citas de 2014."),
    ("Q15", "¿Cuál fue el artículo más citado publicado en 2015 y de qué trata?",
     arts_where("year=2015") + " limit 1",
     "Fasahati et al. (2015, Energy), con 38 citas: impacto económico, energético y ambiental de la tecnología "
     "de deshidratación de alcohol en la producción de biocombustible a partir de algas pardas.",
     "El Word dice que el más citado de 2015 es Hassanein et al., que solo está en WoS."),
    ("Q16", "Entre los artículos con 'photovoltaic', 'agrivoltaic' o 'PV' en el título, ¿cuál es el más citado y qué sistema analiza?",
     arts_where("(title like '%PHOTOVOLT%' or title like '%AGRIVOLT%' or title like '%AGROVOLT%' or title like '% PV %')") + " limit 1",
     "Azam et al. (2020, Energy), con 69 citas: un secador de invernadero híbrido para tomates que integra un "
     "sistema fotovoltaico y un colector solar.",
     "El Word lo señala como el más citado con esos términos (pero le pone 68 citas y año 2024)."),
    ("Q17", "¿Cuáles fueron los artículos más citados publicados entre 2007 y 2012 y de qué tratan?",
     arts_where("year between 2007 and 2012") + " limit 2",
     "Dos artículos con 13 citas cada uno: Meng et al. (2009), un sistema integrado de invernadero y calentador "
     "solar para la digestión anaerobia de lodos activados; y Rankins et al. (2008), el secado solar de mangos "
     "para conservar la provitamina A en África occidental francófona.",
     "Coincide con el Word, que cita ambos DOI con 13 citas."),
    ("Q18", "¿Qué artículos tienen autores de Bangladesh y de qué tratan?",
     arts_where("SR in (select SR from Affiliation where Country='BANGLADESH')"),
     "3 artículos: Rahman et al. (2022), revisión de energías renovables en agricultura (165 citas); Rana et al. "
     "(2023), acuicultura marina y un secador de pescado inteligente basado en IoT; y Rony et al. (2024), "
     "agrovoltaica más acuaponía en azoteas urbanas de Dhaka.",
     "El Word destaca a Bangladesh como el país con más colaboración."),
    ("Q19", "¿Qué artículos publicó el grupo de Carsten Agert y de qué tratan?",
     arts_where("SR in (select SR from ArticleAuthor where AuthorID like 'C_AGERT%')"),
     "3 artículos (Osterthun et al., 2021–2022), todos sobre celdas solares espectralmente selectivas que "
     "combinan fotovoltaica y fotosíntesis: celdas ultradelgadas de germanio (30 citas), su efecto en el "
     "crecimiento de microalgas en fotobiorreactores (8 citas) y su desempeño con datos PV-GIS (0 citas).",
     "La Tabla IV del Word sitúa a Agert y su grupo en el núcleo de autores."),
    ("Q20", "¿Qué artículos publicó Jason A. Carlyon y tienen relación con los agrovoltaicos?",
     arts_where("SR in (select SR from ArticleAuthor where AuthorID like '%CARLYON%')"),
     "2 artículos sobre la bacteria Anaplasma phagocytophilum (Read et al., 2022, 16 citas; Oki et al., 2015, "
     "10 citas). Son de microbiología y no tienen relación con los agrovoltaicos.",
     "El Word lo ubica en una comunidad de autores ajena al tema."),
    ("Q21", "¿Qué artículos publicó Acta Horticulturae en el corpus y de qué tratan?",
     arts_where("source_title='ACTA HORTIC'"),
     "4 artículos: arreglos fotovoltaicos sobre un huerto de perales (Singh R., 2024); pepino con solución "
     "nutritiva oxigenada en invernaderos (Singh P., 2021); temperatura y humedad en un invernadero plástico "
     "asimétrico (Hu, 2018); estrategias pre y poscosecha para compuestos bioactivos (Gil, 2015).",
     "El Word la señala como la revista con más artículos, de bajo impacto."),
    ("Q22", "¿Qué artículos con participación de Alemania se publicaron desde 2022 y cuáles tratan sobre agrovoltaicos?",
     arts_where("year>=2022 and SR in (select SR from Affiliation where Country='GERMANY')"),
     "4 artículos. Solo uno trata de agrovoltaica: el desempeño de una celda solar espectralmente selectiva con "
     "datos PV-GIS (Osterthun, 2022). Los otros tratan de producción agrícola resiliente y climáticamente "
     "neutra (Uhl, 2023), manejo de lodos fecales en asentamientos de desplazados (Orugba, 2024) y producción "
     "de metanol renovable (Svitnič, 2024).",
     "El Word dice que Alemania tiene tres artículos recientes (2022–2024) dedicados a agrovoltaicos."),
]

# ── RAG: (id, pregunta, sr_fuente, respuesta_esperada, relación con el Word) ──
RAG_Q = [
    ("Q23", "¿Qué estudio del corpus usa energía solar para compostar lodos de depuración y qué encontró?",
     "CHEN Y, 2014, WASTE MANAGE",
     "Chen et al. (2014) compararon tres reactores (ordinario, de invernadero y solar) para compostar lodos "
     "municipales: el reactor solar dio calor más estable y fue el único que mantuvo más de 55 °C por más de "
     "3 días, mejorando la calidad del compost como fertilizante.",
     "Descrito en el Word (periodo 2013–2019)."),
    ("Q24", "¿Cómo funciona el secador de invernadero híbrido para tomates estudiado en el corpus?",
     "AZAM MM, 2020, ENERGY",
     "Es un secador de invernadero autónomo de convección forzada que integra un sistema fotovoltaico y un "
     "colector solar; se evaluó con un modelo térmico y distintos pretratamientos del tomate (el escaldado "
     "15 min aceleró el secado), comparado con el secado al sol.",
     "Descrito en el Word (periodo 2020–2025)."),
    ("Q25", "¿Qué propone el estudio sobre agrovoltaica y acuaponía en azoteas urbanas?",
     "RONY JH, 2024, J FINANC",
     "Integrar paneles solares (8 de 500 W, unos 4.000 W) y un sistema acuapónico (peces y plantas sin suelo en "
     "circuito cerrado) en azoteas de Dhaka, Bangladesh, con recolección de agua lluvia, para producir energía y "
     "alimentos donde falta suelo.",
     "Descrito en el Word (colaboración Bangladesh–Japón)."),
    ("Q26", "¿Qué herramienta del corpus sirve para comparar y elegir configuraciones de sistemas agrovoltaicos?",
     "BELLONE Y, 2024, ",
     "Un marco basado en simulación que combina indicadores (proporción de cultivo, energía por hectárea, "
     "rendimiento energético específico, eficiencia del agua, inversión inicial) en un análisis multicriterio, "
     "y clasifica cuatro configuraciones (vertical, monoaxial interespaciada, monoaxial elevada y biaxial "
     "elevada) según el entorno.",
     "Descrito en el Word (Italia–Suiza), que lo fecha en 2020; en el corpus es de 2024."),
    ("Q27", "¿Qué tratamiento se aplica al digestato de estiércol en el estudio de secado solar del corpus?",
     "MOREY L, 2023, J ENVIRON MANAGE",
     "Secado solar combinado con acidificación del digestato y de su fracción sólida, para reducir el contenido "
     "de agua y las emisiones gaseosas; el digestato acidificado conservó más nitrógeno.",
     "Descrito en el Word (comunidad naranja)."),
    ("Q28", "¿Qué diseña el estudio sobre el secador solar de invernadero en Filipinas?",
     "BASILIO GA, 2023, J FINANC",
     "Un sistema de control para un secador solar de invernadero, que reduce el riesgo de los trabajadores "
     "expuestos a altas temperaturas y da más flexibilidad al secado de productos agrícolas.",
     "Descrito en el Word (comunidad verde)."),
    ("Q29", "¿Qué sistema se usó para calentar la digestión anaerobia de lodos activados excedentes?",
     "MENG C, 2009, ",
     "Un sistema integrado de invernadero y calentador solar que mantuvo la temperatura de digestión mesofílica "
     "y termofílica, elevándola entre unos 10 y 28 °C según la estación y aumentando la producción de biogás.",
     "El Word solo cita su DOI y 13 citas."),
    ("Q30", "¿Qué estudio del corpus seca mangos con energía solar y con qué propósito?",
     "RANKINS J, 2008, J AM OPTOM ASSOC",
     "Rankins et al. (2008): secado solar de 3,75 t de mango fresco (360 kg secos) para reducir las pérdidas "
     "poscosecha y conservar beta-caroteno frente a la deficiencia de vitamina A en África occidental francófona.",
     "El Word solo cita su DOI y 13 citas."),
    ("Q31", "¿Qué tipo de celda solar se propone en el corpus para combinar fotovoltaica y fotosíntesis?",
     "OSTERTHUN N, 2021, OPT EXPRESS",
     "Una celda solar espectralmente selectiva de germanio ultradelgado, cuya transmisión se ajusta al espectro "
     "de absorción de la clorofila, para usarla en sistemas agrovoltaicos, invernaderos y fotobiorreactores.",
     "El Word solo menciona a sus autores (grupo Agert)."),
    ("Q32", "¿Qué tipos de productos agrícolas se secan con energía solar en los artículos del corpus?",
     "",
     "Entre otros: tomate (y pasta y hojuelas de tomate), cacao, mango, amla, pescado, residuos de "
     "cultivos, digestato y lodos. 26 artículos del corpus tienen 'dry' o 'drying' en el título.",
     "El Word dice que la mayoría de trabajos de 2020–2025 son secadores solares."),
]


def run(db, sql):
    return [list(r) for r in db.execute(sql).fetchall()]


def main():
    db = sqlite3.connect(DB)
    items = []
    for qid, preg, sql, resp, word in SQL_Q:
        items.append({"id": qid, "tipo": "SQL puro", "pregunta": preg, "respuesta_esperada": resp,
                      "gold_sql": sql, "gold_bd": run(db, sql), "relacion_word": word})
    for qid, preg, sql, resp, word in HYB_Q:
        rows = run(db, sql)
        items.append({"id": qid, "tipo": "Híbrida", "pregunta": preg, "respuesta_esperada": resp,
                      "gold_sql": sql, "gold_bd": rows, "sr_fuente": [r[0] for r in rows], "relacion_word": word})
    for qid, preg, sr, resp, word in RAG_Q:
        if sr:
            assert db.execute("select 1 from Article where SR=? and ismainarticle=1", (sr,)).fetchone(), sr
        items.append({"id": qid, "tipo": "RAG puro", "pregunta": preg, "respuesta_esperada": resp,
                      "sr_fuente": [sr] if sr else [], "relacion_word": word})
    assert len(items) == 32 and len({i["id"] for i in items}) == 32

    (HERE / f"{NAME}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown legible
    md = ["# Dataset Scopus — 32 preguntas (agrovoltaicos)\n",
          "Todas las respuestas esperadas salen del corpus **Scopus** (66 artículos principales), que es lo "
          "que consulta el agente. La columna «Relación con el Word» es solo referencia.\n"]
    for tipo, titulo in (("SQL puro", "SQL puro (Q01–Q12)"), ("Híbrida", "Híbridas: SQL + contenido (Q13–Q22)"),
                         ("RAG puro", "RAG puro (Q23–Q32)")):
        md.append(f"\n## {titulo}\n")
        for it in (i for i in items if i["tipo"] == tipo):
            md.append(f"### {it['id']}. {it['pregunta']}")
            md.append(f"- **Respuesta esperada:** {it['respuesta_esperada']}")
            if it.get("gold_sql"):
                md.append(f"- Resultado en la BD: `{json.dumps(it['gold_bd'], ensure_ascii=False)[:400]}`")
                md.append(f"- SQL de referencia: `{it['gold_sql']}`")
            if it.get("sr_fuente"):
                md.append(f"- Artículo(s) fuente: {', '.join('`' + s + '`' for s in it['sr_fuente'])}")
            md.append(f"- Relación con el Word: {it['relacion_word']}\n")
    (HERE / f"{NAME}.md").write_text("\n".join(md), encoding="utf-8")

    # Excel para revisar y anotar a mano
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "preguntas"
    head = ["id", "tipo", "pregunta", "respuesta_esperada", "gold_sql", "gold_bd", "sr_fuente",
            "relacion_word", "respuesta_modelo", "correcta (sí/parcial/no)", "comentario"]
    ws.append(head)
    fills = {"SQL puro": "FFF2A8", "Híbrida": "AEEFF0", "RAG puro": "B8F5B8"}
    for it in items:
        ws.append([it["id"], it["tipo"], it["pregunta"], it["respuesta_esperada"], it.get("gold_sql", ""),
                   json.dumps(it.get("gold_bd", ""), ensure_ascii=False) if it.get("gold_sql") else "",
                   "; ".join(it.get("sr_fuente", [])), it["relacion_word"], "", "", ""])
        ws.cell(ws.max_row, 2).fill = PatternFill("solid", fgColor=fills[it["tipo"]])
    for c in ws[1]:
        c.font = Font(bold=True)
    for col, w in zip("ABCDEFGHIJK", (6, 10, 45, 60, 40, 30, 28, 40, 50, 14, 30)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "C2"
    wb.save(HERE / f"{NAME}.xlsx")

    print(f"OK: {NAME}.json / .md / .xlsx")
    for it in items:
        if it.get("gold_sql"):
            print(it["id"], json.dumps(it["gold_bd"], ensure_ascii=False)[:150])


if __name__ == "__main__":
    main()
