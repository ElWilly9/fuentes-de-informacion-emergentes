# Bancos externos con V10 sin consenso vs V8 — 2026-11-12/13

V10 sin consenso = commit dfccb2d (worktree limpio `wt_cmp_v10`) con `SQL_ENSEMBLE=0`, glm4:9b + qwen2.5-coder:7b, protocolo habitual (muestra de 300, semilla 42, Spider/BIRD en modo `agente2`, BIRD con evidence), mismo equipo (RTX A2000 12 GB, Ollama 0.31.2, `num_ctx` 8192). Línea base V8 = las corridas ya medidas con los mismos scripts y muestras (`*_dual-ddl.jsonl` en Spider y BIRD; `respuestas_n300_seed42_glm4-9b.jsonl` en HotpotQA); McNemar exacto pareado por pregunta, bilateral. **WikiEval omitido por pedido de William** (además, el juez gpt-oss:120b-cloud no estaba disponible: Ollama cloud pedía créditos/suscripción).

Aclaración de alcance: `run_spider.py` y `run_bird.py` llaman a `generate_sql` directamente (no pasan por `graph.node_generate_sql`), así que el consenso de V9/V10 no se ejercita en estos bancos, con o sin `SQL_ENSEMBLE`. Lo que cambia entre V8 y V10 aquí es el prompt SQL (regla 13), `sql_validator` (reparaciones) y el modelo/ejemplos del generador; el esquema con columnas extra de `article` no aplica (lo arma `graph.py`). La ruta RAG (`layer3_rag`) es idéntica en V8 y V10; en la síntesis solo se añadió «cantidades con dígitos».

## Resultados

| Banco | Métrica | V8 | V10 sin consenso | b (V8 sí, V10 no) / c (V10 sí, V8 no) | p |
|---|---|---|---|---|---|
| Spider dev 300 | EX (oficial) | 0,793 (238) | 0,787 (236) | 2 / 0 | 0,50 |
| Spider dev 300 | EM (oficial) | 0,530 | **0,437** | — | — |
| BIRD dev 300 | EX | 0,497 (149) | **0,517 (155)** | 1 / 7 | 0,070 |
| BIRD · simple (177) | EX | 106 | 108 | 1 / 3 | 0,63 |
| BIRD · moderate (98) | EX | 34 | 37 | 0 / 3 | 0,25 |
| BIRD · challenging (25) | EX | 9 | 10 | 0 / 1 | 1,0 |
| HotpotQA 300 | EM | 0,450 (135) | 0,453 (136) | 7 / 8 | 1,0 |
| HotpotQA 300 | F1 | 0,560 | 0,560 | — | — |

Spider por dificultad (EX, V10): easy 0,867 · medium 0,809 · hard 0,783 · extra 0,604 (V8: 0,867 · 0,809 · 0,783 · 0,646). Errores/excepciones: 0 en Spider y BIRD (ambas versiones). HotpotQA: sin errores; 36 de 300 respuestas cambian de texto (temperatura 0,3 en la generación: es ruido de muestreo, la ruta no cambió).

## Lectura

1. **Spider:** empate en ejecución (−2 preguntas, p = 0,5). **El EM cae de 0,530 a 0,437** sin que cambie el EX: 90 de 300 consultas cambian de texto y en 88 de ellas el resultado es el mismo. La causa visible es la reparación de V10 «grupos NULL fuera de los GROUP BY de una columna», que añade `HAVING col IS NOT NULL` a casi cualquier `GROUP BY` de una columna (p. ej. `GROUP BY Year HAVING Year IS NOT NULL`). Es una regla pensada para el corpus bibliométrico (revista nula) que se aplica también a esquemas de otros dominios; no cambia la exactitud de ejecución, pero distorsiona el EM y puede alterar resultados si una columna con NULL es un grupo legítimo (no verifiqué si las 2 preguntas perdidas en Spider se deben a esto). Conviene que esa reparación se condicione al esquema bibliométrico, como ya se hizo con las reglas de dominio de `agente2`.
2. **BIRD:** V10 sin consenso 0,517 frente a 0,497 de V8 (+6 netas, 7 ganadas y 1 perdida, p = 0,070): mejora numérica, en el límite de la significación, sin corrección por comparaciones múltiples; concentrada en moderate (+3). Una corrida por celda, 300 preguntas.
3. **HotpotQA:** sin diferencia (EM 0,450 vs 0,453; p = 1,0), como se esperaba porque el RAG no cambió; la diferencia entre las dos corridas es el ruido de muestreo de glm4. Frente a Vu et al. (Flash 0,602 / Pro 0,631) el resultado de glm4 con top-5 sigue en torno a 0,45.
4. **Latencia (cuidado):** las corridas antiguas de V8 son más rápidas (Spider 5,6 s vs 12,4 s; BIRD 6,6 s vs 13,7 s) con el mismo número de llamadas (3,0 y ~3,15), pero **no es atribuible a la versión**: re-corrí hoy V8 (`wt_cmp_v8`) en las primeras 39 preguntas de Spider y tarda 12,1 s/pregunta frente a 11,8 s de V10 sin consenso en esas mismas 39 y 4,6 s en la corrida antigua. El equipo (o Ollama) está más lento hoy que cuando se midieron las cifras antiguas; solo la comparación V8 vs V10 hecha hoy (misma sesión) es válida para la latencia, y ahí son iguales. (La calibración de V8 es una excepción menor al encargo de no correr V8: 39 preguntas, para aislar esto; sus EX: 33/39 igual que la corrida antigua, 32/39 V10.)

## Archivos

`resultados_por_pregunta.csv` (por banco y pregunta: acierto, segundos y llamadas de V8 y V10), `comparacion.json`, `compara_bancos.py`, `run_bancos.sh`, `logs/`. Los resultados completos de V10 (predicciones, evaluación oficial) están en `wt_cmp_v10/benchmark/externos/*/results/*_v10sc.*` (ignorados por git).
