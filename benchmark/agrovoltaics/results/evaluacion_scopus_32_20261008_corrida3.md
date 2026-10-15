# Evaluación del agente — 32 preguntas solo Scopus, tercera corrida (2026-10-08)

- **Modelo:** `glm4:9b` vía Ollama.
- **Corrida:** `respuestas_preguntas_scopus_32_20261008_104344_glm4-9b.json`
- **Cambios respecto a la corrida 2:** (1) un juez aparte (SI/NO) decide si hay que buscar en las referencias, en vez de pedirle `NO_ENCONTRADO` al modelo en el prompt de respuesta; (2) el esquema muestra cómo están escritos los valores de texto con ejemplos reales (países en inglés y mayúsculas, autores por apellido, revistas abreviadas y su nombre completo en `journal`).
- **Puntuación:** manual, misma escala. 5 = correcta y completa · 4 = correcta con un detalle menor · 3 = parcial · 2 = mayormente incorrecta pero en la dirección correcta · 1 = incorrecta, vacía, error o inventada.

## Resumen de las tres corridas

| Bloque | Línea base (07-oct) | Corrida 2 (idioma + `a(sr)`) | Corrida 3 (juez + valores) |
|---|---|---|---|
| SQL puro (12) | 1.25 | 3.00 | 3.75 |
| Híbridas (10) | 1.10 | 1.50 | 1.30 |
| RAG puro (10) | 1.60 | 3.20 | 3.50 |
| **Total (32)** | **1.31** | **2.59** | **2.91** |

Distribución de notas en la corrida 3: 1: 11 · 2: 5 · 3: 1 · 4: 6 · 5: 9.

## Qué mejoró en esta corrida

- **Valores de texto:** Q05 (Alemania), Q07 (Acta Horticulturae) y Q08 (AIP) pasaron de 1 a 5. Q09 ya encuentra al autor por apellido.
- **Respuestas RAG completas otra vez:** Q29, Q30 y Q31 dejaron de ser fragmentos (2–3 → 3–4) al quitar la regla `NO_ENCONTRADO` del prompt de respuesta.

## Qué sigue fallando

1. **El filtro de artículos principales no es estable** (Q03, Q04, Q09, Q13–Q16, Q18): con la misma pregunta, a veces lo pone y a veces no (Q04 y Q13 acertaron en la corrida 2 y fallaron en la 3). Es ahora el error que más puntos quita. La pista en el esquema no basta para glm4; la opción robusta es que el agente consulte por defecto una vista con solo los artículos principales.
2. **Inventa cuando el SQL no encuentra nada** (Q19, Q17): presenta artículos del RAG como si respondieran la pregunta.
3. **Columnas inventadas** (Q14, Q17): `citation.cited_by` sigue apareciendo.
4. **Q26:** el artículo correcto sale 1.º en la búsqueda y el modelo igual dice que ninguno sirve.
5. **La síntesis falló una vez (Q21)** y devolvió el texto de respaldo; lo mismo pasó en Q17 de la corrida 2. Hay que registrar la excepción para ver la causa.

## Pregunta por pregunta

### SQL puro (Q01–Q12)

#### Q01 · Nota: 5/5 (línea base 4 · corrida 2 5)
- **Pregunta:** ¿Cuántos artículos principales hay en el corpus?
- **Esperada:** 66 artículos principales.
- **Respuesta del modelo** (ruta `sql`): Hay 66 artículos principales en el corpus.
- **SQL del modelo:** `SELECT COUNT(*) FROM article WHERE ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 66.

#### Q02 · Nota: 5/5 (línea base 1 · corrida 2 5)
- **Pregunta:** ¿En qué año se publicaron más artículos y cuántos?
- **Esperada:** 2024, con 13 artículos.
- **Respuesta del modelo** (ruta `sql`): En el año 2024 se publicaron más artículos, con un total de 13.
- **SQL del modelo:** `SELECT CAST(year AS INTEGER), COUNT(*) FROM article WHERE ismainarticle = 1 GROUP BY year ORDER BY COUNT(*) DESC LIMIT 1;`
- **Por qué esa nota:** Correcta: 2024 con 13.

#### Q03 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Cuántos artículos se publicaron entre 2020 y 2025?
- **Esperada:** 45 artículos.
- **Respuesta del modelo** (ruta `sql`): Entre 2020 y 2025 se publicaron un total de 507 artículos.
- **SQL del modelo:** `SELECT COUNT(DISTINCT sr) AS total_articles FROM article WHERE CAST(year AS INTEGER) BETWEEN 2020 AND 2025;`
- **Por qué esa nota:** No filtra artículos principales: 507 en vez de 45.

#### Q04 · Nota: 1/5 (línea base 1 · corrida 2 5)
- **Pregunta:** ¿Qué país aparece en más artículos y en cuántos?
- **Esperada:** China, en 17 artículos.
- **Respuesta del modelo** (ruta `sql`): El país que aparece en más artículos es Estados Unidos, con un total de 1,025 artículos.
- **SQL del modelo:** `SELECT country, COUNT(*) AS num_articles FROM article JOIN affiliation ON article.sr = affiliation.sr GROUP BY country ORDER BY num_articles DESC LIMIT 1;`
- **Por qué esa nota:** Esta vez no filtró artículos principales: responde EE. UU. con 1.025 (en la corrida anterior acertó China 17).

#### Q05 · Nota: 5/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿En cuántos artículos participa al menos una institución de Alemania?
- **Esperada:** 7 artículos.
- **Respuesta del modelo** (ruta `sql`): En total, participan en 7 artículos al menos una institución de Alemania.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) FROM article a JOIN affiliation af ON a.sr = af.sr WHERE UPPER(af.country) LIKE '%GERMANY%' AND a.ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 7. Ahora usa UPPER(country) LIKE '%GERMANY%'.

#### Q06 · Nota: 5/5 (línea base 1 · corrida 2 5)
- **Pregunta:** ¿En cuántos artículos participa al menos una institución de India?
- **Esperada:** 8 artículos.
- **Respuesta del modelo** (ruta `sql`): En total, participan al menos en 8 artículos con al menos una institución de India.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN affiliation af ON aa.authorid = af.authorid WHERE UPPER(af.country) LIKE '%INDIA%' AND a.ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 8.

#### Q07 · Nota: 5/5 (línea base 1 · corrida 2 1)
- **Pregunta:** Entre los artículos que tienen revista registrada, ¿qué revista concentra más artículos y cuántos?
- **Esperada:** Acta Horticulturae (ACTA HORTIC), con 4 artículos.
- **Respuesta del modelo** (ruta `sql`): La revista que concentra más artículos es "ACTA HORTICULTURAE" con un total de 4 artículos.
- **SQL del modelo:** `SELECT journal.journal, COUNT(article.sr) AS num_articles FROM article JOIN journal ON article.source_title = journal.source_title WHERE article.ismainarticle = 1 GROUP BY journal.journal ORDER BY COUNT(article.sr) DESC …`
- **Por qué esa nota:** Correcta: Acta Horticulturae, 4 artículos. Usó el JOIN con journal tal como indica la pista.

#### Q08 · Nota: 5/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Cuántos artículos del corpus se publicaron en AIP Conference Proceedings?
- **Esperada:** 3 artículos.
- **Respuesta del modelo** (ruta `sql`): Se publicaron 3 artículos en AIP Conference Proceedings.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) AS num_articles FROM article a WHERE UPPER(a.source_title) LIKE '%AIP CONF PROC%' AND a.ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 3 artículos en AIP CONF PROC.

#### Q09 · Nota: 2/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Cuántos artículos tiene Carsten Agert en el corpus y cuántas citas suman?
- **Esperada:** 3 artículos con 38 citas en total.
- **Respuesta del modelo** (ruta `sql`): Carsten Agert tiene 13 artículos en el corpus y acumula un total de 288 citas.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) AS num_articulos, SUM(CAST(a.cited_by AS INTEGER)) AS total_citas FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid WHERE UPPER(au.authorfullname…`
- **Por qué esa nota:** Encuentra al autor por apellido (AGERT), pero no filtra principales: 13 artículos y 288 citas en vez de 3 y 38.

#### Q10 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Cuántos artículos tiene Jason A. Carlyon en el corpus y cuántas citas suman?
- **Esperada:** 2 artículos con 26 citas en total.
- **Respuesta del modelo** (ruta `sql`): Jason A. Carlyon no tiene artículos en el corpus, y la suma de citas es None.
- **SQL del modelo:** `SELECT COUNT(DISTINCT a.sr) AS num_articles, SUM(CAST(a.cited_by AS INTEGER)) AS total_citations FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid WHERE UPPER(au.authorfulln…`
- **Por qué esa nota:** Busca '%CARLYON JASON A.%' y la BD guarda 'JASON A. CARLYON': no buscó solo por apellido.

#### Q11 · Nota: 5/5 (línea base 1 · corrida 2 5)
- **Pregunta:** ¿Qué autores tienen 3 o más artículos en el corpus?
- **Esperada:** 5 autores, todos con 3 artículos: Carsten Agert, Kai Gehrke, Martin Vehse, Nils Neugebohrn y Norbert Osterthun.
- **Respuesta del modelo** (ruta `sql`): Los autores con 3 o más artículos en el corpus son: 1. C., AGERT, CARSTEN con 3 artículos. 2. K., GEHRKE, KAI con 3 artículos. 3. M., VEHSE, MARTIN con 3 artículos. 4. N., NEUGEBOHRN, NILS con 3 artículos. 5. N., OSTERTHUN, NORBERT con 3 artículos.
- **SQL del modelo:** `SELECT a.authorname, COUNT(DISTINCT aa.sr) AS num_articles FROM author a JOIN articleauthor aa ON a.authorid = aa.authorid WHERE aa.sr IN (SELECT sr FROM article WHERE ismainarticle = 1) GROUP BY a.authorname HAVING COUN…`
- **Por qué esa nota:** Correcta: los 5 autores con 3 artículos.

#### Q12 · Nota: 5/5 (línea base 1 · corrida 2 5)
- **Pregunta:** ¿Cuántas citas suman los artículos publicados en 2014?
- **Esperada:** 78 citas.
- **Respuesta del modelo** (ruta `sql`): Los artículos publicados en 2014 suman un total de 78 citas.
- **SQL del modelo:** `SELECT SUM(CAST(cited_by AS INTEGER)) AS total_citations FROM article WHERE CAST(year AS INTEGER) = 2014 AND ismainarticle = 1;`
- **Por qué esa nota:** Correcta: 78 citas.

### Híbridas (Q13–Q22)

#### Q13 · Nota: 1/5 (línea base 1 · corrida 2 4)
- **Pregunta:** ¿Cuál es el artículo más citado del corpus y de qué trata?
- **Esperada:** «Powering agriculture: present status, future potential, and challenges of renewable energy applications» (Rahman et al., 2022, Renewable Energy), con 165 citas. Revisa el uso de energías renovables en la agricultura para reducir la dependencia de combustibles fósiles (secado de grano, fertilizantes, maquinaria, electricidad) y sus emisiones.
- **Respuesta del modelo** (ruta `sql`): El artículo más citado del corpus es "Analysis of Relative Gene Expression Data Using Real-Time Quantitative PCR and the 2−ΔΔCT Method", que no tiene un resumen disponible.
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE sr = ( SELECT sr FROM article ORDER BY CAST(cited_by AS INTEGER) DESC LIMIT 1 );`
- **Por qué esa nota:** Esta vez no filtró principales: devuelve un artículo de biología molecular (en la corrida anterior acertó Rahman).

#### Q14 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Cuál fue el artículo más citado publicado en 2014 y qué estudió?
- **Esperada:** Chen et al. (2014, Waste Management), con 59 citas: uso de energía solar en el compostaje de lodos de depuración; comparó reactores ordinario, de invernadero y solar, y el solar dio calor más estable (más de 55 °C durante más de 3 días).
- **Respuesta del modelo** (ruta `sql`): El artículo más citado publicado en 2014 fue "MODERATED ESTIMATION OF FOLD CHANGE AND DISPERSION FOR RNA-SEQ DATA WITH DESEQ2", que estudió la análisis de datos de cuenta en técnicas de secuenciación de alta throughput, utilizando el método DESeq2 para la dife…
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE year = CAST('2014' AS INTEGER) ORDER BY CAST(cited_by AS INTEGER) DESC LIMIT 1;`
- **Por qué esa nota:** No filtra principales: devuelve DESeq2 (bioinformática).

#### Q15 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Cuál fue el artículo más citado publicado en 2015 y de qué trata?
- **Esperada:** Fasahati et al. (2015, Energy), con 38 citas: impacto económico, energético y ambiental de la tecnología de deshidratación de alcohol en la producción de biocombustible a partir de algas pardas.
- **Respuesta del modelo** (ruta `hybrid`): El artículo más citado publicado en 2015 fue "HISAT: A FAST SPLICED ALIGNER WITH LOW MEMORY REQUIREMENTS". Este artículo se enfoca en el desarrollo de un alineador spliced rápido con bajas necesidades de memoria, lo que es relevante para la bioinformática y la…
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE year = CAST('2015' AS INTEGER) ORDER BY CAST(cited_by AS INTEGER) DESC LIMIT 1;`
- **Por qué esa nota:** No filtra principales: devuelve HISAT.

#### Q16 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** Entre los artículos con 'photovoltaic', 'agrivoltaic' o 'PV' en el título, ¿cuál es el más citado y qué sistema analiza?
- **Esperada:** Azam et al. (2020, Energy), con 69 citas: un secador de invernadero híbrido para tomates que integra un sistema fotovoltaico y un colector solar.
- **Respuesta del modelo** (ruta `hybrid`): El artículo más citado entre aquellos con 'photovoltaic', 'agrivoltaic' o 'PV' en el título es "PHOTOVOLTAIC DEGRADATION RATES—AN ANALYTICAL REVIEW", que ha sido citado 1267 veces. Este sistema analiza la degradación de las celdas fotovoltaicas, lo cual es rel…
- **SQL del modelo:** `SELECT a.title, a.cited_by FROM article a WHERE UPPER(a.title) LIKE '%PHOTOVOLTAIC%' OR UPPER(a.title) LIKE '%AGRIVOLTAIC%' OR UPPER(a.title) LIKE '%PV%' ORDER BY CAST(a.cited_by AS INTEGER) DESC LIMIT 1;`
- **Por qué esa nota:** No filtra principales: devuelve una revisión de degradación fotovoltaica (1.267 citas), que es referencia.

#### Q17 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Cuáles fueron los artículos más citados publicados entre 2007 y 2012 y de qué tratan?
- **Esperada:** Dos artículos con 13 citas cada uno: Meng et al. (2009), un sistema integrado de invernadero y calentador solar para la digestión anaerobia de lodos activados; y Rankins et al. (2008), el secado solar de mangos para conservar la provitamina A en África occidental francófona.
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron artículos específicos publicados entre 2007 y 2012 con un alto número de citas según la consulta SQL. Sin embargo, de acuerdo con los artículos recuperados por búsqueda semántica, aquí hay información sobre algunos artículos que pueden ser re…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN citation c ON a.sr = c.sr_ref WHERE CAST(a.year AS INTEGER) BETWEEN 2007 AND 2012 ORDER BY CAST(c.cited_by AS INTEGER) DESC LIMIT 10;`
- **Por qué esa nota:** Inventa citation.cited_by; luego describe artículos del RAG que no son de 2007–2012.

#### Q18 · Nota: 2/5 (línea base 2 · corrida 2 2)
- **Pregunta:** ¿Qué artículos tienen autores de Bangladesh y de qué tratan?
- **Esperada:** 3 artículos: Rahman et al. (2022), revisión de energías renovables en agricultura (165 citas); Rana et al. (2023), acuicultura marina y un secador de pescado inteligente basado en IoT; y Rony et al. (2024), agrovoltaica más acuaponía en azoteas urbanas de Dhaka.
- **Respuesta del modelo** (ruta `hybrid`): Los artículos con autores de Bangladesh que se encontraron en la consulta SQL son los siguientes: 1. **Título:** EXPERIMENTAL INVESTIGATION ON SOLAR DRYING OF FISH USING SOLAR TUNNEL DRYER **Abstract:** Este artículo presenta el rendimiento del secador solar d…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid JOIN affiliation af ON au.authorid = af.authorid WHERE UPPER(af.country) LIKE '%BANGLADESH%' LIM…`
- **Por qué esa nota:** Sin filtro de principales: lista artículos de Bangladesh que no son los 3 del corpus; el RAG sí trajo a Rony 2024.

#### Q19 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Qué artículos publicó el grupo de Carsten Agert y de qué tratan?
- **Esperada:** 3 artículos (Osterthun et al., 2021–2022), todos sobre celdas solares espectralmente selectivas que combinan fotovoltaica y fotosíntesis: celdas ultradelgadas de germanio (30 citas), su efecto en el crecimiento de microalgas en fotobiorreactores (8 citas) y su desempeño con datos PV-GIS (0 citas).
- **Respuesta del modelo** (ruta `hybrid`): El grupo de Carsten Agert ha publicado varios artículos en diferentes áreas temáticas. Según la búsqueda semántica, aquí se presentan algunos detalles sobre sus publicaciones: 1. **Artículo Principal del Corpus (similitud: 0.5524)**: - **Título**: "THE OBLIGAT…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid JOIN affiliation af ON a.sr = af.sr WHERE UPPER(au.authorfullname) LIKE '%CARSTEN AGERT%' AND af…`
- **Por qué esa nota:** Afirma que el grupo de Agert publicó artículos y describe los de Anaplasma (del RAG): inventa.

#### Q20 · Nota: 2/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Qué artículos publicó Jason A. Carlyon y tienen relación con los agrovoltaicos?
- **Esperada:** 2 artículos sobre la bacteria Anaplasma phagocytophilum (Read et al., 2022, 16 citas; Oki et al., 2015, 10 citas). Son de microbiología y no tienen relación con los agrovoltaicos.
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron artículos publicados por Jason A. Carlyon que tengan relación directa con los agrovoltaicos según la consulta SQL y los resultados de búsqueda semántica proporcionados. La consulta SQL no devolvió ningún resultado, lo que indica que no hay ar…
- **SQL del modelo:** `SELECT a.title, a.abstract, a.year, CAST(a.cited_by AS INTEGER), a.author_keywords, a.doi, a.document_type, a.source_title FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid …`
- **Por qué esa nota:** Concluye bien que Carlyon no tiene trabajos sobre agrovoltaicos, pero dice que no tiene artículos (tiene 2 sobre Anaplasma).

#### Q21 · Nota: 2/5 (línea base 1 · corrida 2 2)
- **Pregunta:** ¿Qué artículos publicó Acta Horticulturae en el corpus y de qué tratan?
- **Esperada:** 4 artículos: arreglos fotovoltaicos sobre un huerto de perales (Singh R., 2024); pepino con solución nutritiva oxigenada en invernaderos (Singh P., 2021); temperatura y humedad en un invernadero plástico asimétrico (Hu, 2018); estrategias pre y poscosecha para compuestos bioactivos (Gil, 2015).
- **Respuesta del modelo** (ruta `hybrid`): Se encontraron 10 resultados. Columnas: title, abstract. Primer resultado: {'title': 'EFFECTS OF ABOVE-CANOPY PHOTOVOLTAIC ARRAYS ON TRANSPIRATION AND ENERGY PRODUCTION IN A PEAR ORCHARD', 'abstract': 'AGRIVOLTAICS IS A NEW APPROACH TO INTEGRATE PHOTOVOLTAIC A…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid JOIN affiliation af ON au.authorid = af.authorid WHERE UPPER(a.source_title) LIKE '%ACTA HORTIC%…`
- **Por qué esa nota:** El SQL encontró los artículos correctos de Acta Horticulturae, pero la síntesis falló y devolvió el texto de respaldo con solo el primero.

#### Q22 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Qué artículos con participación de Alemania se publicaron desde 2022 y cuáles tratan sobre agrovoltaicos?
- **Esperada:** 4 artículos. Solo uno trata de agrovoltaica: el desempeño de una celda solar espectralmente selectiva con datos PV-GIS (Osterthun, 2022). Los otros tratan de producción agrícola resiliente y climáticamente neutra (Uhl, 2023), manejo de lodos fecales en asentamientos de desplazados (Orugba, 2024) y producción de metanol renovable (Svitnič, 2024).
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron artículos específicos con participación de Alemania que traten sobre agrovoltaicos publicados desde 2022, según la consulta SQL. Sin embargo, uno de los artículos recuperados por búsqueda semántica, titulado "POWERING AGRICULTURE: PRESENT STA…
- **SQL del modelo:** `SELECT a.title, a.doi FROM article a JOIN affiliation af ON a.sr = af.sr WHERE UPPER(af.country) LIKE '%GERMANY%' AND CAST(a.year AS INTEGER) >= 2022 AND UPPER(a.author_keywords) LIKE '%AGROVOLTAICOS%' ORDER BY cited_by …`
- **Por qué esa nota:** Exige la keyword 'AGROVOLTAICOS' (en español) y responde que no hay ninguno (hay 4).

### RAG puro (Q23–Q32)

#### Q23 · Nota: 5/5 (línea base 1 · corrida 2 5)
- **Pregunta:** ¿Qué estudio del corpus usa energía solar para compostar lodos de depuración y qué encontró?
- **Esperada:** Chen et al. (2014) compararon tres reactores (ordinario, de invernadero y solar) para compostar lodos municipales: el reactor solar dio calor más estable y fue el único que mantuvo más de 55 °C por más de 3 días, mejorando la calidad del compost como fertilizante.
- **Respuesta del modelo** (ruta `hybrid`): El estudio del corpus que utiliza energía solar para compostar lodos de depuración es el artículo titulado "UTILIZATION OF SOLAR ENERGY IN SEWAGE SLUDGE COMPOSTING: FERTILIZER EFFECT AND APPLICATION", publicado en 2014 en la revista WASTE MANAGE. Este estudio …
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE UPPER(ts.tos) LIKE '%ENERGY SOLAR%' AND UPPER(a.title) LIKE '%COMPOSTING SEWAGE SLUDGE%' LIMIT 10;`
- **Por qué esa nota:** Correcta: Chen et al. 2014 y los tres reactores.

#### Q24 · Nota: 4/5 (línea base 1 · corrida 2 4)
- **Pregunta:** ¿Cómo funciona el secador de invernadero híbrido para tomates estudiado en el corpus?
- **Esperada:** Es un secador de invernadero autónomo de convección forzada que integra un sistema fotovoltaico y un colector solar; se evaluó con un modelo térmico y distintos pretratamientos del tomate (el escaldado 15 min aceleró el secado), comparado con el secado al sol.
- **Respuesta del modelo** (ruta `hybrid`): El secador de invernadero híbrido para tomates estudiado en el corpus es una tecnología innovadora que combina sistemas solares y fotovoltaicos con un secador de invernadero. Este sistema tiene como objetivo mejorar la eficiencia energética y reducir costos en…
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE UPPER(title) LIKE '%SECADOR DE INVERNADERO HIBRIDO%' AND UPPER(title) LIKE '%TOMATES%' LIMIT 10;`
- **Por qué esa nota:** Artículo correcto (Azam) y explica el secador PV + colector; faltan los pretratamientos.

#### Q25 · Nota: 4/5 (línea base 4 · corrida 2 4)
- **Pregunta:** ¿Qué propone el estudio sobre agrovoltaica y acuaponía en azoteas urbanas?
- **Esperada:** Integrar paneles solares (8 de 500 W, unos 4.000 W) y un sistema acuapónico (peces y plantas sin suelo en circuito cerrado) en azoteas de Dhaka, Bangladesh, con recolección de agua lluvia, para producir energía y alimentos donde falta suelo.
- **Respuesta del modelo** (ruta `rag`): El estudio titulado "INTEGRATED AGRIVOLTAICS AND AQUAPONIC SYSTEM FOR URBAN ROOFTOP FARMING: A CASE STUDY IN DHAKA, BANGLADESH" (2024), publicado en la revista J FINANC, propone una solución innovadora para las ciudades densamente pobladas como Dhaka, donde la…
- **Por qué esa nota:** Artículo correcto y buena explicación; faltan detalles (8×500 W, agua lluvia).

#### Q26 · Nota: 1/5 (línea base 1 · corrida 2 1)
- **Pregunta:** ¿Qué herramienta del corpus sirve para comparar y elegir configuraciones de sistemas agrovoltaicos?
- **Esperada:** Un marco basado en simulación que combina indicadores (proporción de cultivo, energía por hectárea, rendimiento energético específico, eficiencia del agua, inversión inicial) en un análisis multicriterio, y clasifica cuatro configuraciones (vertical, monoaxial interespaciada, monoaxial elevada y biaxial elevada) según el entorno.
- **Respuesta del modelo** (ruta `rag`): No se encontró información específica sobre una herramienta del corpus que sirva para comparar y elegir configuraciones de sistemas agrovoltaicos en los artículos proporcionados. Los artículos presentan temas variados relacionados con agricultura, pero no menc…
- **Por qué esa nota:** El artículo correcto salió 1.º en la búsqueda, pero el modelo responde que ninguno habla de una herramienta.

#### Q27 · Nota: 4/5 (línea base 2 · corrida 2 4)
- **Pregunta:** ¿Qué tratamiento se aplica al digestato de estiércol en el estudio de secado solar del corpus?
- **Esperada:** Secado solar combinado con acidificación del digestato y de su fracción sólida, para reducir el contenido de agua y las emisiones gaseosas; el digestato acidificado conservó más nitrógeno.
- **Respuesta del modelo** (ruta `hybrid`): En el estudio de secado solar del digestato de estiércol, se aplica un tratamiento de acidificación y secado solar para producir fertilizantes mejorados. Según el artículo principal del corpus titulado "ACIDIFICATION AND SOLAR DRYING OF MANURE-BASED DIGESTATE …
- **SQL del modelo:** `SELECT DISTINCT a.title, a.author_keywords FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE UPPER(a.title) LIKE '%DIGESTATO DE ESTIÉRCOL%' AND UPPER(ts.author_keywords) LIKE '%SECADO SOLAR%';`
- **Por qué esa nota:** Correcta: acidificación + secado solar para bajar agua y emisiones.

#### Q28 · Nota: 4/5 (línea base 1 · corrida 2 4)
- **Pregunta:** ¿Qué diseña el estudio sobre el secador solar de invernadero en Filipinas?
- **Esperada:** Un sistema de control para un secador solar de invernadero, que reduce el riesgo de los trabajadores expuestos a altas temperaturas y da más flexibilidad al secado de productos agrícolas.
- **Respuesta del modelo** (ruta `rag`): El estudio sobre el secador solar de invernadero en Filipinas, presentado en el artículo "DESIGN OF A CONTROL SYSTEM FOR GREENHOUSE SOLAR DRYER" (2023), diseña un sistema de control para el secador solar de invernadero. Este sistema incluye componentes como se…
- **Por qué esa nota:** Correcta: sistema de control con sensores, actuadores y PID; falta el propósito.

#### Q29 · Nota: 3/5 (línea base 1 · corrida 2 2)
- **Pregunta:** ¿Qué sistema se usó para calentar la digestión anaerobia de lodos activados excedentes?
- **Esperada:** Un sistema integrado de invernadero y calentador solar que mantuvo la temperatura de digestión mesofílica y termofílica, elevándola entre unos 10 y 28 °C según la estación y aumentando la producción de biogás.
- **Respuesta del modelo** (ruta `rag`): Se utilizó un sistema de calentamiento solar para la digestión anaerobia de lodos activados excedentes. Este sistema se integró con una invernadero y un calentador solar, como se describe en el artículo "INTEGRATED SYSTEM OF GREENHOUSE AND SOLAR HEATER FOR ANA…
- **Por qué esa nota:** Identifica el sistema integrado de invernadero y calentador solar; no explica cómo mejoró la temperatura.

#### Q30 · Nota: 4/5 (línea base 2 · corrida 2 3)
- **Pregunta:** ¿Qué estudio del corpus seca mangos con energía solar y con qué propósito?
- **Esperada:** Rankins et al. (2008): secado solar de 3,75 t de mango fresco (360 kg secos) para reducir las pérdidas poscosecha y conservar beta-caroteno frente a la deficiencia de vitamina A en África occidental francófona.
- **Respuesta del modelo** (ruta `rag`): El estudio del corpus seca mangos con energía solar con el propósito de preservar una importante fuente de vitamina A en la región de África Occidental de habla francesa. Este método ayuda a reducir las pérdidas postcosecha y combatir la deficiencia de vitamin…
- **Por qué esa nota:** Correcta: vitamina A, pérdidas poscosecha, niños menores de 5 años; faltan las cantidades.

#### Q31 · Nota: 4/5 (línea base 1 · corrida 2 2)
- **Pregunta:** ¿Qué tipo de celda solar se propone en el corpus para combinar fotovoltaica y fotosíntesis?
- **Esperada:** Una celda solar espectralmente selectiva de germanio ultradelgado, cuya transmisión se ajusta al espectro de absorción de la clorofila, para usarla en sistemas agrovoltaicos, invernaderos y fotobiorreactores.
- **Respuesta del modelo** (ruta `rag`): En el corpus, se propone el uso de celdas solares espectralmente selectivas para combinar fotovoltaica y fotosíntesis. Esto se destaca en los siguientes artículos: 1. **SPECTRAL ENGINEERING OF ULTRATHIN GERMANIUM SOLAR CELLS FOR COMBINED PHOTOVOLTAIC AND PHOTO…
- **Por qué esa nota:** Correcta: celdas espectralmente selectivas de germanio ultradelgado para PV + fotosíntesis.

#### Q32 · Nota: 2/5 (línea base 2 · corrida 2 3)
- **Pregunta:** ¿Qué tipos de productos agrícolas se secan con energía solar en los artículos del corpus?
- **Esperada:** Entre otros: tomate (y pasta y hojuelas de tomate), cacao, mango, amla, pescado, residuos de cultivos, digestato y lodos. 26 artículos del corpus tienen 'dry' o 'drying' en el título.
- **Respuesta del modelo** (ruta `hybrid`): En los artículos del corpus, se mencionan varios tipos de productos agrícolas que se secan con energía solar. Según el artículo principal titulado "COMPARATIVE STUDY OF SOLAR DRYING OF COCOA BEANS: TWO METHODS USED IN COLOMBIAN RURAL AREAS", se seca cocoa bean…
- **SQL del modelo:** `SELECT DISTINCT a.author_keywords FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE UPPER(ts.tos) LIKE '%SOLAR DRYING%' AND a.ismainarticle = 1 ORDER BY a.author_keywords DESC LIMIT 10;`
- **Por qué esa nota:** Solo menciona cacao y granos; faltan tomate, mango, amla, pescado, residuos.
