# WikiEval + RAGAS: nuestro RAG vs. Vu et al. (ICCIES 2026, Tabla 4)

Fecha: 2026-10-15. Script: `run_wikieval.py`. Resultados por pregunta en `results/ragas_*.csv`.

## Montaje

- WikiEval (50 preguntas, 50 páginas de Wikipedia de 2022+; `vibrantlabsai/WikiEval` en Hugging Face).
- Nuestro pipeline: las 50 páginas indexadas con `get_abstracts_collection` (nomic-embed-text, coseno),
  recuperación top-5 con `retriever._query`, respuesta de **glm4:9b** (temp. 0,3) con el prompt de
  `node_rag_search` (solo cambia el idioma: inglés).
- **A `tal_cual`**: contexto armado con `format_rag_context`, que corta cada texto a **300 caracteres**
  (así funciona hoy el agente con los abstracts).
- **B `completo`**: el mismo pipeline, pero el LLM ve el pasaje completo (num_ctx 16384).
- Juez RAGAS 0.4.3 (métricas clásicas: faithfulness, answer relevancy, context precision con referencia,
  context recall). Embeddings de answer relevancy: nomic-embed-text.
- Recuperación: página correcta en 1.er lugar en **50/50** preguntas (en ambas configuraciones).

## Resultados

| Sistema | Juez | Faithfulness | Answer relevancy | Context precision | Context recall |
|---|---|---|---|---|---|
| Nuestro RAG, A (corte 300) | glm4:9b | 0,834 | 0,754 | 0,940 | 0,432 |
| Nuestro RAG, A (corte 300) | gpt-oss:120b-cloud | 0,818 | 0,784 | 0,680 | 0,349 |
| **Nuestro RAG, B (texto completo)** | **gpt-oss:120b-cloud** | **0,957** | **0,957** | **1,000** | **0,981** |
| Nuestro RAG, B (texto completo) | glm4:9b | en curso | | | |
| AQO + Gemini 2.5 Flash (Vu et al.) | no especificado | 0,981 | 0,901 | 0,817 | 0,978 |
| AQO + Gemini 2.5 Pro (Vu et al.) | no especificado | 0,985 | 0,868 | 0,934 | 0,983 |

Juez parcial: Gemma 4 31B (AI Studio, nivel gratuito) puntuó 19/50 de A; se dejó por lento (~7 min/pregunta).

## Lectura

1. **Con el texto completo, nuestro RAG con un modelo local de 9B queda al nivel de AQO con Gemini 2.5**:
   igual en context recall, por encima en answer relevancy y context precision, algo por debajo en faithfulness.
2. **El corte a 300 caracteres de `format_rag_context` explica casi toda la diferencia** de la config A:
   la página recuperada es la correcta, pero el LLM no ve la parte que contiene la respuesta y contesta
   "no aparece en los pasajes" (p. ej. q7, q9, q40). Esto también afecta al agente real con los abstracts.
3. Los jueces coinciden en faithfulness y answer relevancy (±0,03). glm4 es indulgente en context precision
   con contextos recortados (0,94 vs 0,68 de gpt-oss): con un juez más fuerte se detecta que el recorte no sirve.

## Cautelas para citar

- El juez no es el mismo que el de Vu et al. (no lo especifican; probablemente Gemini). Las cifras de RAGAS
  dependen del juez.
- WikiEval es fácil para la recuperación (50 páginas muy distintas entre sí); no dice nada sobre la búsqueda
  en un corpus bibliométrico grande y homogéneo.
- RAGAS 0.4.3 con las métricas clásicas (`ragas.metrics`), sin `scikit-network` (Python 3.14).
