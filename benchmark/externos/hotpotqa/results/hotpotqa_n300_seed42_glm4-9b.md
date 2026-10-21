# HotpotQA (dev distractor) — n300_seed42_glm4-9b

- Generador: `glm4:9b` · recuperación: nomic-embed-text top-5 sobre los 10 párrafos de cada pregunta
- Fecha: 2026-10-16 14:07 · latencia media del LLM: 9.9 s

| Subconjunto | n | EM | F1 | Precisión | Recall | 2 párrafos de apoyo en top-k |
|---|---|---|---|---|---|---|
| Todas | 300 | 0.4567 | 0.5627 | 0.5761 | 0.5660 | 0.813 |
| Puente (bridge) | 256 | 0.4258 | 0.5395 | 0.5540 | 0.5405 | 0.781 |
| Comparación | 44 | 0.6364 | 0.6975 | 0.7043 | 0.7140 | 1.000 |

Vu et al. (AQO): Gemini 2.5 Flash EM 0,6017 · F1 0,7334 · P 0,7517 · R 0,7473; Gemini 2.5 Pro EM 0,6310 · F1 0,7587 · P 0,7794 · R 0,7710.
