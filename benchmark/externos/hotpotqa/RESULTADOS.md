# HotpotQA (distractor): nuestro RAG vs. Vu et al. (ICCIES 2026, Tablas 6-7)

Fecha: 2026-10-16. Script: `run_hotpotqa.py`. Respuestas por pregunta en
`results/respuestas_n300_seed42_glm4-9b.jsonl`; tabla en `results/hotpotqa_n300_seed42_glm4-9b.md`.

## Montaje

- HotpotQA dev *distractor* (7.405 preguntas, todas nivel *hard*; Hugging Face `hotpotqa/hotpot_qa`).
  **Muestra aleatoria de 300 (semilla 42)**: 256 de puente y 44 de comparación (la proporción del dev es 80/20).
- Por pregunta: los 10 párrafos (2 útiles + 8 distractores) en una colección Chroma en memoria con nuestro embedder
  (nomic-embed-text, coseno), recuperación top-5 con `retriever._query`, contexto con `format_rag_context` (texto
  completo) y respuesta de **glm4:9b** (temp. 0,3). Una sola búsqueda por pregunta (el agente no hace búsquedas en
  varios pasos). Única adaptación: pedir la respuesta corta.
- Métricas oficiales de la respuesta (normalización de `hotpot_evaluate_v1`). Además, recuperación: si los 2 párrafos
  de apoyo quedan en el top-5.

## Resultados

| Sistema | n | EM | F1 | Precisión | Recall |
|---|---|---|---|---|---|
| **Nuestro RAG + glm4:9b** | 300 | **0,457** | **0,563** | **0,576** | **0,566** |
| — preguntas de puente | 256 | 0,426 | 0,540 | 0,554 | 0,541 |
| — preguntas de comparación | 44 | 0,636 | 0,698 | 0,704 | 0,714 |
| AQO + Gemini 2.5 Flash (Vu et al.) | ¿? | 0,602 | 0,733 | 0,752 | 0,747 |
| AQO + Gemini 2.5 Pro (Vu et al.) | ¿? | 0,631 | 0,759 | 0,779 | 0,771 |
| SAE-large (supervisado) | dev completo | 0,669 | 0,796 | | |
| HGN (supervisado) | dev completo | 0,661 | 0,794 | | |

Intervalo de confianza del 95 % para nuestro EM con n = 300: ±0,056 (0,40–0,51).

Recuperación: los 2 párrafos de apoyo quedan en el top-5 en el **81,3 %** de las preguntas (puente 78,1 %,
comparación 100 %).

## Lectura

1. **Quedamos ~15 puntos de EM y ~17 de F1 por debajo de AQO.** A diferencia de WikiEval, aquí sí hay una diferencia clara.
2. **La causa principal es la búsqueda en un solo paso**, no solo el tamaño del modelo:
   - Cuando la recuperación trae los 2 párrafos de apoyo (244 preguntas), EM = **0,508**; cuando falta alguno (56), EM = **0,232**.
   - Las preguntas de puente necesitan un segundo salto: la entidad intermedia no está en la pregunta, así que una sola
     búsqueda por similitud no la encuentra. AQO descompone la pregunta y vuelve a buscar (bucle de autocorrección).
   - En las de comparación (las dos entidades están en la pregunta, recuperación 100 %) llegamos a EM 0,636, al nivel
     del AQO completo.
3. **EM es muy estricta con el formato**: 52 respuestas son parcialmente correctas (F1 > 0, EM = 0), p. ej.
   "Stone Brewing Co." frente a "Stone Brewing", "Matt Kemp" frente a "Matthew Ryan Kemp", "2011 Pulitzer Prize"
   frente a "Pulitzer Prize". Por eso la F1 es la métrica más informativa.

## Cautelas para citar

- Muestra de 300 de 7.405; Vu et al. no dicen cuántas preguntas usaron ni la modalidad (probablemente *distractor*).
- Nuestro sistema hace **una sola búsqueda**; AQO planifica y reintenta. La comparación mide sistemas distintos,
  no solo modelos distintos.
- Para comparar en igualdad de arquitectura habría que añadir búsqueda en varios pasos (descomponer la pregunta o
  buscar de nuevo con la entidad puente): sería una mejora del agente, no del benchmark.
