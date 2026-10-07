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
  doi 10.1007/978-3-032-21625-0_6): reportan tres bloques por separado (SQL / RAG / híbrido propio).
  Se redactó una carta pidiéndoles detalles de su benchmark híbrido; aún sin respuesta.
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
- [ ] `TABLE_COLUMNS` en `schema_linker.py` lista columnas de `scimagodb` en snake_case (`sjr_best_quartile`,
  `h_index`…) que no existen: las reales son `"SJR Best Quartile"`, `"H index"`… (error previo, no resuelto).
- [x] (2026-10-04) `benchmark/evaluate.py`: corre las 30 preguntas contra `run_agent` y reporta
  por separado EX estricta/laxa (SQL), LLM-as-judge 0-2 (RAG), cifras de la BD + juez (híbridas),
  acierto de ruta y latencia. Guarda JSON en `benchmark/agrovoltaics/results/`. No usa RAGAS (no está
  instalado); el juez es el mismo glm4:9b (`--judge-model` para otro). Prueba en 6 preguntas, ~30-70 s
  c/u: la corrida completa tarda ~20 min. Falta la corrida completa y revisar el sesgo del juez.
- Hallazgos de la prueba: Q01 el agente usa `COUNT(DISTINCT sr)` (65, gold 66 por SR repetido), Q05 olvida
  `ismainarticle=1`, y las híbridas se enrutan a `sql` en vez de `hybrid`.
- [ ] Extender el agente con nodos graph / community / forecast para la tesis de frentes emergentes.
