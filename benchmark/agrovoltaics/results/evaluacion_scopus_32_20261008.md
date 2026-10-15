# Evaluación del agente — 32 preguntas solo Scopus, después de los cambios (2026-10-08)

- **Modelo:** `glm4:9b` vía Ollama.
- **Corrida:** `respuestas_preguntas_scopus_32_20261008_095238_glm4-9b.json`
- **Cambios respecto a la línea base (2026-10-07):** el esquema explica `ismainarticle` (1 = principal, 0 = referencia); respaldo en referencias con aviso; RAG solo sobre artículos principales; pregunta traducida al inglés para la búsqueda semántica; esquema mostrado como `tabla: col, col` y reparación automática de `a(sr)`; memoria de artículos para preguntas de seguimiento (no se evalúa aquí: el dataset no tiene preguntas encadenadas).
- **Puntuación:** manual, misma escala que la línea base. 5 = correcta y completa · 4 = correcta con un detalle menor · 3 = parcial · 2 = mayormente incorrecta pero en la dirección correcta · 1 = incorrecta, vacía, error o inventada.

## Resumen

| Bloque | Preguntas | Línea base 07-oct | Ahora | Cambio |
|---|---|---|---|---|
| SQL puro | 12 | 1.25 | 3.00 | +1.75 |
| Híbridas | 10 | 1.10 | 1.50 | +0.40 |
| RAG puro | 10 | 1.60 | 3.20 | +1.60 |
| **Total** | **32** | **1.31** | **2.59** | **+1.28** |

Distribución de notas ahora: 1: 14 · 2: 4 · 3: 2 · 4: 5 · 5: 7.

## Qué mejoró

- **SQL:** 6 de 12 correctas (antes ninguna). El filtro de artículos principales aparece solo en la mayoría de consultas y ya no hay errores por `a(sr)`.
- **RAG:** el artículo correcto aparece en las fuentes en 9 de 9 preguntas sobre un artículo concreto (antes, 1). Q23, Q24, Q27 y Q28 pasaron de 1 a 4–5.

## Qué sigue fallando (ordenado por cuántas preguntas afecta)

1. **Formatos de valores** (Q05, Q08, Q09, Q10, Q19, Q20, Q22): `'Germany'` vs `GERMANY`, `'Carsten Agert'` vs `AGERT C.`, `'AIP Conference Proceedings'` vs `AIP CONF PROC`. El SQL es válido pero devuelve 0. Es ahora la causa que más puntos quita.
2. **Híbridas que no filtran principales** (Q03, Q15, Q16, Q18): en preguntas de "el más citado de 2015" o por país el modelo todavía olvida `ismainarticle = 1`.
3. **Respuestas RAG demasiado cortas o falsos "no encontrado"** (Q26, Q29, Q30, Q31): el artículo correcto está en las fuentes, pero el modelo responde con un fragmento o con `NO_ENCONTRADO`. Lo provoca la regla nueva que le pide responder solo `NO_ENCONTRADO` si nada sirve: glm4 la interpreta como "responde lo mínimo".
4. **Columnas o tablas inventadas** (Q07, Q14, Q21): `citation.cited_by`, tabla `source_title`, columna ambigua `journal`.
5. **Inventa cuando el SQL falla** (Q19): sigue afirmando que el autor publicó artículos que en realidad salieron del RAG.

## Pregunta por pregunta

### SQL puro (Q01–Q12)

#### Q01 · Nota: 5/5 (antes 4/5)
- **Pregunta:** ¿Cuántos artículos principales hay en el corpus?
- **Esperada:** 66 artículos principales.
- **Respuesta del modelo** (ruta `sql`): Hay 66 artículos principales en el corpus.
- **SQL del modelo:** `SELECT COUNT(*) FROM article WHERE ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 66, con el filtro de artículos principales.

#### Q02 · Nota: 5/5 (antes 1/5)
- **Pregunta:** ¿En qué año se publicaron más artículos y cuántos?
- **Esperada:** 2024, con 13 artículos.
- **Respuesta del modelo** (ruta `sql`): En el año 2024 se publicaron más artículos, con un total de 13.
- **SQL del modelo:** `SELECT CAST(year AS INTEGER), COUNT(*) FROM article WHERE ismainarticle = 1 GROUP BY year ORDER BY COUNT(*) DESC LIMIT 1;`
- **Por qué esa nota:** Correcta: 2024 con 13.

#### Q03 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Cuántos artículos se publicaron entre 2020 y 2025?
- **Esperada:** 45 artículos.
- **Respuesta del modelo** (ruta `sql`): Entre 2020 y 2025 se publicaron un total de 507 artículos.
- **SQL del modelo:** `SELECT COUNT(DISTINCT sr) AS total_articles FROM article WHERE CAST(year AS INTEGER) BETWEEN 2020 AND 2025;`
- **Por qué esa nota:** No filtra artículos principales: cuenta también las referencias (507 en vez de 45).

#### Q04 · Nota: 5/5 (antes 1/5)
- **Pregunta:** ¿Qué país aparece en más artículos y en cuántos?
- **Esperada:** China, en 17 artículos.
- **Respuesta del modelo** (ruta `sql`): El país que aparece en más artículos es China, con un total de 17 artículos.
- **SQL del modelo:** `SELECT country, COUNT(DISTINCT a.sr) AS num_articles FROM article a JOIN affiliation af ON a.sr = af.sr WHERE a.ismainarticle = 1 GROUP BY country ORDER BY num_articles DESC LIMIT 1;`
- **Por qué esa nota:** Correcta: China, 17 artículos.

#### Q05 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿En cuántos artículos participa al menos una institución de Alemania?
- **Esperada:** 7 artículos.
- **Respuesta del modelo** (ruta `sql`): En el corpus académico consultado, no hay artículos en los que participe al menos una institución de Alemania.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN affiliation af ON aa.authorid = af.authorid WHERE af.country = 'Germany' AND a.ismainarticle = 1;`
- **Por qué esa nota:** SQL válido, pero busca 'Germany' con = y la BD guarda 'GERMANY': responde que no hay ninguno (son 7).

#### Q06 · Nota: 5/5 (antes 1/5)
- **Pregunta:** ¿En cuántos artículos participa al menos una institución de India?
- **Esperada:** 8 artículos.
- **Respuesta del modelo** (ruta `sql`): En total, participan al menos en 8 artículos con una institución de India.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN affiliation af ON aa.authorid = af.authorid WHERE af.country LIKE 'India' AND a.ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 8. Usó LIKE 'India', que en SQLite no distingue mayúsculas.

#### Q07 · Nota: 1/5 (antes 1/5)
- **Pregunta:** Entre los artículos que tienen revista registrada, ¿qué revista concentra más artículos y cuántos?
- **Esperada:** Acta Horticulturae (ACTA HORTIC), con 4 artículos.
- **Respuesta del modelo** (ruta `sql`): Lo siento, no pude obtener los resultados. Hubo un error al consultar la base de datos: Error SQLite: ambiguous column name: journal
- **SQL del modelo:** `SELECT journal, COUNT(*) AS num_articles FROM article JOIN journal ON article.source_title = journal.journal WHERE article.ismainarticle = 1 AND article.source_title IS NOT NULL GROUP BY journal ORDER BY num_articles DES…`
- **Por qué esa nota:** Error SQL: columna 'journal' ambigua (está en dos tablas).

#### Q08 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Cuántos artículos del corpus se publicaron en AIP Conference Proceedings?
- **Esperada:** 3 artículos.
- **Respuesta del modelo** (ruta `sql`): No se encontraron artículos del corpus publicados en AIP Conference Proceedings.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE a.source_title LIKE '%AIP Conference Proceedings%' AND a.ismainarticle = 1;`
- **Por qué esa nota:** Busca 'AIP Conference Proceedings', pero la BD guarda 'AIP CONF PROC': responde 0.

#### Q09 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Cuántos artículos tiene Carsten Agert en el corpus y cuántas citas suman?
- **Esperada:** 3 artículos con 38 citas en total.
- **Respuesta del modelo** (ruta `sql`): Carsten Agert no tiene artículos en el corpus, y por lo tanto, no hay citas asociadas.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) AS num_articles, SUM(CAST(a.cited_by AS INTEGER)) AS total_citations FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid WHERE au.authorname = 'Car…`
- **Por qué esa nota:** Busca 'Carsten Agert', pero la BD guarda 'AGERT C.': dice que no tiene artículos.

#### Q10 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Cuántos artículos tiene Jason A. Carlyon en el corpus y cuántas citas suman?
- **Esperada:** 2 artículos con 26 citas en total.
- **Respuesta del modelo** (ruta `sql`): Jason A. Carlyon tiene 0 artículos en el corpus y suman 0 citas.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) AS num_articles, SUM(CAST(a.cited_by AS INTEGER)) AS total_citations FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid WHERE au.authorname LIKE '…`
- **Por qué esa nota:** Busca 'Jason A. Carlyon', pero la BD guarda 'CARLYON J.A.': dice que tiene 0.

#### Q11 · Nota: 5/5 (antes 1/5)
- **Pregunta:** ¿Qué autores tienen 3 o más artículos en el corpus?
- **Esperada:** 5 autores, todos con 3 artículos: Carsten Agert, Kai Gehrke, Martin Vehse, Nils Neugebohrn y Norbert Osterthun.
- **Respuesta del modelo** (ruta `sql`): Los autores con 3 o más artículos en el corpus son: 1. C., AGERT, CARSTEN (3 artículos) 2. K., GEHRKE, KAI (3 artículos) 3. M., VEHSE, MARTIN (3 artículos) 4. N., NEUGEBOHRN, NILS (3 artículos) 5. N., OSTERTHUN, NORBERT (3 artículos)
- **SQL del modelo:** `SELECT a.authorname, COUNT(DISTINCT aa.sr) AS articles_count FROM author a JOIN articleauthor aa ON a.authorid = aa.authorid WHERE aa.sr IN (SELECT sr FROM article WHERE ismainarticle = 1) GROUP BY a.authorname HAVING CO…`
- **Por qué esa nota:** Correcta: los 5 autores con 3 artículos cada uno.

#### Q12 · Nota: 5/5 (antes 1/5)
- **Pregunta:** ¿Cuántas citas suman los artículos publicados en 2014?
- **Esperada:** 78 citas.
- **Respuesta del modelo** (ruta `sql`): Los artículos publicados en 2014 suman un total de 78 citas.
- **SQL del modelo:** `SELECT SUM(CAST(cited_by AS INTEGER)) AS total_citations FROM article WHERE CAST(year AS INTEGER) = 2014 AND ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 78 citas.

### Híbridas (Q13–Q22)

#### Q13 · Nota: 4/5 (antes 1/5)
- **Pregunta:** ¿Cuál es el artículo más citado del corpus y de qué trata?
- **Esperada:** «Powering agriculture: present status, future potential, and challenges of renewable energy applications» (Rahman et al., 2022, Renewable Energy), con 165 citas. Revisa el uso de energías renovables en la agricultura para reducir la dependencia de combustibles fósiles (secado de grano, fertilizantes, maquinaria, electricidad) y sus emisiones.
- **Respuesta del modelo** (ruta `sql`): El artículo más citado del corpus se titula "POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS". Este texto aborda el uso de energías renovables en la agricultura, sus desafíos y oportunidades para países e…
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE sr = ( SELECT sr FROM article WHERE ismainarticle = 1 ORDER BY CAST(cited_by AS INTEGER) DESC LIMIT 1 );`
- **Por qué esa nota:** Artículo correcto (Rahman 2022) y buen resumen; no da las 165 citas ni los autores.

#### Q14 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Cuál fue el artículo más citado publicado en 2014 y qué estudió?
- **Esperada:** Chen et al. (2014, Waste Management), con 59 citas: uso de energía solar en el compostaje de lodos de depuración; comparó reactores ordinario, de invernadero y solar, y el solar dio calor más estable (más de 55 °C durante más de 3 días).
- **Respuesta del modelo** (ruta `sql`): Lo siento, no pude obtener los resultados. Hubo un error al consultar la base de datos: Error SQLite: no such column: c.cited_by
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a WHERE CAST(a.year AS INTEGER) = 2014 AND CAST((SELECT MAX(c.cited_by) FROM citation c WHERE c.sr_ref = a.sr) AS INTEGER) = (SELECT MAX(CAST(c.cited_by AS INTEGER)) FROM citation)…`
- **Por qué esa nota:** Inventa la columna citation.cited_by: error SQL.

#### Q15 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Cuál fue el artículo más citado publicado en 2015 y de qué trata?
- **Esperada:** Fasahati et al. (2015, Energy), con 38 citas: impacto económico, energético y ambiental de la tecnología de deshidratación de alcohol en la producción de biocombustible a partir de algas pardas.
- **Respuesta del modelo** (ruta `hybrid`): El artículo más citado publicado en 2015 fue "HISAT: A FAST SPLICED ALIGNER WITH LOW MEMORY REQUIREMENTS". Este artículo se enfoca en el desarrollo de un alineador rápido para secuencias splicadas con bajas necesidades de memoria. Sin embargo, no hay informaci…
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE year = CAST('2015' AS INTEGER) ORDER BY CAST(cited_by AS INTEGER) DESC LIMIT 1;`
- **Por qué esa nota:** No filtra artículos principales: devuelve HISAT (bioinformática, una referencia).

#### Q16 · Nota: 1/5 (antes 1/5)
- **Pregunta:** Entre los artículos con 'photovoltaic', 'agrivoltaic' o 'PV' en el título, ¿cuál es el más citado y qué sistema analiza?
- **Esperada:** Azam et al. (2020, Energy), con 69 citas: un secador de invernadero híbrido para tomates que integra un sistema fotovoltaico y un colector solar.
- **Respuesta del modelo** (ruta `hybrid`): Entre los artículos con 'photovoltaic', 'agrivoltaic' o 'PV' en el título, el más citado es "POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS", publicado en la revista RENEW ENERGY en 2022. Este artículo h…
- **SQL del modelo:** `SELECT a.title, a.cited_by, aa.affiliation FROM article a JOIN articleauthor aa ON a.sr = aa.sr WHERE a.title LIKE '%photovoltaic%' OR a.title LIKE '%agrivoltaic%' OR a.title LIKE '%PV%' ORDER BY CAST(a.cited_by AS INTEG…`
- **Por qué esa nota:** El SQL no filtra principales y el OR mal agrupado; responde Rahman 2022 en vez de Azam 2020.

#### Q17 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Cuáles fueron los artículos más citados publicados entre 2007 y 2012 y de qué tratan?
- **Esperada:** Dos artículos con 13 citas cada uno: Meng et al. (2009), un sistema integrado de invernadero y calentador solar para la digestión anaerobia de lodos activados; y Rankins et al. (2008), el secado solar de mangos para conservar la provitamina A en África occidental francófona.
- **Respuesta del modelo** (ruta `hybrid`): Se encontraron 10 resultados. Columnas: title, abstract. Primer resultado: {'title': "PERRY'S CHEMICAL ENGINEERS' HANDBOOK", 'abstract': 'SECTION 1: CONVERSION FACTORS AND MATHEMATICAL SYMBOLS SECTION 2: PHYSICAL AND CHEMICAL DATA SECTION 3: MATHEMATICS SECTIO…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author a1 ON aa.authorid = a1.authorid WHERE CAST(a.year AS INTEGER) BETWEEN 2007 AND 2012 AND a.cited_by IS NOT NULL ORDER BY CAST(a.c…`
- **Por qué esa nota:** La síntesis falló y devolvió el texto de respaldo con una referencia (Perry's Handbook).

#### Q18 · Nota: 2/5 (antes 2/5)
- **Pregunta:** ¿Qué artículos tienen autores de Bangladesh y de qué tratan?
- **Esperada:** 3 artículos: Rahman et al. (2022), revisión de energías renovables en agricultura (165 citas); Rana et al. (2023), acuicultura marina y un secador de pescado inteligente basado en IoT; y Rony et al. (2024), agrovoltaica más acuaponía en azoteas urbanas de Dhaka.
- **Respuesta del modelo** (ruta `hybrid`): Los artículos con autores de Bangladesh que se encontraron en la consulta SQL son los siguientes: 1. **Título:** EXPERIMENTAL INVESTIGATION ON SOLAR DRYING OF FISH USING SOLAR TUNNEL DRYER **Abstract:** Este artículo presenta el rendimiento del secador solar d…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid JOIN affiliation af ON au.authorid = af.authorid WHERE af.country LIKE '%Bangladesh%' LIMIT 10;`
- **Por qué esa nota:** Sin filtro de principales: lista artículos de Bangladesh que no son los 3 del corpus; el RAG sí trajo a Rony 2024.

#### Q19 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Qué artículos publicó el grupo de Carsten Agert y de qué tratan?
- **Esperada:** 3 artículos (Osterthun et al., 2021–2022), todos sobre celdas solares espectralmente selectivas que combinan fotovoltaica y fotosíntesis: celdas ultradelgadas de germanio (30 citas), su efecto en el crecimiento de microalgas en fotobiorreactores (8 citas) y su desempeño con datos PV-GIS (0 citas).
- **Respuesta del modelo** (ruta `hybrid`): El grupo de Carsten Agert ha publicado varios artículos, aunque los resultados exactos de la consulta SQL no arrojaron información específica sobre sus publicaciones. A continuación, se presentan detalles sobre algunos de los artículos recuperados por búsqueda…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid WHERE au.authorname LIKE '%Carsten Agert%' AND a.ismainarticle = 1 LIMIT 10;`
- **Por qué esa nota:** Nombre mal escrito en el SQL ('Carsten Agert'); afirma que el grupo publicó varios artículos y describe los de Anaplasma: engañoso.

#### Q20 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Qué artículos publicó Jason A. Carlyon y tienen relación con los agrovoltaicos?
- **Esperada:** 2 artículos sobre la bacteria Anaplasma phagocytophilum (Read et al., 2022, 16 citas; Oki et al., 2015, 10 citas). Son de microbiología y no tienen relación con los agrovoltaicos.
- **Respuesta del modelo** (ruta `hybrid`): Jason A. Carlyon publicó artículos en diversas áreas de investigación, pero no se encontraron resultados específicos relacionados con los agrovoltaicos en la consulta SQL. Sin embargo, mediante búsqueda semántica, se identificaron artículos que podrían tener u…
- **SQL del modelo:** `SELECT a.title, a.abstract, a.year, CAST(a.cited_by AS INTEGER), a.author_keywords, a.doi, a.document_type, a.source_title, a.ismainarticle FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.author…`
- **Por qué esa nota:** Dice que no encontró a Carlyon (nombre mal escrito); tiene 2 artículos.

#### Q21 · Nota: 2/5 (antes 1/5)
- **Pregunta:** ¿Qué artículos publicó Acta Horticulturae en el corpus y de qué tratan?
- **Esperada:** 4 artículos: arreglos fotovoltaicos sobre un huerto de perales (Singh R., 2024); pepino con solución nutritiva oxigenada en invernaderos (Singh P., 2021); temperatura y humedad en un invernadero plástico asimétrico (Hu, 2018); estrategias pre y poscosecha para compuestos bioactivos (Gil, 2015).
- **Respuesta del modelo** (ruta `hybrid`): Acta Horticulturae publicó varios artículos en el corpus, aunque no se encontraron resultados estructurados en la consulta SQL. A continuación, se presentan detalles sobre algunos de los artículos recuperados por búsqueda semántica: 1. **EFFECTS OF DIFFERENT F…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN source_title st ON a.source_title = st.sr WHERE st.title LIKE '%Acta Horticulturae%' AND a.ismainarticle = 1 LIMIT 10;`
- **Por qué esa nota:** SQL con tabla inventada; el RAG trajo 1–2 de los 4 de Acta Horticulturae, pero sin decir que son de esa revista.

#### Q22 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Qué artículos con participación de Alemania se publicaron desde 2022 y cuáles tratan sobre agrovoltaicos?
- **Esperada:** 4 artículos. Solo uno trata de agrovoltaica: el desempeño de una celda solar espectralmente selectiva con datos PV-GIS (Osterthun, 2022). Los otros tratan de producción agrícola resiliente y climáticamente neutra (Uhl, 2023), manejo de lodos fecales en asentamientos de desplazados (Orugba, 2024) y producción de metanol renovable (Svitnič, 2024).
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron artículos específicos con participación de Alemania que traten sobre agrovoltaicos publicados desde 2022 en la base de datos consultada. Sin embargo, hay un artículo relevante relacionado con energías renovables y agricultura que podría ser d…
- **SQL del modelo:** `SELECT a.title, a.abstract, a.year, CAST(a.cited_by AS INTEGER) AS cited_by FROM article a JOIN affiliation af ON a.sr = af.sr JOIN author au ON af.authorid = au.authorid WHERE af.country LIKE '%Germany%' AND CAST(a.year…`
- **Por qué esa nota:** Busca 'Germany' y responde que no hay ninguno (hay 4, uno sobre agrovoltaica).

### RAG puro (Q23–Q32)

#### Q23 · Nota: 5/5 (antes 1/5)
- **Pregunta:** ¿Qué estudio del corpus usa energía solar para compostar lodos de depuración y qué encontró?
- **Esperada:** Chen et al. (2014) compararon tres reactores (ordinario, de invernadero y solar) para compostar lodos municipales: el reactor solar dio calor más estable y fue el único que mantuvo más de 55 °C por más de 3 días, mejorando la calidad del compost como fertilizante.
- **Respuesta del modelo** (ruta `hybrid`): El estudio del corpus que utiliza energía solar para compostar lodos de depuración es el artículo titulado "UTILIZATION OF SOLAR ENERGY IN SEWAGE SLUDGE COMPOSTING: FERTILIZER EFFECT AND APPLICATION", publicado en 2014 en la revista WASTE MANAGE. Este estudio …
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE ts.tos LIKE '%energía solar%' AND ts.tos LIKE '%compostar lodos de depuración%' LIMIT 10;`
- **Por qué esa nota:** Correcta: Chen et al. 2014, los tres reactores y el resultado del reactor solar.

#### Q24 · Nota: 4/5 (antes 1/5)
- **Pregunta:** ¿Cómo funciona el secador de invernadero híbrido para tomates estudiado en el corpus?
- **Esperada:** Es un secador de invernadero autónomo de convección forzada que integra un sistema fotovoltaico y un colector solar; se evaluó con un modelo térmico y distintos pretratamientos del tomate (el escaldado 15 min aceleró el secado), comparado con el secado al sol.
- **Respuesta del modelo** (ruta `hybrid`): El secador de invernadero híbrido para tomates estudiado en el corpus funciona mediante la integración de un sistema solar fotovoltaico y un colector solar, lo que permite una producción energética autónoma y eficiente. Este sistema está diseñado específicamen…
- **SQL del modelo:** `SELECT title, abstract FROM article JOIN treeofscience ON article.sr = treeofscience.sr WHERE title LIKE '%secador de invernadero híbrido%' AND document_type = 'article' AND ismainarticle = 1 LIMIT 10;`
- **Por qué esa nota:** Artículo correcto (Azam) y explica el secador PV + colector; faltan los pretratamientos del tomate.

#### Q25 · Nota: 4/5 (antes 4/5)
- **Pregunta:** ¿Qué propone el estudio sobre agrovoltaica y acuaponía en azoteas urbanas?
- **Esperada:** Integrar paneles solares (8 de 500 W, unos 4.000 W) y un sistema acuapónico (peces y plantas sin suelo en circuito cerrado) en azoteas de Dhaka, Bangladesh, con recolección de agua lluvia, para producir energía y alimentos donde falta suelo.
- **Respuesta del modelo** (ruta `rag`): El estudio sobre agrovoltaica y acuaponía en azoteas urbanas, presentado en el artículo "INTEGRATED AGRIVOLTAICS AND AQUAPONIC SYSTEM FOR URBAN ROOFTOP FARMING: A CASE STUDY IN DHAKA, BANGLADESH" (2024), propone la integración de sistemas agrovoltaicos y acuap…
- **Por qué esa nota:** Artículo correcto y buena explicación; faltan detalles (8×500 W, agua lluvia).

#### Q26 · Nota: 1/5 (antes 1/5)
- **Pregunta:** ¿Qué herramienta del corpus sirve para comparar y elegir configuraciones de sistemas agrovoltaicos?
- **Esperada:** Un marco basado en simulación que combina indicadores (proporción de cultivo, energía por hectárea, rendimiento energético específico, eficiencia del agua, inversión inicial) en un análisis multicriterio, y clasifica cuatro configuraciones (vertical, monoaxial interespaciada, monoaxial elevada y biaxial elevada) según el entorno.
- **Respuesta del modelo** (ruta `rag`): No encontré artículos que respondan esta pregunta, ni entre los artículos principales del corpus ni entre sus referencias citadas.
- **Por qué esa nota:** El artículo correcto salió 1.º en la búsqueda, pero el modelo respondió NO_ENCONTRADO y terminó diciendo que no hay nada.

#### Q27 · Nota: 4/5 (antes 2/5)
- **Pregunta:** ¿Qué tratamiento se aplica al digestato de estiércol en el estudio de secado solar del corpus?
- **Esperada:** Secado solar combinado con acidificación del digestato y de su fracción sólida, para reducir el contenido de agua y las emisiones gaseosas; el digestato acidificado conservó más nitrógeno.
- **Respuesta del modelo** (ruta `hybrid`): En el estudio de secado solar del digestato de estiércol, se aplica un tratamiento de acidificación y deshidratación para producir productos fertilizantes mejorados. Este proceso es descrito en el artículo principal del corpus titulado "ACIDIFICATION AND SOLAR…
- **SQL del modelo:** `SELECT DISTINCT a.author_keywords FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE a.title LIKE '%digestato de estiércol%' AND a.title LIKE '%secado solar%';`
- **Por qué esa nota:** Correcta: acidificación + secado solar para bajar agua y emisiones; no menciona que conserva más nitrógeno.

#### Q28 · Nota: 4/5 (antes 1/5)
- **Pregunta:** ¿Qué diseña el estudio sobre el secador solar de invernadero en Filipinas?
- **Esperada:** Un sistema de control para un secador solar de invernadero, que reduce el riesgo de los trabajadores expuestos a altas temperaturas y da más flexibilidad al secado de productos agrícolas.
- **Respuesta del modelo** (ruta `rag`): El estudio sobre el secador solar de invernadero en Filipinas, según el artículo titulado "DESIGN OF A CONTROL SYSTEM FOR GREENHOUSE SOLAR DRYER" publicado en 2023 en la revista J FINANC, diseña un sistema de control para el secador solar de invernadero. Este …
- **Por qué esa nota:** Correcta: sistema de control (sensores, actuadores, PID); falta el propósito (riesgo de los trabajadores).

#### Q29 · Nota: 2/5 (antes 1/5)
- **Pregunta:** ¿Qué sistema se usó para calentar la digestión anaerobia de lodos activados excedentes?
- **Esperada:** Un sistema integrado de invernadero y calentador solar que mantuvo la temperatura de digestión mesofílica y termofílica, elevándola entre unos 10 y 28 °C según la estación y aumentando la producción de biogás.
- **Respuesta del modelo** (ruta `rag`): INTEGRATED SYSTEM OF GREENHOUSE AND SOLAR HEATER ARTÍCULO PRINCIPAL DEL CORPUS (Título: INTEGRATED SYSTEM OF GREENHOUSE AND SOLAR HEATER FOR ANAEROBIC DIGESTION OF EXCESS ACTIVATED SLUDGE, Año: N/A, Revista: )
- **Por qué esa nota:** Nombra el artículo correcto, pero la respuesta es un fragmento sin explicar cómo funciona el sistema.

#### Q30 · Nota: 3/5 (antes 2/5)
- **Pregunta:** ¿Qué estudio del corpus seca mangos con energía solar y con qué propósito?
- **Esperada:** Rankins et al. (2008): secado solar de 3,75 t de mango fresco (360 kg secos) para reducir las pérdidas poscosecha y conservar beta-caroteno frente a la deficiencia de vitamina A en África occidental francófona.
- **Respuesta del modelo** (ruta `rag`): SOLAR DRYING OF MANGOES: PRESERVATION OF AN IMPORTANT SOURCE OF VITAMIN A IN FRENCH-SPEAKING WEST AFRICA, 2008, J AM OPTOM ASSOC.
- **Por qué esa nota:** Solo da título, año y revista; el propósito (vitamina A) se deduce del título, sin más detalle.

#### Q31 · Nota: 2/5 (antes 1/5)
- **Pregunta:** ¿Qué tipo de celda solar se propone en el corpus para combinar fotovoltaica y fotosíntesis?
- **Esperada:** Una celda solar espectralmente selectiva de germanio ultradelgado, cuya transmisión se ajusta al espectro de absorción de la clorofila, para usarla en sistemas agrovoltaicos, invernaderos y fotobiorreactores.
- **Respuesta del modelo** (ruta `rag`): SPECTRALLY SELECTIVE SOLAR CELLS (SSSC)
- **Por qué esa nota:** Responde solo 'Spectrally selective solar cells'; falta que es de germanio ultradelgado y para qué sirve.

#### Q32 · Nota: 3/5 (antes 2/5)
- **Pregunta:** ¿Qué tipos de productos agrícolas se secan con energía solar en los artículos del corpus?
- **Esperada:** Entre otros: tomate (y pasta y hojuelas de tomate), cacao, mango, amla, pescado, residuos de cultivos, digestato y lodos. 26 artículos del corpus tienen 'dry' o 'drying' en el título.
- **Respuesta del modelo** (ruta `hybrid`): En los artículos del corpus, se mencionan varios tipos de productos agrícolas que se secan con energía solar. Según la fuente SQL, las palabras clave y términos asociados con estos productos incluyen "AGRICULTURAL PRODUCTS", "POTATO CHIPS", "LEMONGRASS", "COCO…
- **SQL del modelo:** `SELECT DISTINCT a.author_keywords FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE a.document_type LIKE '%Product%' AND a.title LIKE '%solar drying%' OR a.abstract LIKE '%solar drying%';`
- **Por qué esa nota:** Lista varios productos correctos (cacao, limoncillo, tomate, residuos de cultivo); faltan mango, amla y pescado.
