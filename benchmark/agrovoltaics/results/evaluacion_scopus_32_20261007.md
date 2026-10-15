# Evaluación del agente — 32 preguntas solo Scopus (agrovoltaicos)

- **Modelo:** `glm4:9b` vía Ollama, agente sin cambios (prompts originales).
- **Corrida:** 2026-10-07 · `respuestas_preguntas_scopus_32_20261007_084249_glm4-9b.json`
- **Dataset:** `preguntas_scopus_32` (respuestas esperadas sacadas solo del corpus Scopus).
- **Puntuación:** la puse yo leyendo cada respuesta. 5 = correcta y completa · 4 = correcta con un detalle menor · 3 = parcial · 2 = mayormente incorrecta pero en la dirección correcta · 1 = incorrecta, vacía, error o inventada.

## Resumen

| Bloque | Preguntas | Nota media (1–5) |
|---|---|---|
| SQL puro | 12 | 1.25 |
| Híbridas | 10 | 1.10 |
| RAG puro | 10 | 1.60 |
| **Total** | **32** | **1.31** |

Distribución de notas: 1: 26 · 2: 4 · 3: 0 · 4: 2 · 5: 0.

Solo dos respuestas son buenas (Q01 y Q25, nota 4). El resto falla por pocas causas que se repiten, y casi todas vienen de los datos o de cómo se le presenta el esquema al modelo, no del enrutamiento.

## Por qué falla (ordenado por cuántas preguntas afecta)

1. **No filtra los artículos del corpus (`ismainarticle = 1`).** La tabla `Article` tiene 1.766 filas: 66 artículos del corpus y 1.700 referencias citadas. El modelo cuenta y ordena sobre todo, así que aparecen referencias de bioinformática con miles de citas. Afecta a Q02–Q04, Q11–Q16 y Q18.
2. **El índice RAG está lleno de referencias.** ChromaDB tiene 1.624 documentos y solo 66 son del corpus. Dos referencias en español casi sin resumen («Desarrollo de un modelo matemático para el biosecado…», con 32 caracteres de abstract, y «Determinación del contenido de humedad…») salen en casi todas las búsquedas y desplazan a los artículos correctos. Solo Q25 recuperó el artículo esperado.
3. **Los valores no se escriben como en la BD.** Autores (`AGERT C.`, `CARLYON J.A.`), revistas abreviadas (`AIP CONF PROC`) y países en mayúsculas (`GERMANY`). El modelo busca «Carsten Agert», «AIP Conference Proceedings» o «Germany» y no encuentra nada. Afecta a Q05, Q08, Q10, Q19, Q20 y Q22.
4. **SQL inválido o con columnas inventadas.** Escribe `a(sr)` en vez de `a.sr` (Q05, Q06), une columnas que no se corresponden (Q07) o inventa columnas y tablas (Q09, Q17, Q21, Q23).
5. **Inventa cuando el SQL falla.** En Q19 y Q21 presenta artículos que trajo el RAG como si fueran del autor o de la revista pedida. Es el fallo más grave para una tesis, porque la respuesta parece confiable.
6. **Enrutamiento.** 4 de las 10 preguntas RAG se fueron a `hybrid` (Q23, Q24, Q27, Q32) y generaron SQL con palabras en español que no existen en la BD. Las SQL e híbridas sí se enrutaron razonablemente.

## Pregunta por pregunta

### SQL puro (Q01–Q12)

#### Q01 · Nota: 4/5
- **Pregunta:** ¿Cuántos artículos principales hay en el corpus?
- **Esperada:** 66 artículos principales.
- **Respuesta del modelo** (ruta `sql`): Hay 65 artículos principales en el corpus.
- **SQL del modelo:** `SELECT COUNT(DISTINCT sr) FROM article WHERE ismainarticle = '1' LIMIT 10;`
- **Por qué esa nota:** Da 65 en vez de 66: usó COUNT(DISTINCT sr) y dos artículos distintos comparten SR. El filtro de artículos principales sí está.

#### Q02 · Nota: 1/5
- **Pregunta:** ¿En qué año se publicaron más artículos y cuántos?
- **Esperada:** 2024, con 13 artículos.
- **Respuesta del modelo** (ruta `sql`): En el año 2021 se publicaron más artículos, con un total de 155.
- **SQL del modelo:** `SELECT year, COUNT(*) AS num_articles FROM article GROUP BY CAST(year AS INTEGER) ORDER BY num_articles DESC LIMIT 1;`
- **Por qué esa nota:** No filtra artículos principales: cuenta también las 1.700 referencias (2021, 155).

#### Q03 · Nota: 1/5
- **Pregunta:** ¿Cuántos artículos se publicaron entre 2020 y 2025?
- **Esperada:** 45 artículos.
- **Respuesta del modelo** (ruta `sql`): Entre 2020 y 2025 se publicaron un total de 507 artículos.
- **SQL del modelo:** `SELECT COUNT(DISTINCT sr) AS total_articles FROM article WHERE CAST(year AS INTEGER) BETWEEN 2020 AND 2025;`
- **Por qué esa nota:** Mismo error: cuenta referencias (507 en vez de 45).

#### Q04 · Nota: 1/5
- **Pregunta:** ¿Qué país aparece en más artículos y en cuántos?
- **Esperada:** China, en 17 artículos.
- **Respuesta del modelo** (ruta `sql`): El país que aparece en más artículos es Estados Unidos, con un total de 269 artículos.
- **SQL del modelo:** `SELECT country, COUNT(DISTINCT a.sr) AS num_articles FROM article a JOIN affiliation af ON a.sr = af.sr GROUP BY country ORDER BY num_articles DESC LIMIT 1;`
- **Por qué esa nota:** Sin filtro de artículos principales: responde EE. UU. con 269.

#### Q05 · Nota: 1/5
- **Pregunta:** ¿En cuántos artículos participa al menos una institución de Alemania?
- **Esperada:** 7 artículos.
- **Respuesta del modelo** (ruta `sql`): Lo siento, no pude obtener los resultados. Hubo un error al consultar la base de datos: Error SQLite: ambiguous column name: sr
- **SQL del modelo:** `SELECT COUNT(DISTINCT a(sr)) FROM article a JOIN affiliation af ON a(sr) = af(sr) JOIN author au ON af.authorid = au.authorid WHERE af.country = 'Germany' AND a(sr) IN (SELECT sr FROM citation WHERE type = 'author');`
- **Por qué esa nota:** SQL inválido (escribe a(sr) en vez de a.sr) y además busca 'Germany' en minúscula.

#### Q06 · Nota: 1/5
- **Pregunta:** ¿En cuántos artículos participa al menos una institución de India?
- **Esperada:** 8 artículos.
- **Respuesta del modelo** (ruta `sql`): Lo siento, no pude obtener los resultados. Hubo un error al consultar la base de datos: Error SQLite: ambiguous column name: sr
- **SQL del modelo:** `SELECT COUNT(DISTINCT a(sr)) FROM article a JOIN affiliation af ON a(sr) = af(sr) WHERE CAST(af.country AS TEXT) LIKE '%India%' AND af.authorid IS NOT NULL;`
- **Por qué esa nota:** SQL inválido (a(sr)).

#### Q07 · Nota: 1/5
- **Pregunta:** Entre los artículos que tienen revista registrada, ¿qué revista concentra más artículos y cuántos?
- **Esperada:** Acta Horticulturae (ACTA HORTIC), con 4 artículos.
- **Respuesta del modelo** (ruta `sql`): La consulta no retornó resultados. Esto puede significar que no hay datos que coincidan con los criterios de búsqueda en el corpus.
- **SQL del modelo:** `SELECT journal.source_title, COUNT(article.sr) AS num_articles FROM article JOIN journal ON article.source_title = journal.journal_id WHERE article.source_title IS NOT NULL GROUP BY journal.source_title ORDER BY num_arti…`
- **Por qué esa nota:** Une source_title con journal_id (columnas que no se corresponden): sin resultados.

#### Q08 · Nota: 1/5
- **Pregunta:** ¿Cuántos artículos del corpus se publicaron en AIP Conference Proceedings?
- **Esperada:** 3 artículos.
- **Respuesta del modelo** (ruta `sql`): No se encontraron artículos del corpus publicados en AIP Conference Proceedings.
- **SQL del modelo:** `SELECT COUNT(DISTINCT sr) FROM article WHERE source_title LIKE '%AIP Conference Proceedings%';`
- **Por qué esa nota:** Busca 'AIP Conference Proceedings', pero la BD guarda la abreviatura 'AIP CONF PROC': responde 0.

#### Q09 · Nota: 1/5
- **Pregunta:** ¿Cuántos artículos tiene Carsten Agert en el corpus y cuántas citas suman?
- **Esperada:** 3 artículos con 38 citas en total.
- **Respuesta del modelo** (ruta `sql`): Lo siento, no pude obtener los resultados. Hubo un error al consultar la base de datos: Error SQLite: no such column: c.cited_by
- **SQL del modelo:** `SELECT COUNT(DISTINCT aa.sr) AS num_articles, SUM(CAST(c.cited_by AS INTEGER)) AS total_citations FROM articleauthor aa JOIN article a ON aa.sr = a.sr JOIN author au ON aa.authorid = au.authorid JOIN citation c ON a.sr =…`
- **Por qué esa nota:** Inventa la columna citation.cited_by: error SQL.

#### Q10 · Nota: 1/5
- **Pregunta:** ¿Cuántos artículos tiene Jason A. Carlyon en el corpus y cuántas citas suman?
- **Esperada:** 2 artículos con 26 citas en total.
- **Respuesta del modelo** (ruta `sql`): Jason A. Carlyon no tiene artículos en el corpus ni citas asociadas.
- **SQL del modelo:** `SELECT COUNT(DISTINCT aa.sr) AS num_articles, SUM(CAST(a.cited_by AS INTEGER)) AS total_citations FROM articleauthor aa JOIN article a ON aa.sr = a.sr JOIN author au ON aa.authorid = au.authorid WHERE au.authorname LIKE …`
- **Por qué esa nota:** Busca 'Jason A. Carlyon', pero la BD guarda 'CARLYON J.A.': dice que no tiene artículos.

#### Q11 · Nota: 1/5
- **Pregunta:** ¿Qué autores tienen 3 o más artículos en el corpus?
- **Esperada:** 5 autores, todos con 3 artículos: Carsten Agert, Kai Gehrke, Martin Vehse, Nils Neugebohrn y Norbert Osterthun.
- **Respuesta del modelo** (ruta `sql`): 1. ABAM F.I. 2. AGERT C. 3. AHMAD A. 4. AHMADI M.H. 5. AKPINAR E.K. 6. AMADUCCI S. 7. AMAR M. 8. ARORA V.K. 9. AYESSOU N.C. 10. AYYAPPAN S.
- **SQL del modelo:** `SELECT a.authorname, COUNT(DISTINCT aa.sr) AS articles_count FROM author a JOIN articleauthor aa ON a.authorid = aa.authorid GROUP BY a.authorname HAVING COUNT(DISTINCT aa.sr) >= 3 LIMIT 10;`
- **Por qué esa nota:** Sin filtro y con LIMIT 10: lista 10 autores cualquiera de la tabla completa (Agert aparece con 12).

#### Q12 · Nota: 1/5
- **Pregunta:** ¿Cuántas citas suman los artículos publicados en 2014?
- **Esperada:** 78 citas.
- **Respuesta del modelo** (ruta `sql`): Los artículos publicados en 2014 suman 75 citas.
- **SQL del modelo:** `SELECT COUNT(CAST(cited_by AS INTEGER)) FROM article WHERE CAST(year AS INTEGER) = 2014;`
- **Por qué esa nota:** Usa COUNT en vez de SUM y no filtra: 75 en vez de 78 citas.

### Híbridas (Q13–Q22)

#### Q13 · Nota: 1/5
- **Pregunta:** ¿Cuál es el artículo más citado del corpus y de qué trata?
- **Esperada:** «Powering agriculture: present status, future potential, and challenges of renewable energy applications» (Rahman et al., 2022, Renewable Energy), con 165 citas. Revisa el uso de energías renovables en la agricultura para reducir la dependencia de combustibles fósiles (secado de grano, fertilizantes, maquinaria, electricidad) y sus emisiones.
- **Respuesta del modelo** (ruta `sql`): El artículo más citado del corpus se titula "Analysis of Relative Gene Expression Data Using Real-Time Quantitative PCR and the 2−ΔΔCT Method" y ha sido citado 164,905 veces. No hay un resumen disponible para este artículo.
- **SQL del modelo:** `SELECT title, abstract, CAST(cited_by AS INTEGER) AS citations_count FROM article ORDER BY cited_by DESC LIMIT 1;`
- **Por qué esa nota:** Sin filtro: devuelve una referencia de biología molecular (164.905 citas) que no es del corpus.

#### Q14 · Nota: 1/5
- **Pregunta:** ¿Cuál fue el artículo más citado publicado en 2014 y qué estudió?
- **Esperada:** Chen et al. (2014, Waste Management), con 59 citas: uso de energía solar en el compostaje de lodos de depuración; comparó reactores ordinario, de invernadero y solar, y el solar dio calor más estable (más de 55 °C durante más de 3 días).
- **Respuesta del modelo** (ruta `sql`): El artículo más citado publicado en 2014 fue "MODERATED ESTIMATION OF FOLD CHANGE AND DISPERSION FOR RNA-SEQ DATA WITH DESEQ2", que estudió el análisis de datos de conteo en ensayos de secuenciación de alto rendimiento, utilizando la metodología DESeq2 para me…
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE year = CAST('2014' AS INTEGER) ORDER BY CAST(cited_by AS INTEGER) DESC LIMIT 1;`
- **Por qué esa nota:** Sin filtro: devuelve DESeq2 (bioinformática), no Chen et al.

#### Q15 · Nota: 1/5
- **Pregunta:** ¿Cuál fue el artículo más citado publicado en 2015 y de qué trata?
- **Esperada:** Fasahati et al. (2015, Energy), con 38 citas: impacto económico, energético y ambiental de la tecnología de deshidratación de alcohol en la producción de biocombustible a partir de algas pardas.
- **Respuesta del modelo** (ruta `hybrid`): El artículo más citado publicado en 2015 es "HISAT: A FAST SPLICED ALIGNER WITH LOW MEMORY REQUIREMENTS". Este artículo se enfoca en el desarrollo de un alineador espaciado rápido con bajas necesidades de memoria, lo cual es relevante para la bioinformática y …
- **SQL del modelo:** `SELECT title, abstract FROM article WHERE year = CAST('2015' AS INTEGER) ORDER BY CAST(cited_by AS INTEGER) DESC LIMIT 1;`
- **Por qué esa nota:** Sin filtro: devuelve HISAT (bioinformática), no Fasahati et al.

#### Q16 · Nota: 1/5
- **Pregunta:** Entre los artículos con 'photovoltaic', 'agrivoltaic' o 'PV' en el título, ¿cuál es el más citado y qué sistema analiza?
- **Esperada:** Azam et al. (2020, Energy), con 69 citas: un secador de invernadero híbrido para tomates que integra un sistema fotovoltaico y un colector solar.
- **Respuesta del modelo** (ruta `hybrid`): El artículo más citado entre los que contienen 'photovoltaic', 'agrivoltaic' o 'PV' en el título es "PHOTOVOLTAIC DEGRADATION RATES—AN ANALYTICAL REVIEW", con un total de 1267 citas. Este estudio se centra en la degradación de las celdas fotovoltaicas y analiz…
- **SQL del modelo:** `SELECT a.title, a.cited_by, a.author_keywords FROM article a WHERE a.title LIKE '%photovoltaic%' OR a.title LIKE '%agrivoltaic%' OR a.title LIKE '%PV%' ORDER BY CAST(a.cited_by AS INTEGER) DESC LIMIT 1;`
- **Por qué esa nota:** Sin filtro: devuelve una revisión de degradación fotovoltaica (1.267 citas) que es referencia, no Azam.

#### Q17 · Nota: 1/5
- **Pregunta:** ¿Cuáles fueron los artículos más citados publicados entre 2007 y 2012 y de qué tratan?
- **Esperada:** Dos artículos con 13 citas cada uno: Meng et al. (2009), un sistema integrado de invernadero y calentador solar para la digestión anaerobia de lodos activados; y Rankins et al. (2008), el secado solar de mangos para conservar la provitamina A en África occidental francófona.
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron artículos específicos publicados entre 2007 y 2012 con un alto número de citas en la consulta SQL. Sin embargo, los artículos recuperados por búsqueda semántica presentan una variedad de temas y niveles de citas: 1. **Artículo 1**: "DESARROLL…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN citation c ON a.sr = c.sr_ref WHERE CAST(a.year AS INTEGER) BETWEEN 2007 AND 2012 ORDER BY CAST(c.cited_by AS INTEGER) DESC LIMIT 10;`
- **Por qué esa nota:** SQL con columna inventada (citation.cited_by): sin resultados; luego describe artículos irrelevantes del RAG.

#### Q18 · Nota: 2/5
- **Pregunta:** ¿Qué artículos tienen autores de Bangladesh y de qué tratan?
- **Esperada:** 3 artículos: Rahman et al. (2022), revisión de energías renovables en agricultura (165 citas); Rana et al. (2023), acuicultura marina y un secador de pescado inteligente basado en IoT; y Rony et al. (2024), agrovoltaica más acuaponía en azoteas urbanas de Dhaka.
- **Respuesta del modelo** (ruta `hybrid`): Los artículos con autores de Bangladesh que se encuentran en la base de datos son los siguientes: 1. **"VERTICAL BIFACIAL SOLAR FARMS: PHYSICS, DESIGN, AND GLOBAL OPTIMIZATION"**: Este artículo no proporciona un resumen o abstracto. 2. **"STUDY ON REHYDRATION …
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid JOIN affiliation af ON au.authorid = af.authorid WHERE af.country LIKE '%Bangladesh%' ORDER BY a…`
- **Por qué esa nota:** El filtro de país funciona, pero sin limitar a artículos principales: lista referencias de Bangladesh y no los 3 esperados.

#### Q19 · Nota: 1/5
- **Pregunta:** ¿Qué artículos publicó el grupo de Carsten Agert y de qué tratan?
- **Esperada:** 3 artículos (Osterthun et al., 2021–2022), todos sobre celdas solares espectralmente selectivas que combinan fotovoltaica y fotosíntesis: celdas ultradelgadas de germanio (30 citas), su efecto en el crecimiento de microalgas en fotobiorreactores (8 citas) y su desempeño con datos PV-GIS (0 citas).
- **Respuesta del modelo** (ruta `hybrid`): El grupo de Carsten Agert ha publicado artículos en diversas áreas del conocimiento, según se desprende de la búsqueda semántica. A continuación, se presentan algunos de sus trabajos y su temática: 1. **"DESARROLLO DE UN MODELO MATEMÁTICO PARA EL BIOSECADO DE …
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.authorid = au.authorid WHERE au.authorname LIKE '%Carsten Agert%' ORDER BY a.year DESC LIMIT 10;`
- **Por qué esa nota:** El nombre no coincide ('Carsten Agert' vs 'AGERT C.') y luego atribuye a Agert artículos del RAG que no son suyos: inventa.

#### Q20 · Nota: 1/5
- **Pregunta:** ¿Qué artículos publicó Jason A. Carlyon y tienen relación con los agrovoltaicos?
- **Esperada:** 2 artículos sobre la bacteria Anaplasma phagocytophilum (Read et al., 2022, 16 citas; Oki et al., 2015, 10 citas). Son de microbiología y no tienen relación con los agrovoltaicos.
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron artículos publicados por Jason A. Carlyon que tengan relación con los agrovoltaicos según la consulta SQL realizada. Sin embargo, la búsqueda semántica arrojó varios artículos que pueden estar relacionados de manera indirecta o temática con t…
- **SQL del modelo:** `SELECT a.title, a.abstract, a.year, CAST(a.cited_by AS INTEGER), a.author_keywords, a.doi, a.document_type, a.source_title, a.ismainarticle FROM article a JOIN articleauthor aa ON a.sr = aa.sr JOIN author au ON aa.author…`
- **Por qué esa nota:** Dice que Carlyon no tiene artículos (nombre mal escrito en el SQL); tiene 2.

#### Q21 · Nota: 1/5
- **Pregunta:** ¿Qué artículos publicó Acta Horticulturae en el corpus y de qué tratan?
- **Esperada:** 4 artículos: arreglos fotovoltaicos sobre un huerto de perales (Singh R., 2024); pepino con solución nutritiva oxigenada en invernaderos (Singh P., 2021); temperatura y humedad en un invernadero plástico asimétrico (Hu, 2018); estrategias pre y poscosecha para compuestos bioactivos (Gil, 2015).
- **Respuesta del modelo** (ruta `hybrid`): Acta Horticulturae publicó varios artículos en el corpus, aunque no se encontraron resultados estructurados en la consulta SQL. A continuación, se presentan detalles sobre algunos de los artículos recuperados por búsqueda semántica: 1. **"DESARROLLO DE UN MODE…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN source_title st ON a.source_title = st.id WHERE st.title LIKE '%Acta Horticulturae%' AND a.document_type = 'article' AND a.ismainarticle = 1 LIMIT 10;`
- **Por qué esa nota:** Inventa una tabla source_title y luego presenta artículos del RAG como si fueran de Acta Horticulturae: inventa.

#### Q22 · Nota: 1/5
- **Pregunta:** ¿Qué artículos con participación de Alemania se publicaron desde 2022 y cuáles tratan sobre agrovoltaicos?
- **Esperada:** 4 artículos. Solo uno trata de agrovoltaica: el desempeño de una celda solar espectralmente selectiva con datos PV-GIS (Osterthun, 2022). Los otros tratan de producción agrícola resiliente y climáticamente neutra (Uhl, 2023), manejo de lodos fecales en asentamientos de desplazados (Orugba, 2024) y producción de metanol renovable (Svitnič, 2024).
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron artículos específicos con participación de Alemania que traten sobre agrovoltaicos publicados desde 2022. La consulta SQL no devolvió resultados, lo que indica que no hay artículos en la base de datos que cumplan con los criterios de país, añ…
- **SQL del modelo:** `SELECT a.title, a.abstract, a.year, CAST(a.cited_by AS INTEGER) AS cited_by FROM article a JOIN affiliation af ON a.sr = af.sr WHERE af.country = 'Germany' AND CAST(a.year AS INTEGER) = 2022 AND a.author_keywords LIKE '%…`
- **Por qué esa nota:** Busca 'Germany' en minúscula y exige la keyword 'agrovoltaics': responde que no hay ninguno (hay 4, uno sobre el tema).

### RAG puro (Q23–Q32)

#### Q23 · Nota: 1/5
- **Pregunta:** ¿Qué estudio del corpus usa energía solar para compostar lodos de depuración y qué encontró?
- **Esperada:** Chen et al. (2014) compararon tres reactores (ordinario, de invernadero y solar) para compostar lodos municipales: el reactor solar dio calor más estable y fue el único que mantuvo más de 55 °C por más de 3 días, mejorando la calidad del compost como fertilizante.
- **Respuesta del modelo** (ruta `hybrid`): No se encontraron estudios específicos en la base de datos que combinan el uso de energía solar para compostar lodos de depuración. Sin embargo, los artículos recuperados por búsqueda semántica proporcionan información relevante sobre aplicaciones de energía s…
- **SQL del modelo:** `SELECT a.title, a.abstract FROM article a JOIN author_keywords ak ON a.sr = ak.sr WHERE ak.keywords LIKE '%energía solar%' AND ak.keywords LIKE '%compostar lodos de depuración%' LIMIT 10;`
- **Por qué esa nota:** Enruta a hybrid con una tabla inventada; el RAG no recupera a Chen et al.: dice que no hay estudios.

#### Q24 · Nota: 1/5
- **Pregunta:** ¿Cómo funciona el secador de invernadero híbrido para tomates estudiado en el corpus?
- **Esperada:** Es un secador de invernadero autónomo de convección forzada que integra un sistema fotovoltaico y un colector solar; se evaluó con un modelo térmico y distintos pretratamientos del tomate (el escaldado 15 min aceleró el secado), comparado con el secado al sol.
- **Respuesta del modelo** (ruta `hybrid`): Lamentablemente, no se encontraron artículos específicos sobre el secador de invernadero híbrido para tomates en la consulta SQL ni en los resultados de búsqueda semántica. Sin embargo, puedo informar sobre temas relacionados que podrían ser útiles para entend…
- **SQL del modelo:** `SELECT title, abstract, year, CAST(cited_by AS INTEGER) AS cited_by_count FROM article WHERE title LIKE '%secador de invernadero híbrido%' AND document_type = 'article' LIMIT 10;`
- **Por qué esa nota:** No recupera a Azam et al.; responde con temas no relacionados.

#### Q25 · Nota: 4/5
- **Pregunta:** ¿Qué propone el estudio sobre agrovoltaica y acuaponía en azoteas urbanas?
- **Esperada:** Integrar paneles solares (8 de 500 W, unos 4.000 W) y un sistema acuapónico (peces y plantas sin suelo en circuito cerrado) en azoteas de Dhaka, Bangladesh, con recolección de agua lluvia, para producir energía y alimentos donde falta suelo.
- **Respuesta del modelo** (ruta `rag`): El estudio sobre agrovoltaica y acuaponía en azoteas urbanas, presentado en el artículo "Integrated Agrivoltaics and Aquaponic Systems for Urban Rooftop Farming: A Case Study in Dhaka, Bangladesh" (2024), propone la integración de sistemas agrícolas y fotovolt…
- **Por qué esa nota:** Recupera el artículo correcto (Rony 2024) y explica bien la idea; faltan detalles (8×500 W, agua lluvia).

#### Q26 · Nota: 1/5
- **Pregunta:** ¿Qué herramienta del corpus sirve para comparar y elegir configuraciones de sistemas agrovoltaicos?
- **Esperada:** Un marco basado en simulación que combina indicadores (proporción de cultivo, energía por hectárea, rendimiento energético específico, eficiencia del agua, inversión inicial) en un análisis multicriterio, y clasifica cuatro configuraciones (vertical, monoaxial interespaciada, monoaxial elevada y biaxial elevada) según el entorno.
- **Respuesta del modelo** (ruta `rag`): No se encontró información específica sobre herramientas del corpus para comparar y elegir configuraciones de sistemas agrovoltaicos en los artículos proporcionados. Los artículos presentan temas variados, como análisis de contenido de humedad en granos de caf…
- **Por qué esa nota:** No recupera a Bellone et al.; dice que no hay información.

#### Q27 · Nota: 2/5
- **Pregunta:** ¿Qué tratamiento se aplica al digestato de estiércol en el estudio de secado solar del corpus?
- **Esperada:** Secado solar combinado con acidificación del digestato y de su fracción sólida, para reducir el contenido de agua y las emisiones gaseosas; el digestato acidificado conservó más nitrógeno.
- **Respuesta del modelo** (ruta `hybrid`): En el estudio de secado solar del digestato de estiércol, no se encontraron resultados específicos en la consulta SQL que combinara los términos "digestato de estiércol" y "secado solar". Sin embargo, en los artículos recuperados por búsqueda semántica, se pue…
- **SQL del modelo:** `SELECT DISTINCT a.title, a.author_keywords FROM article a JOIN treeofscience ts ON a.sr = ts.sr WHERE a.title LIKE '%digestato de estiércol%' AND a.title LIKE '%secado solar%';`
- **Por qué esa nota:** No recupera a Morey et al., pero menciona otros trabajos de energía solar con digestato y aclara que infiere.

#### Q28 · Nota: 1/5
- **Pregunta:** ¿Qué diseña el estudio sobre el secador solar de invernadero en Filipinas?
- **Esperada:** Un sistema de control para un secador solar de invernadero, que reduce el riesgo de los trabajadores expuestos a altas temperaturas y da más flexibilidad al secado de productos agrícolas.
- **Respuesta del modelo** (ruta `rag`): El estudio sobre el secador solar de invernadero en Filipinas no se encuentra directamente mencionado entre los artículos proporcionados. Sin embargo, el artículo más relevante es: - **Artículo 2 (2014)**: "EXPERIMENTAL INVESTIGATION OF ACTIVE SOLAR DRYER FOR …
- **Por qué esa nota:** No recupera a Basilio et al.; propone un secador de chiles como sustituto.

#### Q29 · Nota: 1/5
- **Pregunta:** ¿Qué sistema se usó para calentar la digestión anaerobia de lodos activados excedentes?
- **Esperada:** Un sistema integrado de invernadero y calentador solar que mantuvo la temperatura de digestión mesofílica y termofílica, elevándola entre unos 10 y 28 °C según la estación y aumentando la producción de biogás.
- **Respuesta del modelo** (ruta `rag`): En los artículos encontrados no se menciona específicamente el sistema utilizado para calentar la digestión anaerobia de lodos activados excedentes. Los artículos se centran en temas como el biosecado de residuos sólidos orgánicos, la sostenibilidad de la dige…
- **Por qué esa nota:** No recupera a Meng et al.; dice que ningún artículo lo menciona.

#### Q30 · Nota: 2/5
- **Pregunta:** ¿Qué estudio del corpus seca mangos con energía solar y con qué propósito?
- **Esperada:** Rankins et al. (2008): secado solar de 3,75 t de mango fresco (360 kg secos) para reducir las pérdidas poscosecha y conservar beta-caroteno frente a la deficiencia de vitamina A en África occidental francófona.
- **Respuesta del modelo** (ruta `rag`): El estudio del secado de mangos con energía solar se encuentra en el artículo "THERMAL PERFORMANCE OF INDIRECT FORCED CONVECTION SOLAR DRYER AND KINETICS ANALYSIS OF MANGO" (2018) en la revista APPL THERM ENG. Este trabajo investiga el rendimiento térmico de u…
- **Por qué esa nota:** Encuentra un estudio de secado solar de mango, pero no es Rankins (2008) y no da el propósito (vitamina A).

#### Q31 · Nota: 1/5
- **Pregunta:** ¿Qué tipo de celda solar se propone en el corpus para combinar fotovoltaica y fotosíntesis?
- **Esperada:** Una celda solar espectralmente selectiva de germanio ultradelgado, cuya transmisión se ajusta al espectro de absorción de la clorofila, para usarla en sistemas agrovoltaicos, invernaderos y fotobiorreactores.
- **Respuesta del modelo** (ruta `rag`): No se encontró información específica sobre un tipo de celda solar que combine fotovoltaica y fotosíntesis en los artículos proporcionados. Los artículos abordan temas relacionados con energía solar y producción agrícola, pero no mencionan este tipo de combina…
- **Por qué esa nota:** No recupera a Osterthun et al.; dice que no hay información.

#### Q32 · Nota: 2/5
- **Pregunta:** ¿Qué tipos de productos agrícolas se secan con energía solar en los artículos del corpus?
- **Esperada:** Entre otros: tomate (y pasta y hojuelas de tomate), cacao, mango, amla, pescado, residuos de cultivos, digestato y lodos. 26 artículos del corpus tienen 'dry' o 'drying' en el título.
- **Respuesta del modelo** (ruta `hybrid`): En los artículos del corpus que se refieren a la energía solar, se mencionan varios tipos de productos agrícolas que pueden ser secados utilizando esta tecnología. Según el artículo titulado "Solar Drying of Agricultural Products: A Review" (2011), se abordan …
- **SQL del modelo:** `SELECT DISTINCT a.document_type, a.title FROM article a WHERE a.title LIKE '%energía solar%' ORDER BY a.title DESC LIMIT 10;`
- **Por qué esa nota:** Respuesta general (café, frutas, verduras, tomate); falta la mayoría de productos del corpus (cacao, mango, amla, pescado...).
