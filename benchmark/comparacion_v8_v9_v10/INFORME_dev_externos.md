# Sets de desarrollo y bancos externos: V8 · V9 · V10 sin consenso — 2026-11-15/16

Misma metodología que `INFORME.md` (worktrees limpios `wt_cmp_v8/v9/v10`, TEMP0, guard de `src/` por commit: V8 dd489e0d489f, V9 ba0ec83cb347, V10 a7f6aa75e5e6; el corredor aborta si el hash no coincide). Sin excepciones. V10 con consenso y WikiEval **no se corrieron** (por pedido de William). El set «32 Scopus» (juicio manual) quedó fuera. Los held-out 3/4/5 son los de `INFORME.md` (tanda del 12-13 nov). Resultados por pregunta: `resultados_por_pregunta_dev.csv`; McNemar en `mcnemar_dev.json`; tablas en `tablas_dev_externos.md`. Los bancos externos de V9 se corrieron en el worktree `wt_cmp_v9` (V8 y V10 sin consenso son las corridas del 12-13 nov, ya en `benchmark/externos/comparacion_v10/`).

## Resultados

### Sets de desarrollo: aciertos exactos (puntaje 1,0)

| Set | n | V8 | V9 | V10 sin consenso | s/preg V8 · V9 · V10sc |
|---|---|---|---|---|---|
| plantillas | 60 | 53 | 56 | 50 | 12.8 · 14.0 · 11.0 |
| prueba | 48 | 47 | 45 | 47 | 10.2 · 13.4 · 10.3 |
| prueba2 | 39 | 36 | 38 | 37 | 8.5 · 11.4 · 8.6 |
| prueba3 | 40 | 36 | 37 | 29 | 8.4 · 13.4 · 9.2 |
| prueba4 | 68 | 58 | 56 | 59 | 9.1 · 13.5 · 9.2 |
| coffee | 49 | 46 | 47 | 44 | 9.6 · 13.0 · 9.6 |
| generalizacion | 68 | 34 | 52 | 54 | 9.0 · 12.7 · 8.4 |
| **Total** | 372 | **310** | **331** | **320** | 9.7 · 13.1 · 9.5 |

Mediana s/preg y llamadas LLM/preg (todos los sets): V8: 7.7 s, 3.98 llamadas; V9: 10.4 s, 5.68 llamadas; V10 sin consenso: 7.0 s, 3.99 llamadas

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
| V10 sin consenso vs V8 | plantillas | 60 | 50 | 53 | 1 | 4 | 0.3750 |
| V10 sin consenso vs V8 | prueba | 48 | 47 | 47 | 1 | 1 | 1.0000 |
| V10 sin consenso vs V8 | prueba2 | 39 | 37 | 36 | 1 | 0 | 1.0000 |
| V10 sin consenso vs V8 | prueba3 | 40 | 29 | 36 | 1 | 8 | 0.0391 |
| V10 sin consenso vs V8 | prueba4 | 68 | 59 | 58 | 3 | 2 | 1.0000 |
| V10 sin consenso vs V8 | coffee | 49 | 44 | 46 | 0 | 2 | 0.5000 |
| V10 sin consenso vs V8 | generalizacion | 68 | 54 | 34 | 20 | 0 | 0.0000 |
| V10 sin consenso vs V8 | combinado | 372 | 320 | 310 | 27 | 17 | 0.1742 |
| V10 sin consenso vs V9 | plantillas | 60 | 50 | 56 | 1 | 7 | 0.0703 |
| V10 sin consenso vs V9 | prueba | 48 | 47 | 45 | 2 | 0 | 0.5000 |
| V10 sin consenso vs V9 | prueba2 | 39 | 37 | 38 | 0 | 1 | 1.0000 |
| V10 sin consenso vs V9 | prueba3 | 40 | 29 | 37 | 1 | 9 | 0.0215 |
| V10 sin consenso vs V9 | prueba4 | 68 | 59 | 56 | 5 | 2 | 0.4531 |
| V10 sin consenso vs V9 | coffee | 49 | 44 | 47 | 0 | 3 | 0.2500 |
| V10 sin consenso vs V9 | generalizacion | 68 | 54 | 52 | 2 | 0 | 0.5000 |
| V10 sin consenso vs V9 | combinado | 372 | 320 | 331 | 11 | 22 | 0.0801 |

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

## Límites

Una corrida por celda (TEMP0); sets de desarrollo ya vistos por quien diseñó V9/V10; generalización dominada por reglas añadidas con ese mismo set; no se corrió V10 con consenso en estos sets ni V9 sin consenso, así que el efecto del consenso y el de las reparaciones de V10 no están separados.
