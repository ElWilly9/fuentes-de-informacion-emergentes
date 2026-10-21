# Evaluación manual — corrida 5 (2026-10-16)

Corrida `respuestas_preguntas_scopus_32_20261016_120734_glm4-9b`. Nota 1–5 puesta a mano leyendo cada respuesta,
con el mismo criterio que la corrida 4.
Único cambio respecto a la corrida 4: `format_rag_context` pasa el **abstract completo** (antes lo cortaba a 300
caracteres; tope total de 20.000 caracteres, que aquí no se alcanza). Afecta a RAG, híbridas y seguimientos; no al SQL.

## Resumen

| Bloque | Base 10-07 | Corrida 2 | Corrida 3 | Corrida 4 | **Corrida 5** |
|---|---|---|---|---|---|
| SQL (Q01–12) | 1,25 | 3,00 | 3,75 | 4,50 | **4,50** |
| Híbridas (Q13–22) | 1,10 | 1,50 | 1,30 | 3,10 | **3,30** |
| RAG (Q23–32) | 1,60 | 3,20 | 3,50 | 3,90 | **3,90** |
| **Total** | 1,31 | 2,59 | 2,91 | 3,88 | **3,94** |

Errores de SQL tras 3 reintentos: 2 (Q17 `c.cited_by`, Q32 `misuse of aggregate COUNT()`), los mismos de la corrida 4.

## Qué cambió con el abstract completo

**Mejoran en detalle** (+1 cada una): Q15 (sin el dato falso), Q18 (los 3 artículos de Bangladesh, antes 2),
Q24 (ahora incluye los pretratamientos y el escaldado de 15 min), Q25 (agua lluvia), Q28 (el propósito: riesgo de
los trabajadores), Q31 (germanio, clorofila, resonador Fabry-Perot).

**Empeoran por elegir el artículo equivocado** (la recuperación es correcta en ambas):
- Q26 (2→1): el artículo esperado sale **1.º** en la búsqueda, pero glm4 responde con el 2.º (teoría del sistema gris, 2007).
- Q29 (4→2): el artículo esperado (Meng 2009, invernadero + calentador solar) sale **1.º**, pero glm4 responde con el 4.º
  (biodigestor asistido por energía solar, 2022).
- Q19 (3→2): además del artículo correcto, atribuye al grupo de Agert temas de la búsqueda semántica (Anaplasma).

Lectura: con 5 abstracts completos (~8.000 caracteres) el modelo de 9B tiene más información para responder con detalle,
pero a veces elige un artículo que no es el más relevante. En WikiEval no pasaba porque las páginas son muy distintas
entre sí; aquí los 5 artículos tratan temas cercanos (energía solar + agricultura).

**Cautela:** es una sola corrida. La ruta elegida varía entre corridas (Q23, Q24, Q27 y Q32 fueron por `hybrid`) y
una diferencia de 0,06 en el total está dentro de la variación esperable.

## Notas por pregunta

| Q | Nota | C4 | Comentario |
|---|---|---|---|
| Q01 | 5 | 5 | 66. |
| Q02 | 5 | 5 | 2024, 13. |
| Q03 | 3 | 3 | 44 en vez de 45 (SR repetido, límite conocido). |
| Q04 | 5 | 5 | China, 17. |
| Q05 | 5 | 5 | 7. |
| Q06 | 5 | 5 | 8. |
| Q07 | 5 | 5 | Acta Horticulturae, 4. |
| Q08 | 5 | 5 | 3. |
| Q09 | 5 | 5 | 3 artículos, 38 citas. |
| Q10 | 1 | 1 | Sigue buscando `'%CARLYON JASON A%'`: 0 artículos (gold 2/26). |
| Q11 | 5 | 5 | Los 5 autores. |
| Q12 | 5 | 5 | 78. |
| Q13 | 5 | 5 | Rahman 2022 y de qué trata. |
| Q14 | 5 | 5 | Chen 2014 y qué estudió. |
| Q15 | 5 | 4 | Fasahati 2015, descripción detallada y correcta (antes añadía un dato falso). |
| Q16 | 4 | 4 | Azam 2020, 69 citas; sigue el párrafo confuso sobre la búsqueda semántica. |
| Q17 | 1 | 1 | Otra vez `citation.cited_by` inventada; lista artículos ajenos al período. |
| Q18 | 5 | 3 | Los 3 artículos de Bangladesh con su contenido. |
| Q19 | 2 | 3 | 1 de los 3 artículos de Osterthun, y atribuye al grupo temas ajenos (Anaplasma) sacados de la búsqueda. |
| Q20 | 2 | 2 | Concluye bien que no hay relación, pero no encuentra sus 2 artículos (Anaplasma). |
| Q21 | 3 | 3 | 3 de 4; Gil vuelve a quedar entre los "semánticamente relacionados". |
| Q22 | 1 | 1 | Sigue exigiendo la keyword `AGROVOLTAICOS` (español): "no se encontraron". |
| Q23 | 5 | 5 | Chen 2014, reactor solar >55 °C por >3 días, y más cifras (−31,3 % COT, GI 91 %). |
| Q24 | 5 | 4 | Ahora con pretratamientos y escaldado de 15 min. |
| Q25 | 5 | 4 | Paneles + acuaponía + agua lluvia; solo falta el "8 × 500 W". |
| Q26 | 1 | 2 | Responde con el artículo equivocado (el correcto estaba 1.º en la recuperación). |
| Q27 | 5 | 5 | Acidificación + secado solar, con las reducciones de NH₃ y CH₄. |
| Q28 | 5 | 4 | Sistema de control con PID y su propósito. |
| Q29 | 2 | 4 | Responde con el 4.º artículo recuperado; el correcto estaba 1.º. |
| Q30 | 4 | 5 | Propósito correcto, pero no nombra el estudio (solo la revista). |
| Q31 | 5 | 4 | Celdas espectralmente selectivas de germanio ultradelgado, ajustadas a la clorofila. |
| Q32 | 2 | 2 | Solo cacao, residuos de invernadero y granos; SQL con COUNT mal usado. |

## Pendiente (propuestas, sin aplicar)

1. Q26/Q29: que el modelo priorice el artículo más similar. Opciones: pasar top-3 en vez de top-5, o pedir en el prompt
   que responda con el artículo que trate directamente la pregunta. Requiere aprobación (cambia la técnica/prompt).
2. Los fallos de SQL de siempre: Q10 (nombre completo), Q17 (columna inventada), Q22 (keyword en español), Q32.
