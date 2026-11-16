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
