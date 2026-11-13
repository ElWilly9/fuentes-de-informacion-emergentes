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

### McNemar exacto pareado (acierto = puntaje 1,0; bilateral)

| A vs B | corte | n | A acierta | B acierta | b (A sí, B no) | c (B sí, A no) | p |
|---|---|---|---|---|---|---|---|
| V10 vs V8 | TOTAL · set 3 | 60 | 52 | 52 | 1 | 1 | 1.0000 |
| V10 vs V8 | SQL · set 3 | 32 | 28 | 27 | 1 | 0 | 1.0000 |
| V10 vs V8 | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V10 vs V8 | RAG · set 3 | 12 | 10 | 11 | 0 | 1 | 1.0000 |
| V10 vs V8 | TOTAL · set 4 | 61 | 48 | 36 | 16 | 4 | 0.0118 |
| V10 vs V8 | SQL · set 4 | 36 | 27 | 19 | 10 | 2 | 0.0386 |
| V10 vs V8 | Híbrida · set 4 | 17 | 14 | 10 | 6 | 2 | 0.2891 |
| V10 vs V8 | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V10 vs V8 | TOTAL · set 5 | 58 | 47 | 46 | 1 | 0 | 1.0000 |
| V10 vs V8 | SQL · set 5 | 40 | 31 | 30 | 1 | 0 | 1.0000 |
| V10 vs V8 | Híbrida · set 5 | 18 | 16 | 16 | 0 | 0 | 1.0000 |
| V10 vs V8 | TOTAL · combinado | 179 | 147 | 134 | 18 | 5 | 0.0106 |
| V10 vs V8 | SQL · combinado | 108 | 86 | 76 | 12 | 2 | 0.0129 |
| V10 vs V8 | Híbrida · combinado | 51 | 44 | 40 | 6 | 2 | 0.2891 |
| V10 vs V8 | RAG · combinado | 20 | 17 | 18 | 0 | 1 | 1.0000 |
| V10 vs V9 | TOTAL · set 3 | 60 | 52 | 52 | 0 | 0 | 1.0000 |
| V10 vs V9 | SQL · set 3 | 32 | 28 | 28 | 0 | 0 | 1.0000 |
| V10 vs V9 | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V10 vs V9 | RAG · set 3 | 12 | 10 | 10 | 0 | 0 | 1.0000 |
| V10 vs V9 | TOTAL · set 4 | 61 | 48 | 42 | 10 | 4 | 0.1796 |
| V10 vs V9 | SQL · set 4 | 36 | 27 | 25 | 4 | 2 | 0.6875 |
| V10 vs V9 | Híbrida · set 4 | 17 | 14 | 10 | 6 | 2 | 0.2891 |
| V10 vs V9 | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V10 vs V9 | TOTAL · set 5 | 58 | 47 | 47 | 1 | 1 | 1.0000 |
| V10 vs V9 | SQL · set 5 | 40 | 31 | 31 | 1 | 1 | 1.0000 |
| V10 vs V9 | Híbrida · set 5 | 18 | 16 | 16 | 0 | 0 | 1.0000 |
| V10 vs V9 | TOTAL · combinado | 179 | 147 | 141 | 11 | 5 | 0.2101 |
| V10 vs V9 | SQL · combinado | 108 | 86 | 84 | 5 | 3 | 0.7266 |
| V10 vs V9 | Híbrida · combinado | 51 | 44 | 40 | 6 | 2 | 0.2891 |
| V10 vs V9 | RAG · combinado | 20 | 17 | 17 | 0 | 0 | 1.0000 |
| V9 vs V8 | TOTAL · set 3 | 60 | 52 | 52 | 1 | 1 | 1.0000 |
| V9 vs V8 | SQL · set 3 | 32 | 28 | 27 | 1 | 0 | 1.0000 |
| V9 vs V8 | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V9 vs V8 | RAG · set 3 | 12 | 10 | 11 | 0 | 1 | 1.0000 |
| V9 vs V8 | TOTAL · set 4 | 61 | 42 | 36 | 6 | 0 | 0.0312 |
| V9 vs V8 | SQL · set 4 | 36 | 25 | 19 | 6 | 0 | 0.0312 |
| V9 vs V8 | Híbrida · set 4 | 17 | 10 | 10 | 0 | 0 | 1.0000 |
| V9 vs V8 | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V9 vs V8 | TOTAL · set 5 | 58 | 47 | 46 | 1 | 0 | 1.0000 |
| V9 vs V8 | SQL · set 5 | 40 | 31 | 30 | 1 | 0 | 1.0000 |
| V9 vs V8 | Híbrida · set 5 | 18 | 16 | 16 | 0 | 0 | 1.0000 |
| V9 vs V8 | TOTAL · combinado | 179 | 141 | 134 | 8 | 1 | 0.0391 |
| V9 vs V8 | SQL · combinado | 108 | 84 | 76 | 8 | 0 | 0.0078 |
| V9 vs V8 | Híbrida · combinado | 51 | 40 | 40 | 0 | 0 | 1.0000 |
| V9 vs V8 | RAG · combinado | 20 | 17 | 18 | 0 | 1 | 1.0000 |
| V8 vs glm4 solo | TOTAL · set 3 | 60 | 52 | 52 | 4 | 4 | 1.0000 |
| V8 vs glm4 solo | SQL · set 3 | 32 | 27 | 28 | 3 | 4 | 1.0000 |
| V8 vs glm4 solo | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V8 vs glm4 solo | RAG · set 3 | 12 | 11 | 10 | 1 | 0 | 1.0000 |
| V8 vs glm4 solo | TOTAL · set 4 | 61 | 36 | 38 | 6 | 8 | 0.7905 |
| V8 vs glm4 solo | SQL · set 4 | 36 | 19 | 21 | 3 | 5 | 0.7266 |
| V8 vs glm4 solo | Híbrida · set 4 | 17 | 10 | 10 | 3 | 3 | 1.0000 |
| V8 vs glm4 solo | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V8 vs glm4 solo | TOTAL · set 5 | 58 | 46 | 41 | 6 | 1 | 0.1250 |
| V8 vs glm4 solo | SQL · set 5 | 40 | 30 | 27 | 4 | 1 | 0.3750 |
| V8 vs glm4 solo | Híbrida · set 5 | 18 | 16 | 14 | 2 | 0 | 0.5000 |
| V8 vs glm4 solo | TOTAL · combinado | 179 | 134 | 131 | 16 | 13 | 0.7111 |
| V8 vs glm4 solo | SQL · combinado | 108 | 76 | 76 | 10 | 10 | 1.0000 |
| V8 vs glm4 solo | Híbrida · combinado | 51 | 40 | 38 | 5 | 3 | 0.7266 |
| V8 vs glm4 solo | RAG · combinado | 20 | 18 | 17 | 1 | 0 | 1.0000 |
| V9 vs glm4 solo | TOTAL · set 3 | 60 | 52 | 52 | 4 | 4 | 1.0000 |
| V9 vs glm4 solo | SQL · set 3 | 32 | 28 | 28 | 4 | 4 | 1.0000 |
| V9 vs glm4 solo | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V9 vs glm4 solo | RAG · set 3 | 12 | 10 | 10 | 0 | 0 | 1.0000 |
| V9 vs glm4 solo | TOTAL · set 4 | 61 | 42 | 38 | 8 | 4 | 0.3877 |
| V9 vs glm4 solo | SQL · set 4 | 36 | 25 | 21 | 5 | 1 | 0.2188 |
| V9 vs glm4 solo | Híbrida · set 4 | 17 | 10 | 10 | 3 | 3 | 1.0000 |
| V9 vs glm4 solo | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V9 vs glm4 solo | TOTAL · set 5 | 58 | 47 | 41 | 6 | 0 | 0.0312 |
| V9 vs glm4 solo | SQL · set 5 | 40 | 31 | 27 | 4 | 0 | 0.1250 |
| V9 vs glm4 solo | Híbrida · set 5 | 18 | 16 | 14 | 2 | 0 | 0.5000 |
| V9 vs glm4 solo | TOTAL · combinado | 179 | 141 | 131 | 18 | 8 | 0.0755 |
| V9 vs glm4 solo | SQL · combinado | 108 | 84 | 76 | 13 | 5 | 0.0963 |
| V9 vs glm4 solo | Híbrida · combinado | 51 | 40 | 38 | 5 | 3 | 0.7266 |
| V9 vs glm4 solo | RAG · combinado | 20 | 17 | 17 | 0 | 0 | 1.0000 |
| V10 vs glm4 solo | TOTAL · set 3 | 60 | 52 | 52 | 4 | 4 | 1.0000 |
| V10 vs glm4 solo | SQL · set 3 | 32 | 28 | 28 | 4 | 4 | 1.0000 |
| V10 vs glm4 solo | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V10 vs glm4 solo | RAG · set 3 | 12 | 10 | 10 | 0 | 0 | 1.0000 |
| V10 vs glm4 solo | TOTAL · set 4 | 61 | 48 | 38 | 13 | 3 | 0.0213 |
| V10 vs glm4 solo | SQL · set 4 | 36 | 27 | 21 | 9 | 3 | 0.1460 |
| V10 vs glm4 solo | Híbrida · set 4 | 17 | 14 | 10 | 4 | 0 | 0.1250 |
| V10 vs glm4 solo | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V10 vs glm4 solo | TOTAL · set 5 | 58 | 47 | 41 | 7 | 1 | 0.0703 |
| V10 vs glm4 solo | SQL · set 5 | 40 | 31 | 27 | 5 | 1 | 0.2188 |
| V10 vs glm4 solo | Híbrida · set 5 | 18 | 16 | 14 | 2 | 0 | 0.5000 |
| V10 vs glm4 solo | TOTAL · combinado | 179 | 147 | 131 | 24 | 8 | 0.0070 |
| V10 vs glm4 solo | SQL · combinado | 108 | 86 | 76 | 18 | 8 | 0.0755 |
| V10 vs glm4 solo | Híbrida · combinado | 51 | 44 | 38 | 6 | 0 | 0.0312 |
| V10 vs glm4 solo | RAG · combinado | 20 | 17 | 17 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | TOTAL · set 3 | 60 | 52 | 52 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | SQL · set 3 | 32 | 28 | 28 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | RAG · set 3 | 12 | 10 | 10 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | TOTAL · set 4 | 61 | 48 | 49 | 2 | 3 | 1.0000 |
| V10 vs V10 sin consenso | SQL · set 4 | 36 | 27 | 28 | 2 | 3 | 1.0000 |
| V10 vs V10 sin consenso | Híbrida · set 4 | 17 | 14 | 14 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | TOTAL · set 5 | 58 | 47 | 48 | 0 | 1 | 1.0000 |
| V10 vs V10 sin consenso | SQL · set 5 | 40 | 31 | 31 | 0 | 0 | 1.0000 |
| V10 vs V10 sin consenso | Híbrida · set 5 | 18 | 16 | 17 | 0 | 1 | 1.0000 |
| V10 vs V10 sin consenso | TOTAL · combinado | 179 | 147 | 149 | 2 | 4 | 0.6875 |
| V10 vs V10 sin consenso | SQL · combinado | 108 | 86 | 87 | 2 | 3 | 1.0000 |
| V10 vs V10 sin consenso | Híbrida · combinado | 51 | 44 | 45 | 0 | 1 | 1.0000 |
| V10 vs V10 sin consenso | RAG · combinado | 20 | 17 | 17 | 0 | 0 | 1.0000 |
| V10 sin consenso vs V8 | TOTAL · set 3 | 60 | 52 | 52 | 1 | 1 | 1.0000 |
| V10 sin consenso vs V8 | SQL · set 3 | 32 | 28 | 27 | 1 | 0 | 1.0000 |
| V10 sin consenso vs V8 | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V10 sin consenso vs V8 | RAG · set 3 | 12 | 10 | 11 | 0 | 1 | 1.0000 |
| V10 sin consenso vs V8 | TOTAL · set 4 | 61 | 49 | 36 | 15 | 2 | 0.0023 |
| V10 sin consenso vs V8 | SQL · set 4 | 36 | 28 | 19 | 9 | 0 | 0.0039 |
| V10 sin consenso vs V8 | Híbrida · set 4 | 17 | 14 | 10 | 6 | 2 | 0.2891 |
| V10 sin consenso vs V8 | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V10 sin consenso vs V8 | TOTAL · set 5 | 58 | 48 | 46 | 2 | 0 | 0.5000 |
| V10 sin consenso vs V8 | SQL · set 5 | 40 | 31 | 30 | 1 | 0 | 1.0000 |
| V10 sin consenso vs V8 | Híbrida · set 5 | 18 | 17 | 16 | 1 | 0 | 1.0000 |
| V10 sin consenso vs V8 | TOTAL · combinado | 179 | 149 | 134 | 18 | 3 | 0.0015 |
| V10 sin consenso vs V8 | SQL · combinado | 108 | 87 | 76 | 11 | 0 | 0.0010 |
| V10 sin consenso vs V8 | Híbrida · combinado | 51 | 45 | 40 | 7 | 2 | 0.1797 |
| V10 sin consenso vs V8 | RAG · combinado | 20 | 17 | 18 | 0 | 1 | 1.0000 |
| V10 sin consenso vs glm4 solo | TOTAL · set 3 | 60 | 52 | 52 | 4 | 4 | 1.0000 |
| V10 sin consenso vs glm4 solo | SQL · set 3 | 32 | 28 | 28 | 4 | 4 | 1.0000 |
| V10 sin consenso vs glm4 solo | Híbrida · set 3 | 16 | 14 | 14 | 0 | 0 | 1.0000 |
| V10 sin consenso vs glm4 solo | RAG · set 3 | 12 | 10 | 10 | 0 | 0 | 1.0000 |
| V10 sin consenso vs glm4 solo | TOTAL · set 4 | 61 | 49 | 38 | 12 | 1 | 0.0034 |
| V10 sin consenso vs glm4 solo | SQL · set 4 | 36 | 28 | 21 | 8 | 1 | 0.0391 |
| V10 sin consenso vs glm4 solo | Híbrida · set 4 | 17 | 14 | 10 | 4 | 0 | 0.1250 |
| V10 sin consenso vs glm4 solo | RAG · set 4 | 8 | 7 | 7 | 0 | 0 | 1.0000 |
| V10 sin consenso vs glm4 solo | TOTAL · set 5 | 58 | 48 | 41 | 8 | 1 | 0.0391 |
| V10 sin consenso vs glm4 solo | SQL · set 5 | 40 | 31 | 27 | 5 | 1 | 0.2188 |
| V10 sin consenso vs glm4 solo | Híbrida · set 5 | 18 | 17 | 14 | 3 | 0 | 0.2500 |
| V10 sin consenso vs glm4 solo | TOTAL · combinado | 179 | 149 | 131 | 24 | 6 | 0.0014 |
| V10 sin consenso vs glm4 solo | SQL · combinado | 108 | 87 | 76 | 17 | 6 | 0.0347 |
| V10 sin consenso vs glm4 solo | Híbrida · combinado | 51 | 45 | 38 | 7 | 0 | 0.0156 |
| V10 sin consenso vs glm4 solo | RAG · combinado | 20 | 17 | 17 | 0 | 0 | 1.0000 |

### Celdas que ya existían vs esta tanda (mismo equipo, otro momento)

| Celda | antes: aciertos | ahora: aciertos | preguntas que cambian de acierto (antes→ahora) | antes: s/preg | ahora: s/preg |
|---|---|---|---|---|---|
| V8 set 3 | 51/60 | 52/60 | 1 (+1 / −0) | 9.0 | 9.2 |
| glm4 solo set 3 | 53/60 | 52/60 | 1 (+0 / −1) | 9.9 | 9.1 |
| V8 set 4 | 36/61 | 36/61 | 0 (+0 / −0) | 7.0 | 8.5 |
| glm4 solo set 4 | 39/61 | 38/61 | 1 (+0 / −1) | 9.7 | 9.8 |
| V9 set 4 | 41/61 | 42/61 | 1 (+1 / −0) | 12.6 | 11.5 |
| V10 set 4 | 49/61 | 48/61 | 1 (+0 / −1) | 12.4 | 11.9 |
| V8 set 5 | 46/58 | 46/58 | 0 (+0 / −0) | 6.8 | 7.4 |
| glm4 solo set 5 | 41/58 | 41/58 | 0 (+0 / −0) | 10.6 | 10.5 |
| V9 set 5 | 46/58 | 47/58 | 1 (+1 / −0) | 10.9 | 10.9 |
| V10 set 5 | 48/58 | 47/58 | 1 (+0 / −1) | 11.1 | 10.6 |
