# Comparación V8 · V9 · V10 (+ glm4 solo, + V10 sin consenso) en los sets held-out 3, 4 y 5 — 2026-11-12/13

Una sola tanda, en este equipo (DESKTOP-M21O3QM): 5 configuraciones × 3 sets = 895 respuestas, temperatura 0 (`TEMP0=1`), una corrida por celda.
Acierto = puntaje automático 1,0 (cifras o títulos del gold; mismo puntaje que `run_plantillas.py`). Sin excepciones en ninguna celda.

## Qué se corrió y cómo se verificó

| Configuración | Árbol (commit) | Variables |
|---|---|---|
| V8 | `wt_cmp_v8` (3875669) | glm4:9b + qwen2.5-coder:7b para SQL (prompt ddl) |
| glm4 solo | `wt_cmp_v8` (3875669) | `OLLAMA_SQL_MODEL=glm4:9b SQL_PROMPT=agente` |
| V9 | `wt_cmp_v9` (28b1a39) | consenso de 3 candidatas de SQL |
| V10 | `wt_cmp_v10` (dfccb2d) | consenso de 3 candidatas + reparaciones |
| V10 sin consenso | `wt_cmp_v10` (dfccb2d) | `SQL_ENSEMBLE=0` (opción que ya existe; no se modificó código): una sola candidata, la del coder |

- Worktrees nuevos y limpios en esos commits; no se tocó `src/` ni la carpeta principal. Antes de cada celda: hash del dataset = congelado (los 3 sets), `src/*.py` sin cambios, y el corredor aborta si el `src` importado no es el del árbol. El hash de `src` de V10 (a7f6aa75e5e6) coincide con el congelado en `congelado_heldout5.json`.
- Entorno: Ollama 0.31.2 (Docker `ollama_0312`), GPU NVIDIA RTX A2000 12 GB (driver 596.71), `num_ctx` 8192 (valor por defecto del código; Ollama reporta `context_length` 8192), `num_predict` 2048, glm4:9b Q4_0, embeddings nomic-embed-text. Calentamiento de modelos antes de cada celda (fuera de los tiempos). Orden set-mayor (set 3, 4, 5; dentro de cada set las 5 configuraciones) para repartir la deriva del equipo.
- Llamadas al LLM: contadas desde fuera, envolviendo `ChatOllama.invoke` (sin modificar el agente). No incluyen embeddings ni la traducción de consulta por HTTP.
- **Incidente (corregido):** una primera tanda completa se descartó porque mi corredor importó, en todas las celdas, el `src/` de otro worktree (se notó porque V8, V9, V10 y glm4 solo daban casi lo mismo y sin llamadas extra de consenso). Se corrigió, se verificó (aparece «[consenso]» en V9/V10) y se repitió desde cero. Esos resultados quedan en `invalido_src_equivocado/` y no se usan. Además, un cierre de sesión mató el proceso una vez; las celdas son retomables y `tanda.log` lo registra.

## Resultados (acierto y latencia)

Las preguntas RAG existen solo en los sets 3 y 4 (12 y 8); el set 5 no tiene.

### Set 3

| Configuración | Aciertos | % | SQL | Híbrida | RAG | s/preg (media · mediana) | llamadas LLM/preg (media · mediana) |
|---|---|---|---|---|---|---|---|
| V8 | 52/60 | 86.7% | 27/32 | 14/16 | 11/12 | 9.2 · 5.5 | 3.97 · 4.0 |
| glm4 solo | 52/60 | 86.7% | 28/32 | 14/16 | 10/12 | 9.1 · 5.6 | 4 · 4.0 |
| V9 | 52/60 | 86.7% | 28/32 | 14/16 | 10/12 | 10.7 · 9.2 | 5.75 · 6.0 |
| V10 | 52/60 | 86.7% | 28/32 | 14/16 | 10/12 | 10.9 · 9.1 | 5.75 · 6.0 |
| V10 sin consenso | 52/60 | 86.7% | 28/32 | 14/16 | 10/12 | 7.5 · 5.3 | 3.95 · 4.0 |

Latencia y llamadas por categoría (media s · mediana s · llamadas/preg):

| Configuración | SQL | Híbrida | RAG |
|---|---|---|---|
| V8 | 4.4 · 4.5 · 4.03 | 15.2 · 13.3 · 3.81 | 14.0 · 13.9 · 4 |
| glm4 solo | 4.9 · 5.0 · 4 | 15.1 · 14.8 · 3.81 | 12.2 · 10.3 · 4.25 |
| V9 | 7.8 · 7.9 · 6 | 15.8 · 13.8 · 5.81 | 11.7 · 10.0 · 5 |
| V10 | 7.9 · 8.0 · 6 | 15.7 · 14.1 · 5.81 | 12.6 · 11.6 · 5 |
| V10 sin consenso | 4.4 · 4.2 · 4 | 12.2 · 10.2 · 3.81 | 9.3 · 8.1 · 4 |

### Set 4

| Configuración | Aciertos | % | SQL | Híbrida | RAG | s/preg (media · mediana) | llamadas LLM/preg (media · mediana) |
|---|---|---|---|---|---|---|---|
| V8 | 36/61 | 59.0% | 19/36 | 10/17 | 7/8 | 8.5 · 5.3 | 3.8 · 4 |
| glm4 solo | 38/61 | 62.3% | 21/36 | 10/17 | 7/8 | 9.8 · 6.2 | 4.16 · 4 |
| V9 | 42/61 | 68.9% | 25/36 | 10/17 | 7/8 | 11.5 · 9.6 | 5.61 · 6 |
| V10 | 48/61 | 78.7% | 27/36 | 14/17 | 7/8 | 11.9 · 9.4 | 5.61 · 6 |
| V10 sin consenso | 49/61 | 80.3% | 28/36 | 14/17 | 7/8 | 7.4 · 5.6 | 3.84 · 4 |

Latencia y llamadas por categoría (media s · mediana s · llamadas/preg):

| Configuración | SQL | Híbrida | RAG |
|---|---|---|---|
| V8 | 4.6 · 4.7 · 4 | 15.2 · 14.7 · 3.29 | 11.7 · 9.9 · 4 |
| glm4 solo | 6.4 · 5.4 · 4.25 | 16.3 · 15.3 · 3.88 | 10.9 · 6.4 · 4.38 |
| V9 | 9.6 · 9.0 · 6 | 16.4 · 16.3 · 5.29 | 9.4 · 6.4 · 4.5 |
| V10 | 8.8 · 8.9 · 6 | 19.4 · 17.9 · 5.29 | 10.0 · 6.5 · 4.5 |
| V10 sin consenso | 4.8 · 4.5 · 4.06 | 12.5 · 11.3 · 3.29 | 8.4 · 6.3 · 4 |

### Set 5

| Configuración | Aciertos | % | SQL | Híbrida | RAG | s/preg (media · mediana) | llamadas LLM/preg (media · mediana) |
|---|---|---|---|---|---|---|---|
| V8 | 46/58 | 79.3% | 30/40 | 16/18 | — | 7.4 · 4.8 | 4.03 · 4.0 |
| glm4 solo | 41/58 | 70.7% | 27/40 | 14/18 | — | 10.5 · 6.1 | 4.12 · 4.0 |
| V9 | 47/58 | 81.0% | 31/40 | 16/18 | — | 10.9 · 9.1 | 5.95 · 6.0 |
| V10 | 47/58 | 81.0% | 31/40 | 16/18 | — | 10.6 · 9.6 | 5.93 · 6.0 |
| V10 sin consenso | 48/58 | 82.8% | 31/40 | 17/18 | — | 6.7 · 5.2 | 4 · 4.0 |

Latencia y llamadas por categoría (media s · mediana s · llamadas/preg):

| Configuración | SQL | Híbrida | RAG |
|---|---|---|---|
| V8 | 4.5 · 4.4 · 4.15 | 13.9 · 11.9 · 3.78 | — |
| glm4 solo | 9.1 · 5.0 · 4.25 | 13.5 · 11.6 · 3.83 | — |
| V9 | 9.0 · 8.2 · 6.1 | 15.2 · 12.9 · 5.61 | — |
| V10 | 8.3 · 7.9 · 6.08 | 15.5 · 13.1 · 5.61 | — |
| V10 sin consenso | 4.6 · 4.3 · 4.15 | 11.2 · 9.5 · 3.67 | — |

### Combinado (3 sets)

| Configuración | Aciertos | % | SQL | Híbrida | RAG | s/preg (media · mediana) | llamadas LLM/preg (media · mediana) |
|---|---|---|---|---|---|---|---|
| V8 | 134/179 | 74.9% | 76/108 | 40/51 | 18/20 | 8.4 · 5.2 | 3.93 · 4 |
| glm4 solo | 131/179 | 73.2% | 76/108 | 38/51 | 17/20 | 9.8 · 6.0 | 4.09 · 4 |
| V9 | 141/179 | 78.8% | 84/108 | 40/51 | 17/20 | 11.0 · 9.3 | 5.77 · 6 |
| V10 | 147/179 | 82.1% | 86/108 | 44/51 | 17/20 | 11.1 · 9.5 | 5.76 · 6 |
| V10 sin consenso | 149/179 | 83.2% | 87/108 | 45/51 | 17/20 | 7.2 · 5.4 | 3.93 · 4 |

Latencia y llamadas por categoría (media s · mediana s · llamadas/preg):

| Configuración | SQL | Híbrida | RAG |
|---|---|---|---|
| V8 | 4.5 · 4.5 · 4.06 | 14.7 · 12.7 · 3.63 | 13.1 · 11.5 · 4 |
| glm4 solo | 7.0 · 5.1 · 4.18 | 14.9 · 13.9 · 3.84 | 11.7 · 6.8 · 4.3 |
| V9 | 8.8 · 8.4 · 6.04 | 15.8 · 14.0 · 5.57 | 10.8 · 6.9 · 4.8 |
| V10 | 8.4 · 8.6 · 6.03 | 16.9 · 16.4 · 5.57 | 11.6 · 7.0 · 4.8 |
| V10 sin consenso | 4.6 · 4.4 · 4.07 | 11.9 · 10.3 · 3.59 | 9.0 · 6.8 · 4 |

## McNemar exacto pareado (bilateral, sin corrección por comparaciones múltiples)

Todos los pares y cortes (SQL, híbrida, RAG) están en `tablas.md` y `resumen.json`. TOTAL:

| A vs B | set 3 (n=60) | set 4 (n=61) | set 5 (n=58) | combinado (n=179) |
|---|---|---|---|---|
| V10 vs V8 | 52 vs 52 (b=1, c=1) p=1.000 | 48 vs 36 (b=16, c=4) p=0.012 | 47 vs 46 (b=1, c=0) p=1.000 | 147 vs 134 (b=18, c=5) p=0.011 |
| V10 vs V9 | 52 vs 52 (b=0, c=0) p=1.000 | 48 vs 42 (b=10, c=4) p=0.180 | 47 vs 47 (b=1, c=1) p=1.000 | 147 vs 141 (b=11, c=5) p=0.210 |
| V9 vs V8 | 52 vs 52 (b=1, c=1) p=1.000 | 42 vs 36 (b=6, c=0) p=0.031 | 47 vs 46 (b=1, c=0) p=1.000 | 141 vs 134 (b=8, c=1) p=0.039 |
| V8 vs glm4 solo | 52 vs 52 (b=4, c=4) p=1.000 | 36 vs 38 (b=6, c=8) p=0.790 | 46 vs 41 (b=6, c=1) p=0.125 | 134 vs 131 (b=16, c=13) p=0.711 |
| V9 vs glm4 solo | 52 vs 52 (b=4, c=4) p=1.000 | 42 vs 38 (b=8, c=4) p=0.388 | 47 vs 41 (b=6, c=0) p=0.031 | 141 vs 131 (b=18, c=8) p=0.075 |
| V10 vs glm4 solo | 52 vs 52 (b=4, c=4) p=1.000 | 48 vs 38 (b=13, c=3) p=0.021 | 47 vs 41 (b=7, c=1) p=0.070 | 147 vs 131 (b=24, c=8) p=0.007 |
| V10 vs V10 sin consenso | 52 vs 52 (b=0, c=0) p=1.000 | 48 vs 49 (b=2, c=3) p=1.000 | 47 vs 48 (b=0, c=1) p=1.000 | 147 vs 149 (b=2, c=4) p=0.688 |
| V10 sin consenso vs V8 | 52 vs 52 (b=1, c=1) p=1.000 | 49 vs 36 (b=15, c=2) p=0.002 | 48 vs 46 (b=2, c=0) p=0.500 | 149 vs 134 (b=18, c=3) p=0.002 |
| V10 sin consenso vs glm4 solo | 52 vs 52 (b=4, c=4) p=1.000 | 49 vs 38 (b=12, c=1) p=0.003 | 48 vs 41 (b=8, c=1) p=0.039 | 149 vs 131 (b=24, c=6) p=0.001 |

b = A acierta y B no; c = B acierta y A no. El combinado junta los 3 sets; como las preguntas salen de plantillas × 4 corpus no son independientes, así que su p es optimista.

## Lectura

1. **Set 3 (held-out puro para V9 y V10): las 5 configuraciones empatan en 52/60 (86,7 %).** Ningún cambio posterior a V8 mejora ni empeora ahí.
2. **Set 5 (held-out para V10):** V10 47/58, V9 47, V8 46, V10 sin consenso 48, glm4 solo 41. V10 vs V8: b=1, c=0 (p = 1,0). V10 vs glm4 solo: 7 vs 1 (p = 0,070); V10 sin consenso vs glm4 solo p = 0,039. En el informe anterior V10 tenía 48 y p = 0,039; en esta repetición V10 pierde una pregunta y el p cruza 0,05.
3. **Toda la mejora está en el set 4, que para V10 es desarrollo** (se diagnosticó con él): V10 48 y V10 sin consenso 49 contra V8 36 (V10 vs V8 p = 0,012). Eso no es evidencia de generalización para V10. Para V9 el set 4 sí era held-out: V9 42 vs V8 36 (6 vs 0, p = 0,031).
4. **Combinado:** V10 147/179 (82,1 %) vs V8 134 (74,9 %), p = 0,011, pero incluye el set 4. En los dos sets held-out para V10 (3 + 5): V10 99/118, V8 98, V9 99, V10 sin consenso 100, glm4 solo 93. **No hay evidencia held-out de que V10 supere a V8**; sí de que no lo empeora.
5. **Ablación del consenso:** V10 sin consenso acierta igual o más que V10 (149 vs 147; 2 a favor de V10, 4 en contra, p = 0,69) con latencia media **7,2 s vs 11,1 s (−35 %)**, mediana 5,4 s vs 9,5 s, y 3,93 vs 5,76 llamadas por pregunta; en SQL puro 4,6 s vs 8,4 s. Con estos tres sets, la ganancia de V10 sobre V8 se explica por las reparaciones y el esquema, no por las 3 candidatas: el consenso cuesta ~+3,9 s/pregunta sin beneficio medible. (No se corrió V9 sin consenso: para V9 no se puede separar.)
6. **V9 vs V8** (141 vs 134, p = 0,039) mezcla dos cambios: los 3 arreglos generales del 9-nov (presentes en V9, no en el V8 de 3875669) y el consenso. Estos datos no los separan.
7. **V8 vs glm4 solo:** 134 vs 131, p = 0,71; dos modelos no se distinguen de glm4 solo. V10/V10 sin consenso/V9 sí superan a glm4 solo en el set 4 y combinado, pero con los matices anteriores.
8. **Latencia:** V9 y V10 hacen ~2 llamadas más por pregunta de SQL/híbrida (6 frente a 4 en SQL puro; el SQL tarda ~2×: 8,4–8,8 s frente a 4,5 s). En híbridas y RAG pesa menos porque domina la síntesis. Mediana combinada: V8 5,2 s · glm4 solo 6,0 · V9 9,3 · V10 9,5 · V10 sin consenso 5,4.

## Qué set se usó para diagnosticar qué

- **Set 3 (60):** congelado por hash el 9-nov antes de tocar el agente; held-out para V9 y V10. Revisé commits e informes: los 3 arreglos del 9-nov se eligieron con los sets de generalización y prueba 4 y, según `heldout3/INFORME.md`, no se activan en el set 3; los fallos que este set mostró (H-S01, H-S06, H-H03, H-R03) no se atacaron. No encontré evidencia de que se usara para diagnosticar V9 ni V10. Salvedad: sus resultados base ya se conocían al diseñar V9 y V10 y el autor es el mismo, así que no es ciego en sentido estricto.
- **Set 4 (61):** held-out para V9 (src congelado antes de correrlo). **Para V10 es desarrollo.**
- **Set 5 (58):** congelado por hash antes de programar V10; held-out para V10 y V9. Sin RAG.
- Límites: los mismos 4 corpus en los tres sets; 15–16 plantillas × 4 corpus; una corrida por celda. Frente a las corridas anteriores de las mismas celdas (`tablas.md`, `reproducibilidad.json`) cambian 0–1 preguntas por celda y la latencia media varía entre −1,6 y +1,5 s/pregunta (deriva del equipo).

## Archivos

- `resultados_por_pregunta.csv`: por set y pregunta, acierto, puntaje, segundos, llamadas LLM y ruta de las 5 configuraciones.
- `tablas.md`, `resumen.json` (todos los McNemar y estadísticas por categoría), `reproducibilidad.json`.
- Código: `run_cell.py`, `run_tanda.sh`, `analiza.py`, `run_plantillas_ref.py` (copia del puntaje), `datos/` (preguntas y congelados). Los `results/*.jsonl` (respuestas y SQL completos) y los logs están ignorados por git: solo locales.
