# Evaluación manual — corrida 4 (2026-10-08)

Corrida `respuestas_preguntas_scopus_32_20261008_123217_glm4-9b`. Nota 1–5 puesta a mano leyendo cada respuesta.
Cambios respecto a la corrida 3: vista `corpus_articles` (principales por defecto), `dedupe_fanout` (conteos sin duplicados),
registro de errores, prompt del seguimiento (este último no se ejercita en las 32).

## Resumen

| Bloque | Base 10-07 | Corrida 2 | Corrida 3 | **Corrida 4** |
|---|---|---|---|---|
| SQL (Q01–12) | 1,25 | 3,00 | 3,75 | **4,50** |
| Híbridas (Q13–22) | 1,10 | 1,50 | 1,30 | **3,10** |
| RAG (Q23–32) | 1,60 | 3,20 | 3,50 | **3,90** |
| **Total** | 1,31 | 2,59 | 2,91 | **3,88** |

Errores de SQL tras 3 reintentos: 2 (Q17 `c.cited_by` inexistente, Q32 `misuse of aggregate COUNT()`). Excepciones tragadas registradas: 0.

## Notas por pregunta

| Q | Nota | Comentario |
|---|---|---|
| Q01 | 5 | 66. |
| Q02 | 5 | 2024, 13. |
| Q03 | 3 | 44 en vez de 45: `COUNT(DISTINCT sr)` une dos artículos con el mismo SR (límite conocido). |
| Q04 | 5 | China, 17 (antes 1.025 o 83). |
| Q05 | 5 | 7. |
| Q06 | 5 | 8. |
| Q07 | 5 | Acta Horticulturae, 4. |
| Q08 | 5 | 3. |
| Q09 | 5 | 3 artículos, 38 citas (antes 13/288 y 3/46). |
| Q10 | 1 | Busca `'%CARLYON JASON A%'` y la BD guarda otro orden: 0 artículos (gold 2/26). Debería buscar por apellido. |
| Q11 | 5 | Los 5 autores. |
| Q12 | 5 | 78. |
| Q13 | 5 | Rahman 2022 y de qué trata. |
| Q14 | 5 | Chen 2014 y qué estudió. |
| Q15 | 4 | Fasahati correcto; añade un dato falso ("ELSEVIER B.V., 2017"). |
| Q16 | 4 | Azam 2020, 69 citas, correcto; el párrafo de la búsqueda semántica es confuso. |
| Q17 | 1 | SQL con `citation.cited_by` inventada; luego describe artículos que no son de 2007–2012. |
| Q18 | 3 | Lista 2 de 3 (falta Rahman 2022). |
| Q19 | 3 | Encuentra 1 de los 3 artículos de Osterthun y lo atribuye bien, pero lo presenta como el único. |
| Q20 | 2 | Concluye bien que no hay relación con agrovoltaicos, pero no dice que Carlyon tiene 2 artículos (Anaplasma) y lista artículos ajenos. |
| Q21 | 3 | 3 de los 4 artículos de Acta Horticulturae; Gil aparece mezclado entre "relacionados". |
| Q22 | 1 | Exige la keyword `AGROVOLTAICOS` (español) y responde que no hay ninguno (hay 4). |
| Q23 | 5 | Chen 2014, tres reactores. |
| Q24 | 4 | Secador correcto; faltan los pretratamientos. |
| Q25 | 4 | Correcto; faltan detalles (8 × 500 W, agua lluvia). |
| Q26 | 2 | Señala el artículo correcto como "parece relevante" pero dice que no se identifica la herramienta (falso negativo parcial). |
| Q27 | 5 | Acidificación + secado solar y su propósito. |
| Q28 | 4 | Sistema de control correcto; falta el propósito (riesgo de trabajadores). |
| Q29 | 4 | Sistema integrado invernadero + calentador solar; falta el aumento de temperatura. |
| Q30 | 5 | Mango, vitamina A, pérdidas poscosecha. |
| Q31 | 4 | Celdas espectralmente selectivas; falta decir germanio y clorofila. |
| Q32 | 2 | Solo cacao y granos; faltan tomate, mango, amla, pescado… SQL con COUNT mal usado. |

## Lo que sigue fallando

1. **Nombres de autor completos** (Q10): el modelo no busca por apellido.
2. **Columnas inventadas** (Q17 `citation.cited_by`) y agregados inválidos (Q32).
3. **Keywords en español en el SQL** (Q22 `AGROVOLTAICOS`, Q24, Q27): traduce términos que en la BD están en inglés.
4. **Falso negativo del RAG** (Q26) y respuestas incompletas en Q32.
5. **SR repetido** (Q03): el conteo por artículos únicos junta dos artículos distintos.
6. La ruta no siempre coincide con la esperada (Q13/Q14 van por `sql`, Q23/Q24/Q27/Q32 por `hybrid`), aunque la respuesta sea buena.
