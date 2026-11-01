# RAG Text-to-SQL Bibliométrico — contexto del proyecto

Proyecto de tesis (TDG) de William Andrés Velásquez Ruiz (UNAL), con Daniel Camilo Blanco Galán,
dirigido por el profesor Sebastián Robledo Giraldo. Este espacio (`demo_limpio`) es la versión
limpia y funcional del prototipo. Responder siempre en español.

## Qué hace el sistema

Agente conversacional que responde preguntas sobre corpus bibliométricos (exportes de Scopus
procesados con el algoritmo de Robledo / Tree of Science) decidiendo entre SQL, RAG o híbrido.

- **Ingesta** (`src/ingestion/load_db.py`, `src/services/ingestion_service.py`): Excel → SQLite
  por sesión en `data/sessions/<tema>/{raw,db,chroma}`.
- **Capa 1 — schema linking** (`src/layer1_schema`): NER con spaCy + embeddings del esquema en ChromaDB.
- **Capa 2 — agente LangGraph** (`src/layer2_agent/graph.py`): rewrite_query → schema_linking →
  classify_intent → `sql` (generate → validate → refine ≤3 → synthesize → reflect) | `rag` | `hybrid`.
- **Capa 3 — RAG** (`src/layer3_rag`): abstracts en ChromaDB.
- **Capa 4 — UI** Streamlit (`src/layer4_ui/app.py`).
- LLM local vía Ollama. Modelo en uso: **glm4:9b** (funciona bien según William). Embeddings: nomic-embed-text.
- Entorno: `.venv` con Python 3.14. Sesiones de datos existentes: `Agrovoltaics`, `ai`.
- Proyecto hermano más antiguo y con evaluaciones BIRD/RAGAS: `../bibliometric-rag` (ver su
  `INFORME_REENGANCHE_TESIS.md`). `../old` tiene una versión anterior de la Capa 2.

## Encuadre de la tesis (acordado en la conversación previa con Claude, sept 2026)

- Tema TDG: **detección de frentes de investigación emergentes** con un agente que integra
  bibliometría estructurada + SQL + RAG + grafo/comunidades + forecasting.
- **Research gap aprobado**: *fragmentación*. Cada pieza existe por separado (CiteSpace/VOSviewer,
  RAG científico tipo LitLLM/AutoSurvey, Text-to-SQL, Agentic RAG), pero ningún trabajo las integra
  en un mismo flujo agente para bibliometría. No afirmar "nadie ha hecho IA en bibliometría".
- El enrutamiento SQL/RAG/híbrido **no es la novedad** (ya está en la literatura de Agentic RAG,
  Singh et al. 2025, arXiv:2501.09136). La contribución es aplicarlo al dominio bibliométrico y
  extenderlo con `graph | community (Louvain, betweenness) | forecast` (Neural Prophet o
  ARIMA/Prophet justificado por interpretabilidad).
- Ya se produjeron (en claude.ai, no están en este repo): auditoría del corpus + 56 referencias,
  `main.tex`/`references.bib` (Introducción + Estado del Arte, IEEEtran), resumen para el profesor,
  doc de benchmarks y una carta a los autores vietnamitas.
  - Pendiente en el .bib: la entrada `motifets2025` tiene autores sin verificar.
  - Pendiente: la Tabla 1 del .tex se desborda horizontalmente (tabcolsep + anchos de columna).

## Evaluación (lo que pidió el profesor)

- RAG se evalúa con RAGAS/DeepEval y SQL con BIRD/Spider (EX). **No existe** una herramienta que
  unifique ambas. El antecedente más cercano es Vu, Minh & The, "Academic Query Orchestration: An AI
  Agent Framework Utilizing RAG and Text-to-SQL" (Springer CCIS 2943, ICCIES 2026,
  doi 10.1007/978-3-032-21625-0_6). Leído completo (2026-10-15): Gemini 2.5 Pro/Flash; evalúan solo por
  separado: RAG con WikiEval + 4 métricas RAGAS, multi-hop con HotpotQA (EM/F1), SQL con Spider (EX/EM, modelo
  solo vs. dentro del agente: Pro 77,8→80,0 %). **No hay benchmark híbrido en los experimentos** (el resumen
  lo menciona; lo híbrido solo aparece en 3 ejemplos cualitativos). Tampoco reportan acierto de ruta,
  ablaciones ni latencia. Su Tabla 5 compara contra Antal & Buza 2025 (RAGAS sobre resúmenes de tesis,
  doi 10.1007/s44427-025-00006-3), otro corpus. Se redactó una carta pidiéndoles detalles de su benchmark
  híbrido; aún sin respuesta.
- (2026-10-15, pedido por William) **Réplica de las pruebas de Vu et al.** en `benchmark/externos/` (WikiEval → HotpotQA →
  Spider). RAGAS 0.4.3 instalado en el `.venv` **sin `scikit-network`** (no compila en Python 3.14; solo se usa para generar
  testsets) y con un shim de `ChatVertexAI` dentro del script (langchain-community 0.4 lo quitó). `wikieval/run_wikieval.py`:
  las 50 páginas en una colección Chroma aparte, nuestro retriever (top-5) + prompt de `node_rag_search` en inglés; config
  `tal_cual` (con el corte a 300 caracteres de `format_rag_context`) y `completo` (pasaje entero, num_ctx 16384). Juez RAGAS
  glm4:9b (local, ~2 min/pregunta, se evalúa a sí mismo), `gpt-oss:120b-cloud` (Ollama, ~1 min/pregunta, máx. 3 en
  paralelo: con 8 da 429) o Google AI Studio por el endpoint OpenAI (`GEMINI_API_KEY` en `.env`, ya ignorado por git;
  nivel gratuito: Gemini 3.8 Flash 5 RPM/20 RPD, inútil; Gemma 4 31B 14.400 RPD pero ~7 min/pregunta). Resultados en
  `wikieval/RESULTADOS.md`: con el texto completo (B) y juez gpt-oss: faithfulness 0,957 · answer relevancy 0,957 ·
  context precision 1,0 · context recall 0,981 (Vu et al. Flash: 0,981/0,901/0,817/0,978). Con el corte de 300 (A):
  0,818/0,784/0,680/0,349. **Hallazgo**: `format_rag_context` cortaba cada abstract a 300 caracteres también en el agente
  real; explicaba casi toda la caída.
- [x] (2026-10-16, aprobado por William) `format_rag_context` pasa el **abstract completo**; solo si entre todos superan
  `RAG_CONTEXT_BUDGET` (20.000 caracteres) se recortan por igual. Motivo del tope: Ollama carga glm4 con num_ctx 8192 por
  defecto y recorta el principio del prompt sin avisar; no se subió num_ctx porque cambiarlo solo en algunas llamadas hace
  que Ollama recargue el modelo. Abstracts principales: Agrovoltaics media 1.673 / máx. 3.766 caracteres. Q26 sigue mal:
  la recuperación pone el artículo esperado 1.º, pero glm4 responde con el 2.º (fallo de generación, no tocado).
  **Corrida 5** (`respuestas_preguntas_scopus_32_20261016_120734`, nota en `results/evaluacion_scopus_32_20261016_corrida5.md`):
  SQL 4,50 · híbridas 3,30 · RAG 3,90 · total 3,94 (corrida 4: 3,88). Mejoran en detalle Q15, Q18, Q24, Q25, Q28, Q31;
  empeoran Q26 y Q29 porque glm4 responde con otro artículo aunque el correcto sale 1.º en la recuperación, y Q19.
  Una sola corrida: la diferencia está dentro de la variación esperable.
- (2026-10-16) **HotpotQA preparado**: `hotpotqa/run_hotpotqa.py` + `data/hotpot_dev_distractor.parquet` (Hugging Face
  `hotpotqa/hotpot_qa`, 7.405 preguntas; el servidor de CMU no respondía). Los 10 párrafos de cada pregunta en una
  colección Chroma en memoria con nuestro embedder, top-5, `format_rag_context`, glm4 con prompt en inglés + respuesta
  corta; EM/F1/P/R oficiales + párrafos de apoyo en el top-k. ~10 s/pregunta. Correr:
  `python benchmark/externos/hotpotqa/run_hotpotqa.py --n 300` (semilla 42, retoma si se corta). **Corrido 2026-10-16**
  (`hotpotqa/RESULTADOS.md`): n = 300, EM 0,457 · F1 0,563 · P 0,576 · R 0,566 (AQO Flash 0,602/0,733; Pro 0,631/0,759).
  Puente EM 0,426, comparación 0,636. Los 2 párrafos de apoyo en el top-5: 81 %; con ambos EM 0,508, sin alguno 0,232 →
  la brecha viene sobre todo de la búsqueda en un solo paso (AQO descompone y reintenta). 52 respuestas parciales (F1>0, EM=0).
- (2026-10-16) **Spider** (`spider/run_spider.py`, `spider/RESULTADOS.md`): dev, 300 preguntas (semilla 42), BD del zip oficial
  en `spider/data/` (205 MB, ignorado por git), evaluador oficial test-suite-sql-eval en `spider/eval_oficial/` (necesita `nltk`).
  glm4 solo (prompt zero-shot en inglés con CREATE TABLE): **EX 0,690 · EM 0,203**. glm4 dentro del flujo SQL del agente
  (prompts y funciones sin tocar; esquema completo en vez de la Capa 1): **EX 0,593 · EM 0,107** (Vu et al.: Pro 0,778→0,800).
  El agente empeora por reglas de dominio del prompt: `LIMIT 10` por defecto (111/300 consultas; sin él, EX 0,637
  contrafactual), `CAST` de year/cited_by (50), `LIKE`; refine rescata 3 de 30. Propuesta sin aplicar: reglas de dominio
  solo para el esquema bibliométrico y tipos de columna en el esquema.
- (2026-10-28) **Plan del profesor, pasos 1–4** (resultados locales en `*/results/`, ignorados por git):
  - Spider `--mode agente2` (reglas de dominio solo si hay tabla `article` + tipos de columna en el esquema):
    **EX 0,667 · EM 0,247** (solo 0,690/0,203; agente original 0,593/0,107).
  - Prefijos `search_document:`/`search_query:` de nomic (`embedder.PrefixedOllamaEmbeddingFunction`, metadata
    `embed_prefix`; sesiones Agrovoltaics/ai/pendulo reindexadas; el chroma de WikiEval no).
  - HotpotQA n = 300, EM/F1: top-5 sin prefijos 0,457/0,563 · top-5 con prefijos 0,453/0,572 (apoyo en top-5 82 %) ·
    los 10 párrafos 0,427/0,522 · solo los 2 de oro **0,507/0,621** (techo de glm4) · `--contexto iterativo` (estilo
    CoRAG con prompt: hasta 2 búsquedas extra de 2 párrafos que decide el LLM) **0,473/0,590**, apoyo 85,7 %, 26 s/pregunta.
    Solo 22/300 piden búsqueda extra (EM 0,18→0,41 en esas); 12 ganadas y 6 perdidas frente al top-5 (parte es ruido de temp 0,3).
  - Benchmark de agrovoltaicos sin repetir tras los prefijos.
  - **Paso 6, otros modelos** (mismo flujo, mismas 300 preguntas; logs en `benchmark/externos/modelos_log/`; qwen3 con
    `NO_THINK=1` = sin razonamiento; gpt-oss:120b-cloud por Ollama cloud). HotpotQA top-5 EM/F1: glm4 0,457/0,563 ·
    qwen3:8b 0,487/0,599 · gpt-oss 0,617/0,738 (AQO Flash 0,602/0,733). Oro: 0,507 · 0,577 · 0,693. Spider EX/EM oficial,
    solo → agente (agente2): glm4 0,690/0,203 → 0,667/0,247 · qwen3:8b 0,730/0,373 → 0,650/0,323 · gpt-oss 0,780/0,290 →
    0,767/0,270 (Vu et al. Pro 0,778 → 0,800). Hallazgo: el flujo SQL del agente no mejora a ningún modelo (−1 a −8 puntos
    de EX); la brecha de HotpotQA es del tamaño del modelo. Una corrida de gpt-oss se colgó 6 h en una llamada a la nube.
- (2026-10-29) **BIRD dev** (`benchmark/externos/bird/run_bird.py`, 300 preguntas, semilla 42, con evidence; EX por conjunto de filas,
  timeout 30 s; datos en `bird/data/`, ignorado por git). EX solo → agente (agente2): glm4:9b 0,313 → **0,403** · qwen3:8b 0,397 → 0,420.
  A diferencia de Spider, el flujo SQL sí suma (sobre todo en moderadas y difíciles), pero la latencia pasa de ~6 s a ~46 s por
  pregunta (~4 h por corrida). Una corrida; la mejora de qwen3 está dentro del ruido. Regla vigente: registrar tiempos en toda prueba.
- (2026-10-28) **Ollama 0.31.2**: un prompt de más de num_ctx (8192) ya **no se recorta en silencio**; ahora falla
  con un error 400 (`exceed_context_size_error`). Además, glm4 a veces entra en un bucle y genera texto basura
  (82.000 "@", horas). En los benchmarks: HotpotQA usa `num_predict=100` y `run_spider.py` registra la excepción
  como fallo sin detener la corrida. El agente real no tiene ninguno de los dos resguardos (pendiente).
- (2026-10-29) **Agrovoltaicos con glm4 + prefijos** (`respuestas_preguntas_scopus_32_20261029_215630`, nota en
  `results/evaluacion_scopus_32_20261029_glm4_prefijos.md`, 38 min, 70 s/pregunta): SQL 4,42 · híbridas 2,70 · RAG 4,30 · total 3,84
  (= qwen3:8b; corrida 5 3,94). Los prefijos no mueven el total. Q16 y Q20 fallaron por prompt híbrido > 8.192 tokens.
- [x] (2026-10-30, aprobado por William) **Resguardo de contexto en las síntesis**: `answer_synthesizer.PROMPT_DATA_BUDGET`
  (20.000 caracteres, env) para los datos de cada prompt. `_format_results(..., budget)` recorta por igual las celdas largas
  (abstracts) hasta que la tabla quepa; en `synthesize_hybrid` el SQL toma hasta la mitad y `format_rag_context(..., budget)`
  ajusta los abstracts a lo que queda (400 caracteres de metadatos por artículo); el seguimiento usa 1/2 y 1/4. Probado
  Q16–Q18 y Q20: 0 errores de contexto (antes 2). Q16 sigue mal por generación: el SQL trae a Azam 2020 y glm4 responde con
  Rahman 2022, que viene del RAG.
- [x] (2026-10-30, aprobado por William) **Tope de salida**: las 12 llamadas a `ChatOllama` del agente (capas 2 y 3) pasan
  `num_predict=OLLAMA_NUM_PREDICT` (env, 2048 tokens) para cortar los bucles de "@" de glm4. La respuesta más larga en
  266 respuestas del benchmark tiene ~5.000 caracteres (~1.700 tokens). Verificado: con 5 genera 5 tokens; Q01, Q15, Q25
  sin cambios (5 min). Ojo con modelos que razonan sin `NO_THINK=1`: el razonamiento cuenta dentro del tope.
- (2026-10-30) **Benchmark por plantillas** (`benchmark/plantillas/`): 20 plantillas iguales en Agrovoltaics (desarrollo), `ai` y
  `pendulo` (prueba); gold con SQL sobre cada BD (`build_plantillas.py`); puntaje automático 0–1 por cifras o títulos
  (`run_plantillas.py`, retoma; `--report`). glm4:9b, 93 min, 93 s/pregunta: total **0,79 · 0,75 · 0,82** (SQL 0,78 en los 3;
  híbridas 0,77 · 0,62 · 0,87; RAG 0,83 en los 3). **No hay sobreajuste a Agrovoltaics**: los fallos son de plantilla y se
  repiten en los 3 corpus. S06 ("citas del más citado") falla en los 3 con el mismo SQL (`COUNT(*)` en vez de `cited_by`);
  S08/H03 (autor por nombre: `LIKE '%CARSTEN AGERT%'` contra `AGERT, CARSTEN`, `'%UY SAL%'`, `authorname 'SINGLA A'`)
  fallan o quedan parciales en los 3; H04 (país) une `affiliation` por `authorid` en vez de `sr` y el `LIMIT 10` sobre filas
  duplicadas corta títulos; ai-H01 une `scimagodb` sin necesidad (0 filas). RAG: 9/18 se enrutan a `hybrid` y el SQL
  `LIKE` sobre el título no sirve; fallan R05 (Agro), R01 (ai), R03 (pendulo). Ojo: `source_title='J FINANC'` aparece en
  respuestas de ai/pendulo (bug de datos sin decidir).
- [x] (2026-10-30, aprobado por William) **Autores por nombre y JOIN de afiliaciones**:
  - Causa de S08/H03/Q09/Q10: cada autor tiene 2 filas en `author` con formatos distintos (`AGERT, CARSTEN` 3 art. /
    `CARSTEN AGERT` 1; `SINGLA, ASHISH` 5 / `ASHISH SINGLA` 2; `MURAT PAŞA UYSAL`). `schema_linker.author_hints(db_path, query)`
    busca nombres de `author.authorfullname` cuyas palabras (2+, sin tildes, cualquier orden) estén todas en la pregunta y da
    sus formas exactas como pista de valor (`authorfullname IN (…)`); se suma a `value_hints` en `node_schema_linking`.
    Sin falsos positivos en las 60 plantillas + 32 preguntas (solo S08/H03, Q09, Q10, Q19, Q20).
  - `sql_validator.link_affiliation_to_article` (dentro de `clean_sql`): un `JOIN affiliation … ON` sin `sr` recibe
    `AND af.sr = <artículo>.sr` (o `articleauthor`). Antes H04 traía 61/12/90 artículos distintos en vez de 4.
    `dedupe_fanout` además pone `DISTINCT` en listados con solo columnas del artículo (el `LIMIT 10` se gastaba en repetidos).
  - Prueba con glm4 (13 preguntas, 20 min, 94 s/pregunta): S08 1/1/1 (antes 0/0/0), H03 1/1/1 (antes 0,33/0,33/0,6),
    H04 1/0,75/1 (antes 0,5/0,75/0,75); Q09 3/38 y Q10 2/26 correctas, Q19 correcta; Q20 parcial (el SQL añade un filtro
    `author_keywords LIKE '%AGROVOLTAIC%'` y da 0 filas, aunque la respuesta dice que no tiene relación).
  - **Plantillas re-corridas** (60 preguntas, 54 min, 54 s/pregunta; antes en `results/plantillas_glm4-9b_20261030_antes.*`):
    total **0,90 · 0,84 · 0,90** (antes 0,79 · 0,75 · 0,82); SQL 0,89 en los 3, híbridas 1,00 · 0,75 · 1,00, RAG 0,83 igual.
    Solo cambian las 8 preguntas tocadas (S08×3, H03×3, H04 Agro/pendulo); ninguna empeora. La latencia bajó ~40 % en
    todas las categorías, también en las no tocadas: es del equipo/Ollama, no de los arreglos. Quedan S06×3, ai-H01,
    ai-H04 (0,75) y los 3 RAG por recuperación.
- Observaciones sobre la metodología de Vu et al. para el paper (juez de RAGAS no especificado, sin benchmark híbrido,
  Tabla 5 con otro corpus, EM > EX…): `benchmark/externos/NOTAS_PAPER_vu2026.md`.
- Datasets útiles: ScienceBenchmark/CORDIS (VLDB 2024), DBLP-QuAD (plantillas de preguntas), HeteQA
  (plantilla para set híbrido).
- Modelos candidatos para mejorar SQL: Arctic-Text2SQL-R1-7B (GGUF, importable a Ollama). Según
  arXiv:2606.29733, el schema linking por embeddings no mejora y la autoconsistencia no compensa:
  conviene una ablación con/sin Capa 1.
- Las cifras de los Qwen 27B/30B de `../bibliometric-rag` **no tienen JSON reproducible**: no
  citarlas hasta volver a correrlas.

## Benchmark propio: agrovoltaicos (`benchmark/agrovoltaics/`)

Idea: usar el artículo cienciométrico que escribieron los estudiantes de Robledo
(`Version_español_Sci_25_2S_G1_agrovoltaicos_.docx`, texto plano en `articulo_agrovoltaicos.txt`)
como referencia experta, sobre el mismo corpus (`data/sessions/Agrovoltaics/raw/agrovoltaics_Scopus_data.xlsx`).

`dataset_agrovoltaicos.xlsx` tiene 30 preguntas: Q01–Q12 SQL puro, Q13–Q20 RAG puro (respuestas
redactadas por Claude, pendientes de validar por Robledo o los autores), Q21–Q30 híbridas (afirmación
del artículo vs. BD; 3 concordantes, 5 discordantes, Q27/Q29 inconsistencias internas del artículo,
Q30 no está en Scopus). Regla: **el gold sale de la BD, el artículo solo se contrasta**.
El artículo usa Scopus+WoS (77 artículos) y la BD solo Scopus (66), así que las diferencias son esperables.
Se excluyeron las preguntas de cuartiles SJR porque el cruce con `scimagodb` no era fiable.

Importante: el gold SQL se calculó cargando **las hojas normalizadas del Excel** (Article, Author,
ArticleAuthor, Affiliation, journal, scimagodb, Citation, TreeOfScience) directamente en SQLite.
`load_db.py` en cambio re-parsea autores y afiliaciones desde la hoja Article, así que no da
los mismos resultados (ver "Estado actual").

### Dataset v2 (2026-10-04): `preguntas_32.json` / `preguntas_32.md`

Reemplaza al dataset de 30 preguntas (sus RAG preguntaban por el texto del Word, que el agente no
tiene indexado: solo conoce los abstracts del corpus). Se genera con `build_preguntas.py`, que ejecuta
el gold SQL sobre la BD. Q01–Q12 SQL, Q13–Q22 híbridas (afirmación del Word vs BD), Q23–Q32 RAG sobre
artículos que el Word describe y que están en el corpus (Q31 es una pregunta trampa: Hassanein no está
en Scopus; Q32 es temática). `evaluate.py` aún apunta al dataset viejo.
El agente se devolvió a su estado original (se revirtieron las reglas de prompt añadidas el mismo día);
solo se conservan los arreglos de ingesta. Línea base del 2026-10-04 con esos prompts modificados:
SQL EX 33 %, RAG juez 0,62/2, híbridas 30 % cifras BD (no es línea base limpia).

### Dataset v3 solo Scopus (2026-10-07): `preguntas_scopus_32.{json,md,xlsx}`

Pedido por William: preguntas parecidas a las del Word pero con respuesta esperada SOLO del corpus Scopus
(lo que ve el agente). Generado por `build_preguntas_scopus.py` (gold SQL ejecutado sobre la BD; contenido
redactado desde los abstracts). Q01–Q12 SQL, Q13–Q22 híbridas (localizar con SQL + explicar el contenido),
Q23–Q32 RAG. El Word solo aparece en `relacion_word`. Sin preguntas trampa (Hassanein se cambió por
Osterthun 2021). El Excel trae columnas vacías para anotar a mano la respuesta del modelo.
Correr: `python benchmark/agrovoltaics/run_preguntas.py --dataset preguntas_scopus_32` (Ollama debe estar encendido).
Línea base limpia 2026-10-07 (glm4:9b, agente original), nota manual 1–5 en
`results/evaluacion_scopus_32_20261007.md`: SQL 1,25 · híbridas 1,10 · RAG 1,60 · total 1,31. Causas: no filtra
`ismainarticle=1` (1.700 de 1.766 filas son referencias); índice Chroma con 1.624 docs (solo 66 del corpus) y
referencias casi sin abstract que salen en todas las búsquedas; formatos de valores (`AGERT C.`, `AIP CONF PROC`,
`GERMANY`); SQL inválido `a(sr)`; inventa cuando el SQL falla (Q19, Q21).

### Conciliación Word vs corpus (2026-10-04) — `benchmark/agrovoltaics/conciliacion/`

La BD `Agrovoltaics` es solo Scopus (66 principales); el Word usa Scopus + WoS. Con `agrovoltaics_WoS_data.xlsx`
(42 principales) la unión por DOI/título da 79 artículos (29 en ambas bases; Word: 77 = 65+41-29). Scopus+WoS
reproducen: 2007-2012 (5 art/46 citas), 2014 (78), 2015 (5 art/104), China 21 (citas 270 vs 266), Alemania 8,
Tailandia 5, Egipto 4, España 4, Australia 3, Bangladesh 3. Difieren por 1: India 11 vs 10, EE. UU. 6 vs 5,
2024 16 vs 15. Ningún par (artículo solo-Scopus, artículo solo-WoS) explica las 3 diferencias a la vez.
Hassanein 2015 SÍ está en el WoS (no en Scopus). Scripts: `union_wos_scopus.py`, `buscar_extras.py`.
Para citas, el Word coincide tomando el máximo entre Scopus y WoS. El agente no consulta WoS.

## Estado actual / próximos pasos

- [x] (2026-10-04) Ingesta: `load_excel` ahora copia las hojas del Excel Robledo tal cual como tablas
  SQLite (`_load_normalized_sheets` en `load_db.py`) cuando existen Article/Author/ArticleAuthor/
  Affiliation; el parser antiguo (re-derivar autores/afiliaciones) queda solo como respaldo para
  Excel planos. Sin claves primarias, porque hay SR repetidos. Las 22 consultas gold con SQL
  coinciden (22/22) y las sesiones `Agrovoltaics` y `ai` fueron regeneradas (SQLite; ChromaDB no).
  Consecuencia: la tabla `Article` ahora tiene las 42 columnas del Excel (p. ej. `open_access_indicator`
  en vez de `open_access`) y ya no existe `egosauthors`.
- [x] (2026-10-04) Limpieza de marcadores de dato ausente (`clean_placeholders` en `load_db.py`, se
  ejecuta al ingerir): `NO COUNTRY`, `NO AFFILIATION`, `NO ORCID`, `NAN`, `-`… pasan a NULL; se eliminan
  las filas de `Affiliation` sin país y de `journal` sin nombre. Los artículos no se borran: 26
  artículos principales de Agrovoltaics quedan con `source_title` NULL (un GROUP BY sobre esa columna
  seguirá mostrando el grupo NULL). Sesiones regeneradas; el gold de las 32 preguntas no cambió. Las
  respuestas de la corrida `respuestas_20261004_145208` se hicieron ANTES de esta limpieza.
- [x] (2026-10-01) Bug: `_to_int` convertía `"True"` en `None` (ismainarticle NULL). Corregido.
- [x] (2026-10-07, aprobado por William) Artículos principales vs referencias. `ismainarticle` sigue como 1/0 (SQLite
  no tiene booleanos; el modelo filtra bien `= 1` cuando sabe que debe). Cambios:
  - `sql_generator._build_schema_text` añade "SIGNIFICADO DE COLUMNAS" con qué es 1/0 y cuándo filtrar;
    `link_schema` incluye siempre la tabla `article`.
  - Se quitó `egosauthors` (ya no existe) de `TABLE_COLUMNS`/`SCHEMA_DOCUMENTS`, y `link_schema` descarta tablas
    viejas de índices ya creados.
  - Respaldo SQL (`graph._fallback_to_references`): si una consulta con `ismainarticle = 1` da 0 filas, se repite con
    `= 0` y la respuesta empieza con un aviso fijo (`REFERENCES_PREFIX`).
  - RAG: `retriever.search_by_origin` busca solo en principales o solo en referencias (metadata `ismainarticle` en
    Chroma, que se completa sola en índices viejos con `_ensure_main_flag`). El nodo RAG responde con los principales;
    si el LLM devuelve `NO_ENCONTRADO`, repite con las referencias y antepone `RAG_REFERENCES_PREFIX`. Híbrido y
    sugerencias de seguimiento usan solo principales. (Un primer intento mezclaba por similitud y metía referencias
    en español en 20/20 preguntas: descartado.)
  - Seguimientos: cada turno guarda `articles` [{sr, title}] en el historial (también en `app.py`). Si la pregunta
    se refiere a ellos ("de esos", "el primero"… regex `_REFERS_TO_PREVIOUS`), la ruta es `followup`
    (`node_followup` + `synthesize_followup`): responde con esos artículos (con autores y países de la BD) y
    sugiere aparte otros del corpus.
  - Probado con la sesión `pendulo`: "los 5 más citados" ya filtra solo; "de esos cinco…" responde con los 5 y
    sugiere aparte; Pendubot (solo en referencias) avisa en SQL y RAG.
- [x] (2026-10-08, aprobado por William) **Causa principal del RAG malo: idioma.** Preguntas en español vs abstracts
  en inglés con nomic-embed-text: cualquier texto en español puntúa más alto (artículo esperado 1.º en 2/9 de Q23–Q31).
  `retriever.to_search_query` traduce la pregunta al inglés con glm4 (temp 0, caché) solo para buscar en Chroma; la
  respuesta sigue en español. Con la traducción automática: 9/9 en 1.er puesto. Desactivable con `RAG_TRANSLATE_QUERY=0`.
  Si Ollama está apagado, la traducción cae en silencio a la pregunta original.
- [x] (2026-10-08) SQL inválido `alias(columna)`: el LLM imitaba el formato `tabla(col, col)` del esquema. Ahora el
  esquema se muestra como `tabla: col, col` y `sql_validator.repair_column_refs` (dentro de `clean_sql`) convierte
  `a(sr)` en `a.sr` cuando `a` es tabla o alias del FROM/JOIN. Pendiente: formatos de valores (`GERMANY`, `AGERT C.`,
  `AIP CONF PROC`) y columnas inventadas (`citation.cited_by`).
- Corrida `respuestas_preguntas_scopus_32_20261007_182846` (paso 1 con la versión descartada del RAG): SQL mejora
  (Q01, Q02, Q11, Q12 correctas) pero persisten `a(sr)` y formatos de valores; no se puntuó.
- **Corrida 2026-10-08** (`respuestas_preguntas_scopus_32_20261008_095238`, todos los cambios anteriores), nota manual en
  `results/evaluacion_scopus_32_20261008.md`: SQL 1,25→3,00 · híbridas 1,10→1,50 · RAG 1,60→3,20 · total 1,31→2,59.
  Fallos restantes: formatos de valores (7 preguntas), híbridas sin filtro de principales, la regla `NO_ENCONTRADO`
  vuelve las respuestas RAG muy cortas o da falsos "no encontrado" (Q26, Q29–Q31), columnas inventadas, inventa en Q19.
- [x] (2026-10-08, aprobado) `NO_ENCONTRADO` reemplazado por un juez aparte (`answer_synthesizer.articles_answer_question`,
  SI/NO); el prompt RAG volvió al original. Valores de ejemplo: `schema_linker.build_value_hints` (ejemplos reales de la
  BD: países en inglés y mayúsculas, autores por apellido en `authorfullname`, revistas abreviadas + `journal.journal`),
  guardados en `SchemaContext.value_hints` desde `node_schema_linking` y mostrados en `_build_schema_text`.
- **Corrida 3 2026-10-08** (`respuestas_preguntas_scopus_32_20261008_104344`), nota en
  `results/evaluacion_scopus_32_20261008_corrida3.md`: SQL 3,75 · híbridas 1,30 · RAG 3,50 · total 2,91 (base 1,31).
  Lo que más resta ahora: el filtro `ismainarticle = 1` no es estable entre corridas (Q04 y Q13 acertaron en la 2 y
  fallaron en la 3); propuesta: vista con solo principales por defecto. Además: inventa cuando el SQL no encuentra (Q19),
  `citation.cited_by` inventada, Q26 falso negativo, la síntesis falló 2 veces sin registrar la excepción (Q17/Q21).
- [x] (2026-10-08, aprobado) Vista de alcance: `sql_validator.scope_to_corpus` (dentro de `clean_sql`) reescribe
  `FROM/JOIN article` como la vista temporal `corpus_articles AS article` (solo `ismainarticle = 1`) cuando la consulta
  no menciona `ismainarticle`; si el LLM filtra `= 1` o `= 0` se respeta. Las vistas (`SCOPE_VIEWS`: `corpus_articles`,
  `reference_articles`) se crean como TEMP en cada `execute_sql`, así valen para BDs ya creadas. El respaldo a
  referencias (`_fallback_to_references`) ahora también reconoce `corpus_articles` y la cambia por `reference_articles`.
  Errores tragados: `answer_synthesizer.log_error` los imprime y los guarda con traceback en `logs/agent_errors.log`
  (síntesis SQL/híbrida/seguimiento, juez de artículos, reflexión, traducción).
  Prueba de 6 preguntas (Q04, Q09, Q13, Q16, Q26, Q29; `respuestas_preguntas_scopus_32_20261008_113716`): Q13 y Q16
  correctas, Q09 encuentra 3 artículos de Agert pero suma 46 citas (gold 38: el autor tiene 2 filas en `Author` y el JOIN
  duplica un artículo), Q04 acierta China pero con `COUNT(*)` de afiliaciones (83, gold 17), Q26 sigue dando falso
  negativo, Q29 parcial. Ningún error registrado en esas 6.
- [x] (2026-10-08, aprobado) Duplicados por JOIN (un artículo tiene varias filas en affiliation/articleauthor/author;
  p. ej. Agert tiene 2 filas en `Author`): `sql_validator.dedupe_fanout` (dentro de `clean_sql`, idempotente).
  Con GROUP BY convierte `COUNT(*)`/`COUNT(1)`/`COUNT(alias.sr)` en `COUNT(DISTINCT alias.sr)`; sin GROUP BY y solo con
  agregados del artículo (SUM de citas, AVG…) los calcula sobre `alias.sr IN (SELECT … joins … WHERE …)`. No toca consultas
  sin JOIN, con COUNT(DISTINCT …) ni agregados de otras tablas. Verificado contra el gold: Q09 3/38, Q10 2/26, Q04 China 17.
  Límite: `SR` no es único (hay SR repetidos), el semi-join los une. Las referencias siguen accesibles: con
  "referencias citadas" el LLM escribe `ismainarticle = 0` y la vista no interviene (probado). Pendiente: el LLM a veces
  escribe agregados sin sentido (`COUNT(DISTINCT cited_by)` para contar referencias).
- [x] (2026-10-08, aprobado) Seguimiento sobre referencias: probado "5 referencias más citadas" → "de esos cinco, ¿cuál sirve para
  agrovoltaica?"; toma los 5 aunque no sean principales (el origen no filtra, se buscan por SR). Fallo hallado: el modelo
  mezclaba una sugerencia con los anteriores y forzaba una relación falsa. `FOLLOWUP_SYSTEM_PROMPT` ahora exige decir que
  ninguno trata el tema si es el caso, y las sugerencias se rotulan "Sugerencia" (no "Artículo N"). Tras el cambio responde
  "Ninguno trata de agrovoltaica" + sugerencias aparte. Las sugerencias siguen saliendo solo de principales.
- **Corrida 4 2026-10-08** (`respuestas_preguntas_scopus_32_20261008_123217`), nota en
  `results/evaluacion_scopus_32_20261008_corrida4.md`: SQL 4,50 · híbridas 3,10 · RAG 3,90 · total 3,88 (base 1,31; corrida 3: 2,91).
  Restan: autor por nombre completo (Q10), columnas inventadas (Q17 `citation.cited_by`), keywords en español en el SQL (Q22),
  falso negativo Q26, Q32 incompleta, SR repetido (Q03 44 vs 45). 2 SQL fallidos, 0 excepciones registradas.
- [ ] `TABLE_COLUMNS` en `schema_linker.py` lista columnas de `scimagodb` en snake_case (`sjr_best_quartile`,
  `h_index`…) que no existen: las reales son `"SJR Best Quartile"`, `"H index"`… (error previo, no resuelto).
- [x] (2026-10-04) `benchmark/evaluate.py`: corre las 30 preguntas contra `run_agent` y reporta
  por separado EX estricta/laxa (SQL), LLM-as-judge 0-2 (RAG), cifras de la BD + juez (híbridas),
  acierto de ruta y latencia. Guarda JSON en `benchmark/agrovoltaics/results/`. No usa RAGAS (no está
  instalado); el juez es el mismo glm4:9b (`--judge-model` para otro). Prueba en 6 preguntas, ~30-70 s
  c/u: la corrida completa tarda ~20 min. Falta la corrida completa y revisar el sesgo del juez.
- Hallazgos de la prueba: Q01 el agente usa `COUNT(DISTINCT sr)` (65, gold 66 por SR repetido), Q05 olvida
  `ismainarticle=1`, y las híbridas se enrutan a `sql` en vez de `hybrid`.
- [x] (2026-10-14, decisiones de William) **Capa 5: redes, frentes y series de tiempo** (`src/layer5_network/`).
  El agente SQL/RAG queda congelado por ahora (corrida 4 = 3,88). Hallazgos sobre los datos que fijaron el diseño:
  las citas directas entre artículos del corpus casi no existen (Agrovoltaics 3/1.874, ai 10/5.588), así que los frentes
  se calculan con **acoplamiento bibliográfico** (referencias compartidas: conecta 40/65, 168/262 y 128/153 artículos);
  la coautoría está muy fragmentada (Agrovoltaics: 15 de 302 autores con ≥2 artículos, 57 grupos desconectados), así que
  **autor puente = autor con artículos en ≥2 frentes** y la intermediación en coautoría se reporta aparte ("intermediarios");
  las series son cortas (15–20 años, 1–54 artículos/año). Decidido por William: **ambas redes** (acoplamiento para frentes
  y coocurrencia de palabras clave para temas) y **series de tiempo con ARIMA** (sin Prophet). Dependencias nuevas:
  `networkx`, `statsmodels`.
  - `networks.py`: redes de acoplamiento, palabras clave (author_keywords, ≥2 artículos, sin términos genéricos tipo
    `ARTICLE`/`CONTROLLED STUDY`) y coautoría; solo artículos principales. Nodos y aristas en orden fijo: con conjuntos
    de texto el orden cambiaba con el hash de cada proceso y Louvain daba comunidades distintas (verificado igual con
    3 PYTHONHASHSEED).
  - `communities.py`: Louvain (semilla 42, frentes de ≥3 artículos), palabras clave distintivas por frente (sin las que
    están en >30 % del corpus), cruce con ramas del Tree of Science, artículos puente (betweenness en acoplamiento),
    autores puente, intermediarios y temas (cada artículo va al tema con el que comparte más palabras clave). `analyze()`
    se cachea por BD y fecha de modificación.
  - `trends.py`: crecimiento por regresión de Poisson (tasa anual + p-valor), participación de los últimos 3 años, año
    medio; ARIMA(p≤2, d≤1, q≤2) por AIC con IC 95 %, solo con ≥10 años y ≥20 artículos.
  - `context.py`: texto para el LLM. **Emergente** = crece más que el corpus, con p<0,05, y más peso reciente que el
    corpus (relativo al corpus porque todo el campo crece); **señal débil** = igual pero sin significancia. Cada grupo
    lleva su clasificación explícita (sin ella glm4 inventaba "EMERGENTE"). Si la pregunta pide temas/palabras clave se
    pasan solo temas, si no solo frentes (glm4 los mezclaba). En pronósticos con tema (palabras clave del corpus
    encontradas en la pregunta traducida; búsqueda en título+abstract+keywords; plurales y AGROVOLTAIC→AGRIVOLTAIC)
    solo se pasan las cifras del tema: con el ARIMA del corpus al lado, glm4 lo presentaba como el del tema.
  - Agente: `detect_network_intent` (reglas: puente/coautoría/centralidad → `graph`; frentes/comunidades/emergente →
    `community`; tendencia/pronóstico/evolución → `forecast`) va antes del clasificador LLM; ninguna de las 32
    preguntas del benchmark se desvía. `node_network` → `synthesize_network` (`NETWORK_SYSTEM_PROMPT`: solo explica
    cifras ya calculadas). La UI muestra "Análisis de redes calculado" en un desplegable.
  - Prueba: `benchmark/agrovoltaics/prueba_capa5.py` (7 preguntas; ruta correcta 7/7). Última corrida
    `results/prueba_capa5_Agrovoltaics_20261014_201010.md`: cifras correctas en las 7. Agrovoltaics: 4 frentes (secado
    solar/invernaderos 21 art., agrovoltaica/sombreado 7, biogás 5, Anaplasma 3 = señal débil), ningún autor puente,
    ARIMA(1,1,0) del total: 2025 13,5 (10,9–16,1). Agrovoltaica: 7 artículos, +88 %/año, emergente, sin ARIMA (serie corta).
  - (2026-10-20, pedido por William) **Diagnóstico del ARIMA** (`benchmark/series_tiempo/diagnostico_arima.py`,
    `RESULTADOS.md`), serie Agrovoltaics 2007–2024: ADF/KPSS → nivel no estacionario; 1.ª diferencia en el límite
    (ADF p 0,10, KPSS p 0,054); 2.ª diferencia estacionaria; en log(1+y) basta d = 1. Fuera de muestra (2022–2024 y
    origen móvil desde 2016): el modelo actual (AIC con d ≤ 1 → ARIMA(1,1,0)) apenas mejora al ingenuo (MAE 2,80 vs 2,90),
    subestima (sesgo +2,6) y su IC 95 % cubre el 67 %; **ARIMA(0,2,0)** MAE 2,00, sesgo +1,33, cobertura 95 %, residuos
    compatibles con ruido blanco (Ljung-Box, JB, Shapiro, heterocedasticidad; todos los candidatos pasan, n = 16–17).
    **Repetido en `ai` y `pendulo` + log(1+y) (sección 5 del informe): ARIMA(0,2,0) NO generaliza** (pendulo ×1,59 el
    ingenuo, pronostica 10→5→0; ai peor que el ingenuo en el corte 2023–25). Los errores del agente se repiten en los 3
    corpus (= ingenuo ×1,00–1,02, subestima, IC 30–38 % en los que aceleran). En conteos `ai` tiene residuos
    heterocedásticos; en log todos pasan. En log, ADF/KPSS coinciden en d = 1 en los 3 (d = 2 en log da MA = −1:
    sobrediferenciación). Más coherente: **log(1+y) ARIMA(0,1,0)/(1,1,0) con deriva impuesta** (×0,87 / ×0,71 / ×1,03–1,08;
    el AICc quita la deriva y vuelve al ingenuo); IC muy anchos. Poisson es la referencia más regular (×0,76–0,90).
  - [x] (2026-10-20, aprobado) `trends.arima_forecast` = **log(1+y) ARIMA(p,1,q) con deriva fija, p,q ≤ 1 por AICc**,
    pronóstico e IC con expm1; devuelve `aicc` y `drift_growth` (ya no `aic`); `context.py` actualizado. Elige (0,1,0)
    en los 3 corpus. Origen móvil: ×0,88 / ×0,78 / ×1,08 el ingenuo (antes ×1,00 / ×1,01 / ×1,02). Sección 6 del informe.
    Ojo: la deriva (+9,5 %/año en Agrovoltaics) no coincide con el crecimiento de Poisson (+22 %): la deriva solo
    depende del primer y último año; Poisson ajusta toda la serie.
  - Pendiente: preguntas con respuesta esperada para la Capa 5 en el benchmark; probar en `ai`/`pendulo`;
    validar los frentes contra las ramas del Tree of Science con una medida (p. ej. NMI).
- [x] (2026-10-14) **Visor de redes en la UI** (pedido por William): la app tiene arriba un selector "💬 Chat / 🕸️ Red
  del corpus". `layer5_network/export.py` (`graph_data`) convierte las redes en nodos/enlaces con los mismos colores
  que usa el agente (frentes, temas, autores puente en dorado, artículos puente con borde); `layer4_ui/network_view.py`
  genera la página con force-graph 1.43.5 (2D) o 3d-force-graph 1.73.3 (3D) desde jsDelivr (necesita internet) y se
  muestra con `st.iframe`; `layer4_ui/network_tab.py` pone los controles (red, 2D/3D, peso mínimo del enlace, ocultar
  aislados) y la tabla de grupos con la clasificación emergente/señal débil. Interacción: arrastrar, zoom, rotar (3D),
  pasar el cursor resalta vecinos, clic fija un panel con el detalle, clic en la leyenda oculta un grupo, buscador.
  `analyze()` ahora devuelve `front_of`, `theme_of`, `author_fronts` y las intermediaciones; los temas con <3 artículos
  ya no se reportan (numeración sin huecos). Lanzar: `.claude/launch.json` (`streamlit-app`, puerto 8501). Ojo:
  Streamlit no recarga los módulos importados al editarlos; hay que reiniciar el servidor.
