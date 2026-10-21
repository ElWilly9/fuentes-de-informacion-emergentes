# Notas para el paper: limitaciones metodológicas de Vu et al. (2026)

Vu, Minh & The, "Academic Query Orchestration: An AI Agent Framework Utilizing RAG and Text-to-SQL",
ICCIES 2026, Springer CCIS 2943, pp. 72–87, doi 10.1007/978-3-032-21625-0_6.
Leído completo el 2026-10-15. Son observaciones para el estado del arte o la discusión; conviene redactarlas
en tono neutro ("no reportan…", "no especifican…"), no como acusaciones.

## Lo que no especifican (afecta la reproducibilidad)

1. **El LLM juez de RAGAS.** Las 4 métricas de RAGAS (Tabla 4) las calcula un LLM juez, y no dicen cuál
   fue. Tampoco qué modelo de embeddings usaron para answer relevancy. Esto importa: en nuestra réplica,
   las *mismas* respuestas puntuadas por dos jueces dieron context precision 0,94 (glm4:9b) frente a
   0,68 (gpt-oss:120b), y context recall 0,43 frente a 0,35 (`wikieval/RESULTADOS.md`, configuración A).
   Sin el juez, sus cifras no se pueden reproducir ni comparar con rigor.
2. **El tamaño de las muestras y las particiones.** No dicen cuántas preguntas usaron de WikiEval, HotpotQA
   ni Spider, ni qué partición (dev/test) de Spider.
3. **La modalidad de HotpotQA** (*distractor* o *fullwiki*). Se comparan con SAE-large y HGN, modelos
   supervisados de la modalidad *distractor*, lo que sugiere esa modalidad, pero no lo declaran.

## Lo que no reportan

4. **Ningún benchmark híbrido en los experimentos.** El resumen afirma que superan a los baselines "on a
   challenging benchmark purpose-built for hybrid, multi-source reasoning", pero la sección 4 solo evalúa
   por separado (RAG: WikiEval; multi-salto textual: HotpotQA; SQL: Spider). Lo híbrido RAG + SQL aparece
   solo en 3 ejemplos cualitativos (Fig. 3). HotpotQA es multi-documento pero **solo texto**: no hay base
   de datos.
5. **Ni acierto del enrutamiento** (si el orquestador elige bien SQL/RAG/híbrido), **ni ablaciones** del bucle
   de autocorrección o del Meta-Prompt, **ni latencias** (la sección 4.2 dice que se registraron).
6. **En HotpotQA, solo métricas de la respuesta** (EM/F1/P/R): no reportan las de los hechos de apoyo
   (supporting facts), que miden si el sistema encontró la evidencia correcta.

## Puntos discutibles

7. **La Tabla 5 compara contra un corpus distinto.** Ponen sus cifras de WikiEval junto a RAG_Mistral y RAG_Llama3
   de Antal & Buza (2025), cuyo trabajo es un benchmark sobre *resúmenes de tesis de grado* (doi
   10.1007/s44427-025-00006-3). Pendiente: leer Antal & Buza para confirmar que no usaron WikiEval.
8. **La descripción de WikiEval no coincide con el dataset.** La sección 4.1 lo describe como una tarea de
   verificación con etiquetas Supported / Contradicted / Not Enough Information. El dataset publicado
   (`explodinggradients/WikiEval`, hoy `vibrantlabsai/WikiEval`) tiene `question`, `context_v1`, `context_v2`,
   `answer`, `ungrounded_answer`, `poor_answer` y `source`, sin esas etiquetas (verificado el 2026-10-15).
9. **Tabla 8: EM mayor que EX.** Para AQO + Gemini 2.5 Flash reportan EM 0,696 y EX 0,615. Es inusual: un SQL
   idéntico al de referencia casi siempre produce el mismo resultado, así que EM ≤ EX es lo esperable.

10. **Spider "solo vs. agente" sin el prompt del modelo solo.** No dicen con qué prompt corrieron Gemini solo ni si el
    agente usa prompts específicos de su dominio académico. Importa: en nuestra réplica, el mismo glm4:9b pasa de EX 0,690
    (solo) a 0,593 dentro de nuestro agente, porque las reglas del prompt pensadas para el corpus (LIMIT 10 por defecto,
    CAST de year) estorban en otras BD (`spider/RESULTADOS.md`).

## Cómo lo usamos nosotros (para contrastar en el paper)

- Declaramos el juez (gpt-oss:120b vía Ollama Cloud, y glm4:9b como segunda opinión), las versiones
  (RAGAS 0.4.3), los embeddings (nomic-embed-text) y el tamaño y la semilla de cada muestra.
- Reportamos la recuperación por separado (página correcta en 1.er lugar 50/50 en WikiEval; párrafos de
  apoyo en el top-k en HotpotQA).
- Evaluamos lo híbrido con un benchmark propio con respuesta esperada (Q13–Q22 de `preguntas_scopus_32`).
