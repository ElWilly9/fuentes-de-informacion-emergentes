# Sets de desarrollo y bancos externos: V8 · V9 · V10 sin consenso — 2026-11-15/16

Misma metodología que `INFORME.md` (worktrees limpios `wt_cmp_v8/v9/v10`, TEMP0, guard de `src/` por commit: V8 dd489e0d489f, V9 ba0ec83cb347, V10 a7f6aa75e5e6; el corredor aborta si el hash no coincide). Sin excepciones. WikiEval **no se corrió** (por pedido de William). V10 con consenso se corrió después (16-nov, sección propia más abajo). El set «32 Scopus» (juicio manual) quedó fuera. Los held-out 3/4/5 son los de `INFORME.md` (tanda del 12-13 nov). Resultados por pregunta: `resultados_por_pregunta_dev.csv`; McNemar en `mcnemar_dev.json`; tablas en `tablas_dev_externos.md`. Los bancos externos de V9 se corrieron en el worktree `wt_cmp_v9` (V8 y V10 sin consenso son las corridas del 12-13 nov, ya en `benchmark/externos/comparacion_v10/`).

## Resultados

### Sets de desarrollo: aciertos exactos (puntaje 1,0)

| Set | n | V8 | V9 | V10 sin consenso | V10 con consenso | s/preg V8 · V9 · V10sc · V10c |
|---|---|---|---|---|---|---|
| plantillas | 60 | 53 | 56 | 50 | 54 | 12.8 · 14.0 · 11.0 · 14.3 |
| prueba | 48 | 47 | 45 | 47 | 45 | 10.2 · 13.4 · 10.3 · 13.8 |
| prueba2 | 39 | 36 | 38 | 37 | 35 | 8.5 · 11.4 · 8.6 · 11.5 |
| prueba3 | 40 | 36 | 37 | 29 | 32 | 8.4 · 13.4 · 9.2 · 13.4 |
| prueba4 | 68 | 58 | 56 | 59 | 59 | 9.1 · 13.5 · 9.2 · 13.4 |
| coffee | 49 | 46 | 47 | 44 | 48 | 9.6 · 13.0 · 9.6 · 12.8 |
| generalizacion | 68 | 34 | 52 | 54 | 57 | 9.0 · 12.7 · 8.4 · 12.9 |
| **Total** | 372 | **310** | **331** | **320** | **330** | 9.7 · 13.1 · 9.5 · 13.2 |

Mediana s/preg y llamadas LLM/preg (todos los sets): V8: 7.7 s, 3.98 llamadas; V9: 10.4 s, 5.68 llamadas; V10 sin consenso: 7.0 s, 3.99 llamadas; V10 con consenso: 10.3 s, 5.66 llamadas

### McNemar exacto pareado (b = A sí / B no; c = B sí / A no)

| A vs B | set | n | A | B | b | c | p |
|---|---|---|---|---|---|---|---|
| V9 vs V8 | plantillas | 60 | 56 | 53 | 3 | 0 | 0.2500 |
| V9 vs V8 | prueba | 48 | 45 | 47 | 0 | 2 | 0.5000 |
| V9 vs V8 | prueba2 | 39 | 38 | 36 | 2 | 0 | 0.5000 |
| V9 vs V8 | prueba3 | 40 | 37 | 36 | 1 | 0 | 1.0000 |
| V9 vs V8 | prueba4 | 68 | 56 | 58 | 2 | 4 | 0.6875 |
| V9 vs V8 | coffee | 49 | 47 | 46 | 2 | 1 | 1.0000 |
| V9 vs V8 | generalizacion | 68 | 52 | 34 | 19 | 1 | 0.0000 |
| V9 vs V8 | combinado | 372 | 331 | 310 | 29 | 8 | 0.0008 |
| V9 vs V8 | **combinado sin generalización** | 304 | 279 | 276 | 10 | 7 | 0.6291 |
| V10 sin consenso vs V8 | plantillas | 60 | 50 | 53 | 1 | 4 | 0.3750 |
| V10 sin consenso vs V8 | prueba | 48 | 47 | 47 | 1 | 1 | 1.0000 |
| V10 sin consenso vs V8 | prueba2 | 39 | 37 | 36 | 1 | 0 | 1.0000 |
| V10 sin consenso vs V8 | prueba3 | 40 | 29 | 36 | 1 | 8 | 0.0391 |
| V10 sin consenso vs V8 | prueba4 | 68 | 59 | 58 | 3 | 2 | 1.0000 |
| V10 sin consenso vs V8 | coffee | 49 | 44 | 46 | 0 | 2 | 0.5000 |
| V10 sin consenso vs V8 | generalizacion | 68 | 54 | 34 | 20 | 0 | 0.0000 |
| V10 sin consenso vs V8 | combinado | 372 | 320 | 310 | 27 | 17 | 0.1742 |
| V10 sin consenso vs V8 | **combinado sin generalización** | 304 | 266 | 276 | 7 | 17 | 0.0639 |
| V10 sin consenso vs V9 | plantillas | 60 | 50 | 56 | 1 | 7 | 0.0703 |
| V10 sin consenso vs V9 | prueba | 48 | 47 | 45 | 2 | 0 | 0.5000 |
| V10 sin consenso vs V9 | prueba2 | 39 | 37 | 38 | 0 | 1 | 1.0000 |
| V10 sin consenso vs V9 | prueba3 | 40 | 29 | 37 | 1 | 9 | 0.0215 |
| V10 sin consenso vs V9 | prueba4 | 68 | 59 | 56 | 5 | 2 | 0.4531 |
| V10 sin consenso vs V9 | coffee | 49 | 44 | 47 | 0 | 3 | 0.2500 |
| V10 sin consenso vs V9 | generalizacion | 68 | 54 | 52 | 2 | 0 | 0.5000 |
| V10 sin consenso vs V9 | combinado | 372 | 320 | 331 | 11 | 22 | 0.0801 |
| V10 sin consenso vs V9 | **combinado sin generalización** | 304 | 266 | 279 | 9 | 22 | 0.0294 |
| V10 con consenso vs V8 | plantillas | 60 | 54 | 53 | 4 | 3 | 1.0000 |
| V10 con consenso vs V8 | prueba | 48 | 45 | 47 | 1 | 3 | 0.6250 |
| V10 con consenso vs V8 | prueba2 | 39 | 35 | 36 | 1 | 2 | 1.0000 |
| V10 con consenso vs V8 | prueba3 | 40 | 32 | 36 | 1 | 5 | 0.2188 |
| V10 con consenso vs V8 | prueba4 | 68 | 59 | 58 | 3 | 2 | 1.0000 |
| V10 con consenso vs V8 | coffee | 49 | 48 | 46 | 3 | 1 | 0.6250 |
| V10 con consenso vs V8 | generalizacion | 68 | 57 | 34 | 23 | 0 | 0.0000 |
| V10 con consenso vs V8 | combinado | 372 | 330 | 310 | 36 | 16 | 0.0078 |
| V10 con consenso vs V8 | **combinado sin generalización** | 304 | 273 | 276 | 13 | 16 | 0.7111 |
| V10 con consenso vs V9 | plantillas | 60 | 54 | 56 | 1 | 3 | 0.6250 |
| V10 con consenso vs V9 | prueba | 48 | 45 | 45 | 1 | 1 | 1.0000 |
| V10 con consenso vs V9 | prueba2 | 39 | 35 | 38 | 0 | 3 | 0.2500 |
| V10 con consenso vs V9 | prueba3 | 40 | 32 | 37 | 0 | 5 | 0.0625 |
| V10 con consenso vs V9 | prueba4 | 68 | 59 | 56 | 3 | 0 | 0.2500 |
| V10 con consenso vs V9 | coffee | 49 | 48 | 47 | 1 | 0 | 1.0000 |
| V10 con consenso vs V9 | generalizacion | 68 | 57 | 52 | 5 | 0 | 0.0625 |
| V10 con consenso vs V9 | combinado | 372 | 330 | 331 | 11 | 12 | 1.0000 |
| V10 con consenso vs V9 | **combinado sin generalización** | 304 | 273 | 279 | 6 | 12 | 0.2379 |
| V10 con consenso vs V10 sin consenso | plantillas | 60 | 54 | 50 | 4 | 0 | 0.1250 |
| V10 con consenso vs V10 sin consenso | prueba | 48 | 45 | 47 | 0 | 2 | 0.5000 |
| V10 con consenso vs V10 sin consenso | prueba2 | 39 | 35 | 37 | 0 | 2 | 0.5000 |
| V10 con consenso vs V10 sin consenso | prueba3 | 40 | 32 | 29 | 6 | 3 | 0.5078 |
| V10 con consenso vs V10 sin consenso | prueba4 | 68 | 59 | 59 | 2 | 2 | 1.0000 |
| V10 con consenso vs V10 sin consenso | coffee | 49 | 48 | 44 | 4 | 0 | 0.1250 |
| V10 con consenso vs V10 sin consenso | generalizacion | 68 | 57 | 54 | 4 | 1 | 0.3750 |
| V10 con consenso vs V10 sin consenso | combinado | 372 | 330 | 320 | 20 | 10 | 0.0987 |
| V10 con consenso vs V10 sin consenso | **combinado sin generalización** | 304 | 273 | 266 | 16 | 9 | 0.2295 |

### Bancos externos (300, semilla 42)

| Banco · métrica | V8 | V9 | V10 sin consenso |
|---|---|---|---|
| Spider EX | 0.793 | 0.790 | 0.787 |
| BIRD EX | 0.497 | 0.500 | 0.517 |
| HotpotQA EM · F1 | 0.450 · 0.560 | 0.457 · 0.572 | 0.453 · 0.560 |
| s/preg media (Spider · BIRD) — OJO: días distintos | 5.6 · 6.6 | 5.2 · 6.6 | 12.4 · 13.7 |

McNemar pareado (V9 vs V8 / V9 vs V10sc):

- Spider EX: v9 vs v8: b=0, c=1, p=1.0000
- Spider EX: v9 vs v10: b=2, c=1, p=1.0000
- BIRD EX: v9 vs v8: b=1, c=0, p=1.0000
- BIRD EX: v9 vs v10: b=1, c=6, p=0.1250
- HotpotQA EM: v9 vs v8: b=8, c=6, p=0.7905
- HotpotQA EM: v9 vs v10: b=8, c=7, p=1.0000

## Lectura

1. **Total en los 7 sets de desarrollo (372 preguntas): V9 331 (89,0 %) > V10 sin consenso 320 (86,0 %) > V8 310 (83,3 %).** V9 vs V8 p = 0,0008; V10 sin consenso vs V8 p = 0,17; V10 sin consenso vs V9 p = 0,08. Casi toda esa diferencia sale del set de **generalización** (V8 34/68, V9 52, V10 sin consenso 54): ese set es de desarrollo para V9/V10 (los arreglos del 9-nov y V10 se eligieron con él), así que **no es evidencia de generalización**.
2. **Sin generalización (6 sets, 304 preguntas): V8 276 · V9 279 · V10 sin consenso 266.** V9 vs V8: b = 10 (V9 sí/V8 no), c = 7, p = 0,63 (sin diferencia). V10 sin consenso vs V8: b = 7, c = 17, p = 0,064; V10 sin consenso vs V9: b = 9, c = 22, **p = 0,029** (V9 acierta más). Es decir, fuera del set donde se desarrolló, V10 sin consenso es peor que V9 y no mejora a V8.
3. **Regresión de V10 sin consenso (verificada en parte).** En prueba3 pierde 8 preguntas frente a V8 (36 → 29, p = 0,039) y en plantillas 4 (53 → 50); V9 acierta todas esas preguntas. Las consultas de V10 sin consenso fallan por **generación del SQL de la única candidata (qwen2.5-coder)**, no por una reparación de `clean_sql`: (a) comparan nombres con identificadores: `WHERE authorid IN ('AGERT, CARSTEN', 'CARSTEN AGERT')` en vez de la subconsulta `authorid IN (SELECT authorid FROM author WHERE authorfullname IN (…))` que escribía V8 (autores por nombre: T-S04 ×4 corpus, S08 Agrovoltaics y ai) → 0 artículos; (b) columnas/alias que no existen: `article.ismainarticle` sin tabla `article` en el FROM (Agro T-S06), `T1.year` sobre `affiliation` (ai T-S02), `a.ismainarticle` sobre `author` (coffee T-S06) → «Error SQLite: no such column»; (c) en T-S06 de ai usa `LIKE '%JORDAN%'` sobre `authorfullname` en vez de país. Con el consenso (V9) las otras dos candidatas (glm4) coinciden en un resultado y se imponen: **el consenso compensa los errores de la candidata única** de V10. Se observa además una reparación que se aplica dos veces (`HAVING T1.country IS NOT NULL AND T1.country IS NOT NULL`: inocua). **Qué cambio de V10 provoca (a)/(b) (esquema con columnas extra de `article`, regla 13 con tres ejemplos, pista de autores) no está aislado**: haría falta correr V10 con consenso y V10 sin consenso con cada cambio apagado; no se hizo.
4. **Esto matiza `INFORME.md`:** en los held-out 3/4/5 V10 sin consenso igualaba a V10 (149 vs 147) y a V8, pero en estos sets de desarrollo (plantillas, prueba3, coffee) es claramente peor que V9; el consenso sí aporta cuando la candidata única es floja. Las conclusiones «el consenso no sirve» de `INFORME.md` solo valen para esos 3 sets.
5. **Bancos externos (300, semilla 42):** Spider EX V8 0,793 · V9 0,790 · V10 sin consenso 0,787 (p = 1,0 en ambas comparaciones de V9); BIRD EX 0,497 · 0,500 · 0,517 (V9 vs V10 sin consenso b = 1, c = 6, p = 0,125); HotpotQA EM/F1 0,450/0,560 · 0,457/0,572 · 0,453/0,560 (sin diferencia). Estos scripts llaman a `generate_sql` directo, así que el consenso de V9 **no se ejercita** ahí: las diferencias V8/V9 en Spider/BIRD reflejan solo cambios de prompt/validador. **Latencia no comparable entre corridas:** V8 y V9 se midieron con 5–7 s/pregunta y V10 sin consenso con 12–14 s en otra sesión (recarga de modelos de Ollama); la corrida V9 de hoy volvió a ir rápida, así que la diferencia es de la sesión y no de la versión.

## V10 CON consenso en los sets de desarrollo (añadido 16-nov)

Misma configuración (wt_cmp_v10, guard `a7f6aa75e5e6`, TEMP0), 372 preguntas, 0 errores; resultados en `results_dev/v10__*.jsonl`.

- **Totales:** V10 con consenso **330/372 (88,7 %)**, V9 331, V10 sin consenso 320, V8 310. Por set (V10c): plantillas 54, prueba 45, prueba2 35, prueba3 32, prueba4 59, coffee 48, generalización 57 (V8 34, V9 52, V10sc 54).
- **McNemar V10c vs V9:** combinado b = 11, c = 12, p = 1,0 (empate); sin generalización (304): 273 vs 279, b = 6, c = 12, p = 0,24. **V10c vs V8:** combinado 330 vs 310, p = 0,008 (todo por generalización: 57 vs 34, p < 0,0001); sin generalización 273 vs 276, b = 13, c = 16, p = 0,71 (empate). **V10c vs V10 sin consenso:** combinado 330 vs 320 (b = 20, c = 10, p = 0,099); sin generalización 273 vs 266 (b = 16, c = 9, p = 0,23): el consenso suma ~10 aciertos, en el límite de la significación.
- **¿Recupera lo que perdía V10 sin consenso?** Solo en parte. En prueba3, de las 8 preguntas que V8 acertaba y V10sc no, V10c recupera 5 (V9 recupera las 8); no recupera T-S04 de Agrovoltaics y ai (autor por nombre) ni ai-T-S02 (país con año). En plantillas, de las 4, V10c recupera 1 (V9 las 4); no recupera el S08 (autor por nombre) en Agrovoltaics, ai ni pendulo. Es decir, las dos candidatas glm4 de V9 resuelven bien «autor por nombre» y con V10 esa ruta se rompe aunque haya consenso: **V10 con consenso es peor que V9 en autores por nombre**, lo que apunta a un cambio de V10 (esquema/pista de autores) que sesga a las tres candidatas, no solo a la del coder. Sigue sin estar aislado cuál.
- **Latencia y llamadas:** V10c 13,2 s/pregunta (mediana 10,3 s; 5,66 llamadas), V9 13,1 s (10,4 s; 5,68), V10 sin consenso 9,5 s (7,0 s; 3,99), V8 9,7 s (7,7 s; 3,98). El consenso cuesta ~+3,7 s y ~+1,7 llamadas por pregunta.
- **Lectura:** fuera del set donde se desarrolló (generalización), V10 con consenso no mejora a V8 ni a V9 (273 vs 276 y 279). Los cambios de V10 sobre V9 (columnas extra, regla 13, reparaciones) no aportan en los 6 sets y probablemente perjudican «autor por nombre»; el consenso sí ayuda (+7 en 304). La ventaja de V9/V10 sobre V8 en el total viene de generalización.

## Límites

Una corrida por celda (TEMP0); sets de desarrollo ya vistos por quien diseñó V9/V10; generalización dominada por reglas añadidas con ese mismo set; no se corrió V9 sin consenso ni V10 con cada cambio apagado, así que el efecto de cada cambio de V10 sobre V9 sigue sin aislarse.
