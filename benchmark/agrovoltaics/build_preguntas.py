"""
build_preguntas.py — Genera preguntas_32.json y preguntas_32.md
================================================================
32 preguntas basadas en el artículo Word de los estudiantes (articulo_agrovoltaicos.txt)
y en el corpus Scopus de agrovoltaicos (data/sessions/Agrovoltaics).

  Q01-Q12  SQL puro   : dato del corpus; se registra además la cifra que reporta el artículo.
  Q13-Q22  Híbridas   : la pregunta trae una afirmación del artículo y pide contrastarla con la BD.
  Q23-Q32  RAG puro   : contenido de artículos que el Word cita y que están (o no) en el corpus.

Regla: el gold de las preguntas con SQL se EJECUTA sobre la BD (no se copia del artículo).
El artículo usa Scopus+WoS (77 artículos) y la BD solo Scopus (66 principales).

Uso (desde demo_limpio):  python benchmark/agrovoltaics/build_preguntas.py
"""

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent.parent / "data" / "sessions" / "Agrovoltaics" / "db" / "bibliometria.db"

MAIN = "SR in (select SR from Article where ismainarticle=1)"


def country_count(c):
    return f"select count(distinct SR) from Affiliation where Country='{c}' and {MAIN}"


# (id, tipo, pregunta, seccion, afirmacion/cifra del artículo, gold_sql, nota)
SQL_Q = [
    ("Q01", "¿Cuántos artículos principales hay en el corpus?", "Search output / Conclusiones",
     "77 publicaciones únicas (Scopus + WoS)",
     "select count(*) from Article where ismainarticle=1",
     "El artículo une Scopus y WoS; la BD es solo Scopus."),
    ("Q02", "¿En qué año se publicaron más artículos y cuántos?", "Scientific Annual Production",
     "2024 fue el año más productivo: Scopus 12 artículos (15 combinando WoS)",
     "select year,count(*) n from Article where ismainarticle=1 group by year order by n desc limit 1",
     ""),
    ("Q03", "¿Cuántos artículos se publicaron entre 2020 y 2025?", "Periodo de consolidación (2020–2025)",
     "49 artículos publicados en el periodo",
     "select count(*) from Article where ismainarticle=1 and year between 2020 and 2025", ""),
    ("Q04", "¿Qué país aparece en más artículos y cuántos?", "Country Analysis / Tabla II",
     "China: 21 artículos (22,34 %)",
     "select Country,count(distinct SR) n from Affiliation where " + MAIN +
     " and Country!='NO COUNTRY' group by Country order by n desc limit 1", ""),
    ("Q05", "¿En cuántos artículos participa al menos una institución de Alemania?", "Tabla II",
     "Alemania: 8 artículos (8,51 %)", country_count("GERMANY"), ""),
    ("Q06", "¿En cuántos artículos participa al menos una institución de India?", "Tabla II",
     "India: 10 artículos (10,64 %)", country_count("INDIA"), ""),
    ("Q07", "¿Qué revista tiene más artículos en el corpus y cuántos?", "Journal Analysis / Tabla III",
     "Acta Horticulturae: 4 artículos en Scopus",
     "select source_title,count(*) n from Article where ismainarticle=1 and source_title is not null "
     "group by source_title order by n desc limit 1", ""),
    ("Q08", "¿Cuántos artículos del corpus se publicaron en AIP Conference Proceedings?", "Journal Analysis / Tabla III",
     "AIP Conference Proceedings: 3 artículos en Scopus",
     "select count(*) from Article where ismainarticle=1 and source_title='AIP CONF PROC'", ""),
    ("Q09", "¿Cuántos artículos tiene Carsten Agert en el corpus y cuántas citas acumulan en total?", "Tabla IV",
     "C. Agert Carsten: 3 artículos, 38 citas",
     "select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR "
     "where aa.AuthorID like 'C_AGERT%' and a.ismainarticle=1", ""),
    ("Q10", "¿Cuántos artículos tiene J.A. Carlyon en el corpus y cuántas citas acumulan en total?", "Tabla IV",
     "J.A. Carlyon: 2 artículos, 26 citas",
     "select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR "
     "where aa.AuthorID like '%CARLYON%' and a.ismainarticle=1", ""),
    ("Q11", "¿Cuántos autores tienen 3 o más artículos en el corpus?", "Análisis de autores / Conclusiones",
     "Ocho investigadores registran tres publicaciones",
     "select count(*) from (select AuthorID from ArticleAuthor where " + MAIN +
     " group by AuthorID having count(distinct SR)>=3)", "El artículo cuenta 8; la tabla IV lista 8 con 3 papers."),
    ("Q12", "¿En cuántos artículos participa al menos una institución de Bangladesh?", "Tabla II",
     "Bangladesh: 3 artículos (3,19 %)", country_count("BANGLADESH"), ""),
]

HYB_Q = [
    ("Q13", "El artículo afirma que entre 2007 y 2012 se publicaron 5 artículos que acumularon 46 citas. "
            "¿Es consistente con la base de datos?", "Periodo de baja producción (2007–2012)",
     "5 artículos, 46 citas",
     "select count(*),sum(cited_by) from Article where ismainarticle=1 and year between 2007 and 2012"),
    ("Q14", "El artículo dice que 2015 tuvo 5 artículos y 104 citaciones. ¿Qué muestra la base de datos?",
     "Periodo 2013–2019", "2015: 5 artículos, 104 citas",
     "select count(*),sum(cited_by) from Article where ismainarticle=1 and year=2015"),
    ("Q15", "El artículo señala que los artículos de 2014 sumaron 78 citaciones. ¿Se confirma en la base de datos?",
     "Periodo 2013–2019", "2014: 78 citas",
     "select sum(cited_by) from Article where ismainarticle=1 and year=2014"),
    ("Q16", "El artículo reporta que Scopus registró 12 artículos en 2024. ¿Cuántos hay en la base de datos?",
     "Scientific Annual Production", "Scopus 2024: 12 artículos",
     "select count(*) from Article where ismainarticle=1 and year=2024"),
    ("Q17", "El artículo afirma que China tiene 21 artículos (22,34 % de la producción). "
            "¿Qué muestra la base de datos para China?", "Country Analysis / Tabla II",
     "China: 21 artículos (22,34 %)", country_count("CHINA")),
    ("Q18", "El artículo dice que el artículo de Azam et al. es el más citado con términos agrovoltaico/fotovoltaico, "
            "con 68 citas y publicado en 2024. ¿Qué dice la base de datos sobre ese artículo?",
     "Periodo 2020–2025", "Azam et al.: 68 citas, publicado en 2024 (Egipto); la referencia lo fecha en 2020",
     "select title,year,cited_by from Article where ismainarticle=1 and title like 'THERMAL ANALYSIS OF PV SYSTEM%'"),
    ("Q19", "La Tabla III del artículo da 3 artículos de Journal of Food Process Engineering en Scopus, "
            "mientras el texto dice 2. ¿Cuántos hay en la base de datos?", "Tabla III y texto",
     "JFPE: 3 en Scopus (tabla) / 2 (texto)",
     "select count(*) from Article where ismainarticle=1 and source_title='J FOOD PROCESS ENG'"),
    ("Q20", "El artículo cita a Hassanein et al. (2015) con 38 citaciones. ¿Existe ese artículo en la base de datos?",
     "Periodo 2013–2019", "Hassanein 2015: 38 citas, Q1",
     "select count(*) from Article where lower(doi) like '%10.1016/j.ecoleng.2015.05.010%'"),
    ("Q21", "El artículo afirma que Alemania tiene tres artículos recientes (2022, 2023 y 2024) dedicados "
            "explícitamente a agrovoltaicos. ¿Qué artículos alemanes de 2022 en adelante hay en la base de datos?",
     "Country Analysis", "Alemania: 3 artículos recientes (2022, 2023, 2024) sobre agrovoltaicos",
     "select year,title from Article where ismainarticle=1 and year>=2022 and SR in "
     "(select SR from Affiliation where Country='GERMANY') order by year"),
    ("Q22", "El artículo indica que Tailandia tiene 5 artículos. ¿Es correcto según la base de datos?", "Tabla II",
     "Tailandia: 5 artículos (5,32 %)", country_count("THAILAND")),
]

# (id, pregunta, seccion, respuesta_esperada, sr_fuente, nota)
RAG_Q = [
    ("Q23", "¿Qué estudió el artículo de Chen et al. (2014) sobre compostaje de lodos y qué concluyó?",
     "Periodo 2013–2019",
     "Evaluó el uso de energía solar (invernadero/reactor solar pasivo) para acelerar el compostaje de lodos "
     "de depuración: la radiación elevó la temperatura, mejoró la deshidratación, la estabilización y la "
     "reducción de patógenos, y dio un compost apto como fertilizante agrícola.",
     "CHEN Y, 2014, WASTE MANAGE", "El abstract compara 3 reactores (ordinario, invernadero, solar) y reporta >55 °C durante más de 3 días en el solar."),
    ("Q24", "¿Qué sistema analiza el estudio del secador de invernadero híbrido para tomates y cómo funciona?",
     "Periodo 2020–2025",
     "Un secador de invernadero híbrido que combina un colector solar térmico y un sistema fotovoltaico: la "
     "energía térmica calienta el aire y los paneles alimentan ventiladores (convección forzada), acelerando "
     "el secado sin energía externa.",
     "AZAM MM, 2020, ENERGY", ""),
    ("Q25", "¿Qué propone el estudio de Bangladesh y Japón sobre azoteas con paneles solares y acuaponía?",
     "Country Analysis",
     "Un modelo de uso dual del espacio: paneles solares en azoteas generan electricidad mientras bajo su "
     "sombra se desarrolla un sistema acuapónico (cultivo de plantas y cría de peces en circuito cerrado), "
     "mejorando el uso del suelo urbano, reduciendo costos energéticos y aumentando la producción de alimentos.",
     "RONY JH, 2024, J FINANC", "El abstract lo sitúa en Dhaka y menciona 8 paneles de 500 W y recolección de agua lluvia."),
    ("Q26", "¿Qué herramienta desarrolla el estudio de colaboración entre Italia y Suiza para evaluar sistemas agrovoltaicos?",
     "Country Analysis",
     "Una herramienta de simulación que evalúa diseños de sistemas agrovoltaicos considerando generación "
     "eléctrica e impacto sobre los cultivos, con indicadores (irradiancia, rendimiento agrícola, producción "
     "de energía) y análisis multicriterio para comparar configuraciones.",
     "BELLONE Y, 2024, ", "El artículo dice 2020; la BD lo registra en 2024 (error del Word)."),
    ("Q27", "¿Qué tratamiento aplica el estudio sobre digestato de estiércol y por qué el artículo lo considera tangencial a los agrovoltaicos?",
     "Author Analysis",
     "Aplica secado solar combinado con acidificación al digestato para reducir su contenido de agua y las "
     "emisiones gaseosas, produciendo fertilizantes; es valorización de residuos y no integra producción "
     "agrícola con generación eléctrica.",
     "MOREY L, 2023, J ENVIRON MANAGE", ""),
    ("Q28", "¿Qué diseña el estudio del secador solar de invernadero publicado en IPEC 2023?",
     "Author Analysis",
     "Un sistema de control para un secador solar de invernadero, orientado a la eficiencia térmica y al "
     "diseño del secado (reduce el riesgo para trabajadores por altas temperaturas y da flexibilidad); no "
     "integra producción simultánea de electricidad y alimentos.",
     "BASILIO GA, 2023, J FINANC", "Contexto de Filipinas en el abstract."),
    ("Q29", "¿Qué sistema evaluó el artículo de Meng et al. (2009) y con qué fin?",
     "Periodo de baja producción",
     "Un sistema integrado de invernadero y calentador solar para calentar y mantener la temperatura del "
     "digestor en la digestión anaerobia de lodos activados excedentes, aumentando la temperatura y la "
     "producción de biogás según la estación.",
     "MENG C, 2009, ", "El artículo lo cita como de bajo impacto (13 citas)."),
    ("Q30", "¿De qué trata el artículo sobre secado solar de mangos en África occidental francófona?",
     "Periodo de baja producción",
     "Secado solar de mangos para reducir las pérdidas poscosecha y conservar beta-caroteno (provitamina A), "
     "frente a la deficiencia de vitamina A en niños: 3,75 t de mango fresco rindieron 360 kg de mango seco.",
     "RANKINS J, 2008, J AM OPTOM ASSOC", "El artículo lo cita como de bajo impacto (13 citas)."),
    ("Q31", "¿Qué proponen Hassanein et al. (2015) sobre biodigestores subterráneos y energía solar?",
     "Periodo 2013–2019",
     "Según el Word: un invernadero construido sobre biodigestores subterráneos que aprovecha energía solar "
     "térmica para calentarlos sin combustibles fósiles, validado con simulación y experimento. "
     "PERO este artículo NO está en el corpus Scopus: el sistema debe decir que no lo encuentra.",
     "", "Pregunta trampa: mide si el sistema inventa. Solo indexado en WoS."),
    ("Q32", "¿Qué tipos de productos agrícolas se secan con energía solar en los artículos del corpus?",
     "Periodo 2020–2025",
     "Según el Word, la mayoría de trabajos de 2020–2025 implementan secadores solares para productos "
     "agrícolas o bioproductos. En el corpus hay 26 artículos con 'dry/drying' en el título; entre ellos "
     "tomate, cacao, mango, amla, pescado, residuos de cultivos y lodos.",
     "", "Pregunta temática: no hay una única fuente."),
]


def run(db, sql):
    return [list(r) for r in db.execute(sql).fetchall()]


def main():
    db = sqlite3.connect(DB)
    items = []
    for qid, preg, secc, claim, sql, nota in SQL_Q:
        items.append({"id": qid, "tipo": "SQL puro", "pregunta": preg, "seccion_articulo": secc,
                      "cifra_articulo": claim, "gold_sql": sql, "gold_bd": run(db, sql), "nota": nota})
    for qid, preg, secc, claim, sql in HYB_Q:
        items.append({"id": qid, "tipo": "Híbrida", "pregunta": preg, "seccion_articulo": secc,
                      "afirmacion_articulo": claim, "gold_sql": sql, "gold_bd": run(db, sql), "nota": ""})
    for qid, preg, secc, esperado, sr, nota in RAG_Q:
        en_corpus = bool(sr) and bool(db.execute("select 1 from Article where SR=?", (sr,)).fetchone())
        items.append({"id": qid, "tipo": "RAG puro", "pregunta": preg, "seccion_articulo": secc,
                      "respuesta_esperada": esperado, "sr_fuente": sr,
                      "en_corpus": en_corpus if sr else (None if qid == "Q32" else False), "nota": nota})
    assert len(items) == 32 and len({i["id"] for i in items}) == 32

    (HERE / "preguntas_32.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Benchmark agrovoltaicos — 32 preguntas\n",
          "Base: artículo Word de los estudiantes + corpus Scopus (66 artículos principales). "
          "El gold SQL se ejecuta sobre la BD; la cifra del artículo se muestra al lado para contrastar "
          "(el Word usa Scopus + WoS, por eso hay diferencias esperables).\n"]
    for tipo, titulo in (("SQL puro", "SQL puro (Q01–Q12)"), ("Híbrida", "Híbridas: afirmación del artículo vs BD (Q13–Q22)"),
                         ("RAG puro", "RAG puro (Q23–Q32)")):
        md.append(f"\n## {titulo}\n")
        for it in (i for i in items if i["tipo"] == tipo):
            md.append(f"### {it['id']}. {it['pregunta']}")
            md.append(f"- Sección del artículo: {it['seccion_articulo']}")
            if it["tipo"] == "RAG puro":
                md.append(f"- Respuesta esperada: {it['respuesta_esperada']}")
                md.append(f"- Fuente en corpus: `{it['sr_fuente'] or '—'}` (en corpus: {it['en_corpus']})")
            else:
                dato = it.get("cifra_articulo") or it.get("afirmacion_articulo")
                md.append(f"- Lo que dice el artículo: {dato}")
                md.append(f"- Respuesta en la BD: `{json.dumps(it['gold_bd'], ensure_ascii=False)}`")
                md.append(f"- SQL gold: `{it['gold_sql']}`")
            if it["nota"]:
                md.append(f"- Nota: {it['nota']}")
            md.append("")
    (HERE / "preguntas_32.md").write_text("\n".join(md), encoding="utf-8")
    print("OK: 32 preguntas")
    for it in items:
        if it["tipo"] != "RAG puro":
            print(it["id"], it["gold_bd"])
        else:
            print(it["id"], "en_corpus=", it["en_corpus"])


if __name__ == "__main__":
    main()
