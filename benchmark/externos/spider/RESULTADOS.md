# Spider (dev): glm4 solo vs. glm4 dentro del agente — como Vu et al. (ICCIES 2026, Tabla 8)

Fecha: 2026-10-16. Script: `run_spider.py`. Predicciones por pregunta en `results/predicciones_{solo,agente}_n300_seed42_glm4-9b.jsonl`;
salida completa del evaluador oficial en `results/evaluacion_oficial_*.txt`; tabla en `results/spider_n300_seed42_glm4-9b.md`.

## Montaje

- Spider 1.0 dev (1.034 preguntas, 20 BD), descargado del zip oficial (`spider_data.zip`, 205,8 MB, Google Drive de
  yale-lily.github.io/spider). **Muestra aleatoria de 300 (semilla 42)**: 75 easy, 131 medium, 46 hard, 48 extra.
- **Solo**: glm4:9b (temp. 0) con un prompt estándar zero-shot en inglés: los `CREATE TABLE` de la BD + la pregunta → SQL. Un intento.
- **Agente**: el flujo SQL de `graph.py` tal cual, con sus prompts (en español) y funciones: `generate_sql` → `execute_sql`
  (con `clean_sql`) → `refine_sql` hasta 3 veces → `synthesize_answer` → `reflect_on_answer` → regenerar con la crítica
  (1 vez). Única adaptación: la Capa 1 (schema linking) está hecha para el esquema bibliométrico, así que se le pasa el
  esquema completo de la BD (tablas, columnas y FKs de `tables.json`).
- Métricas con el **evaluador oficial** (`eval_oficial/`, taoyds/test-suite-sql-eval, licencia Apache 2.0): EX sobre la BD
  original (sin test suites) y EM (*exact set match*).

## Resultados

| Sistema | n | EX easy | EX medium | EX hard | EX extra | **EX** | **EM** |
|---|---|---|---|---|---|---|---|
| **glm4:9b solo** | 300 | 0,787 | 0,779 | 0,457 | 0,521 | **0,690** | **0,203** |
| **glm4:9b dentro del agente** | 300 | 0,693 | 0,626 | 0,457 | 0,479 | **0,593** | **0,107** |
| Gemini 2.5 Pro solo → AQO (Vu et al.) | ¿? | | | | | 0,778 → 0,800 | |
| AQO + Gemini 2.5 Flash (Vu et al.) | ¿? | | | | | 0,615 | 0,696 |

IC 95 % con n = 300: ±0,05 aprox. Latencia media: solo 3,0 s; agente 25,6 s (3 llamadas al LLM por pregunta).

## Lectura

1. **Al revés que en Vu et al., el agente empeora el SQL en Spider (−9,7 puntos de EX).** Por pregunta: ambos aciertan 154,
   el agente pierde 53 que el modelo solo acertaba y gana 24.
2. **La causa son las reglas del prompt pensadas para el corpus bibliométrico**, que en otras BD estorban:
   - *"Siempre incluye LIMIT si la pregunta pide top/más/mejores (default LIMIT 10)"*: el agente añadió `LIMIT` en
     **111 de 300** consultas cuyo gold no lo lleva (solo: 0). Es la causa de 27 de las 53 pérdidas. Quitando ese
     `LIMIT 10` a posteriori, el EX del agente sube a **0,637** (contrafactual, no es una corrida).
   - *"cited_by / year pueden ser TEXT: usa CAST"*: `CAST(...)` en 50 consultas (solo: 0); 13 de las pérdidas
     (p. ej. `CAST(cd.Year AS INTEGER)` o devolver el año convertido).
   - *"Para texto usa LIKE con %"*: 5 pérdidas por `LIKE '%x%'` donde el gold compara con `=`.
   - El esquema del agente va sin tipos de columna (`tabla: col, col`), mientras que el prompt solo ve los `CREATE TABLE`.
3. **El bucle de corrección casi no rescata**: 30 preguntas pasaron por `refine_sql` (sobre todo "no such column" y
   "ambiguous column name") y solo 3 terminaron bien; la reflexión se activó 7 veces (4 bien). El modelo solo deja 22
   consultas que no ejecutan; el agente, 15.
4. **EM es muy bajo en ambos** porque el analizador oficial no acepta alias de columna (`AS cuenta`) y cuenta como
   distinto cualquier `LIMIT`/`DISTINCT` de más; con LLM zero-shot es normal (EX es la métrica que importa). En *hard*
   el agente tiene más EM (0,130 vs 0,065) con el mismo EX.

## Cautelas para citar

- Muestra de 300 de 1.034; Vu et al. no dicen cuántas preguntas usaron ni qué partición.
- glm4:9b frente a Gemini 2.5 Pro/Flash: distinto modelo, no solo distinta arquitectura.
- Nuestro "agente" se evalúa con sus prompts bibliométricos sin tocar, a propósito: mide cuánto generaliza el agente tal
  como está. No es un fallo del benchmark: es una dependencia del dominio en los prompts.
- Mejora posible (sin aplicar, requiere aprobación): que las reglas de dominio (LIMIT 10, CAST de `year`/`cited_by`)
  solo apliquen al esquema bibliométrico, o mostrar tipos de columna en el esquema.
