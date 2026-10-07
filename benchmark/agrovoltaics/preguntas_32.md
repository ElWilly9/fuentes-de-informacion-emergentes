# Benchmark agrovoltaicos — 32 preguntas

Base: artículo Word de los estudiantes + corpus Scopus (66 artículos principales). El gold SQL se ejecuta sobre la BD; la cifra del artículo se muestra al lado para contrastar (el Word usa Scopus + WoS, por eso hay diferencias esperables).


## SQL puro (Q01–Q12)

### Q01. ¿Cuántos artículos principales hay en el corpus?
- Sección del artículo: Search output / Conclusiones
- Lo que dice el artículo: 77 publicaciones únicas (Scopus + WoS)
- Respuesta en la BD: `[[66]]`
- SQL gold: `select count(*) from Article where ismainarticle=1`
- Nota: El artículo une Scopus y WoS; la BD es solo Scopus.

### Q02. ¿En qué año se publicaron más artículos y cuántos?
- Sección del artículo: Scientific Annual Production
- Lo que dice el artículo: 2024 fue el año más productivo: Scopus 12 artículos (15 combinando WoS)
- Respuesta en la BD: `[[2024, 13]]`
- SQL gold: `select year,count(*) n from Article where ismainarticle=1 group by year order by n desc limit 1`

### Q03. ¿Cuántos artículos se publicaron entre 2020 y 2025?
- Sección del artículo: Periodo de consolidación (2020–2025)
- Lo que dice el artículo: 49 artículos publicados en el periodo
- Respuesta en la BD: `[[45]]`
- SQL gold: `select count(*) from Article where ismainarticle=1 and year between 2020 and 2025`

### Q04. ¿Qué país aparece en más artículos y cuántos?
- Sección del artículo: Country Analysis / Tabla II
- Lo que dice el artículo: China: 21 artículos (22,34 %)
- Respuesta en la BD: `[["CHINA", 17]]`
- SQL gold: `select Country,count(distinct SR) n from Affiliation where SR in (select SR from Article where ismainarticle=1) and Country!='NO COUNTRY' group by Country order by n desc limit 1`

### Q05. ¿En cuántos artículos participa al menos una institución de Alemania?
- Sección del artículo: Tabla II
- Lo que dice el artículo: Alemania: 8 artículos (8,51 %)
- Respuesta en la BD: `[[7]]`
- SQL gold: `select count(distinct SR) from Affiliation where Country='GERMANY' and SR in (select SR from Article where ismainarticle=1)`

### Q06. ¿En cuántos artículos participa al menos una institución de India?
- Sección del artículo: Tabla II
- Lo que dice el artículo: India: 10 artículos (10,64 %)
- Respuesta en la BD: `[[8]]`
- SQL gold: `select count(distinct SR) from Affiliation where Country='INDIA' and SR in (select SR from Article where ismainarticle=1)`

### Q07. ¿Qué revista tiene más artículos en el corpus y cuántos?
- Sección del artículo: Journal Analysis / Tabla III
- Lo que dice el artículo: Acta Horticulturae: 4 artículos en Scopus
- Respuesta en la BD: `[["ACTA HORTIC", 4]]`
- SQL gold: `select source_title,count(*) n from Article where ismainarticle=1 and source_title is not null group by source_title order by n desc limit 1`

### Q08. ¿Cuántos artículos del corpus se publicaron en AIP Conference Proceedings?
- Sección del artículo: Journal Analysis / Tabla III
- Lo que dice el artículo: AIP Conference Proceedings: 3 artículos en Scopus
- Respuesta en la BD: `[[3]]`
- SQL gold: `select count(*) from Article where ismainarticle=1 and source_title='AIP CONF PROC'`

### Q09. ¿Cuántos artículos tiene Carsten Agert en el corpus y cuántas citas acumulan en total?
- Sección del artículo: Tabla IV
- Lo que dice el artículo: C. Agert Carsten: 3 artículos, 38 citas
- Respuesta en la BD: `[[3, 38]]`
- SQL gold: `select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR where aa.AuthorID like 'C_AGERT%' and a.ismainarticle=1`

### Q10. ¿Cuántos artículos tiene J.A. Carlyon en el corpus y cuántas citas acumulan en total?
- Sección del artículo: Tabla IV
- Lo que dice el artículo: J.A. Carlyon: 2 artículos, 26 citas
- Respuesta en la BD: `[[2, 26]]`
- SQL gold: `select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR where aa.AuthorID like '%CARLYON%' and a.ismainarticle=1`

### Q11. ¿Cuántos autores tienen 3 o más artículos en el corpus?
- Sección del artículo: Análisis de autores / Conclusiones
- Lo que dice el artículo: Ocho investigadores registran tres publicaciones
- Respuesta en la BD: `[[5]]`
- SQL gold: `select count(*) from (select AuthorID from ArticleAuthor where SR in (select SR from Article where ismainarticle=1) group by AuthorID having count(distinct SR)>=3)`
- Nota: El artículo cuenta 8; la tabla IV lista 8 con 3 papers.

### Q12. ¿En cuántos artículos participa al menos una institución de Bangladesh?
- Sección del artículo: Tabla II
- Lo que dice el artículo: Bangladesh: 3 artículos (3,19 %)
- Respuesta en la BD: `[[3]]`
- SQL gold: `select count(distinct SR) from Affiliation where Country='BANGLADESH' and SR in (select SR from Article where ismainarticle=1)`


## Híbridas: afirmación del artículo vs BD (Q13–Q22)

### Q13. El artículo afirma que entre 2007 y 2012 se publicaron 5 artículos que acumularon 46 citas. ¿Es consistente con la base de datos?
- Sección del artículo: Periodo de baja producción (2007–2012)
- Lo que dice el artículo: 5 artículos, 46 citas
- Respuesta en la BD: `[[4, 27]]`
- SQL gold: `select count(*),sum(cited_by) from Article where ismainarticle=1 and year between 2007 and 2012`

### Q14. El artículo dice que 2015 tuvo 5 artículos y 104 citaciones. ¿Qué muestra la base de datos?
- Sección del artículo: Periodo 2013–2019
- Lo que dice el artículo: 2015: 5 artículos, 104 citas
- Respuesta en la BD: `[[4, 66]]`
- SQL gold: `select count(*),sum(cited_by) from Article where ismainarticle=1 and year=2015`

### Q15. El artículo señala que los artículos de 2014 sumaron 78 citaciones. ¿Se confirma en la base de datos?
- Sección del artículo: Periodo 2013–2019
- Lo que dice el artículo: 2014: 78 citas
- Respuesta en la BD: `[[78]]`
- SQL gold: `select sum(cited_by) from Article where ismainarticle=1 and year=2014`

### Q16. El artículo reporta que Scopus registró 12 artículos en 2024. ¿Cuántos hay en la base de datos?
- Sección del artículo: Scientific Annual Production
- Lo que dice el artículo: Scopus 2024: 12 artículos
- Respuesta en la BD: `[[13]]`
- SQL gold: `select count(*) from Article where ismainarticle=1 and year=2024`

### Q17. El artículo afirma que China tiene 21 artículos (22,34 % de la producción). ¿Qué muestra la base de datos para China?
- Sección del artículo: Country Analysis / Tabla II
- Lo que dice el artículo: China: 21 artículos (22,34 %)
- Respuesta en la BD: `[[17]]`
- SQL gold: `select count(distinct SR) from Affiliation where Country='CHINA' and SR in (select SR from Article where ismainarticle=1)`

### Q18. El artículo dice que el artículo de Azam et al. es el más citado con términos agrovoltaico/fotovoltaico, con 68 citas y publicado en 2024. ¿Qué dice la base de datos sobre ese artículo?
- Sección del artículo: Periodo 2020–2025
- Lo que dice el artículo: Azam et al.: 68 citas, publicado en 2024 (Egipto); la referencia lo fecha en 2020
- Respuesta en la BD: `[["THERMAL ANALYSIS OF PV SYSTEM AND SOLAR COLLECTOR INTEGRATED WITH GREENHOUSE DRYER FOR DRYING TOMATOES", 2020, 69]]`
- SQL gold: `select title,year,cited_by from Article where ismainarticle=1 and title like 'THERMAL ANALYSIS OF PV SYSTEM%'`

### Q19. La Tabla III del artículo da 3 artículos de Journal of Food Process Engineering en Scopus, mientras el texto dice 2. ¿Cuántos hay en la base de datos?
- Sección del artículo: Tabla III y texto
- Lo que dice el artículo: JFPE: 3 en Scopus (tabla) / 2 (texto)
- Respuesta en la BD: `[[2]]`
- SQL gold: `select count(*) from Article where ismainarticle=1 and source_title='J FOOD PROCESS ENG'`

### Q20. El artículo cita a Hassanein et al. (2015) con 38 citaciones. ¿Existe ese artículo en la base de datos?
- Sección del artículo: Periodo 2013–2019
- Lo que dice el artículo: Hassanein 2015: 38 citas, Q1
- Respuesta en la BD: `[[0]]`
- SQL gold: `select count(*) from Article where lower(doi) like '%10.1016/j.ecoleng.2015.05.010%'`

### Q21. El artículo afirma que Alemania tiene tres artículos recientes (2022, 2023 y 2024) dedicados explícitamente a agrovoltaicos. ¿Qué artículos alemanes de 2022 en adelante hay en la base de datos?
- Sección del artículo: Country Analysis
- Lo que dice el artículo: Alemania: 3 artículos recientes (2022, 2023, 2024) sobre agrovoltaicos
- Respuesta en la BD: `[[2022, "PERFORMANCE ANALYSIS OF A SPECTRALLY SELECTIVE SOLAR CELL USING PV-GIS DATA"], [2023, "ESTABLISHMENT OF A RESEARCH FOCUS ON RESILIENT SUSTAINABLE CLIMATE NEUTRAL AGRICULTURAL PRODUCTION—RESILIENT FARMING INITIATIVE"], [2024, "SUSTAINABLE FAECAL SLUDGE MANAGEMENT IN INTERNALLY DISPLACED PERSONS (IDPS) SETTLEMENTS IN TROPICAL CLIMATE: A REVIEW"], [2024, "OPTIMAL DESIGN OF A SECTOR-COUPLED RENEWABLE METHANOL PRODUCTION AMID POLITICAL GOALS AND EXPECTED CONFLICTS: COSTS VS. LAND USE"]]`
- SQL gold: `select year,title from Article where ismainarticle=1 and year>=2022 and SR in (select SR from Affiliation where Country='GERMANY') order by year`

### Q22. El artículo indica que Tailandia tiene 5 artículos. ¿Es correcto según la base de datos?
- Sección del artículo: Tabla II
- Lo que dice el artículo: Tailandia: 5 artículos (5,32 %)
- Respuesta en la BD: `[[5]]`
- SQL gold: `select count(distinct SR) from Affiliation where Country='THAILAND' and SR in (select SR from Article where ismainarticle=1)`


## RAG puro (Q23–Q32)

### Q23. ¿Qué estudió el artículo de Chen et al. (2014) sobre compostaje de lodos y qué concluyó?
- Sección del artículo: Periodo 2013–2019
- Respuesta esperada: Evaluó el uso de energía solar (invernadero/reactor solar pasivo) para acelerar el compostaje de lodos de depuración: la radiación elevó la temperatura, mejoró la deshidratación, la estabilización y la reducción de patógenos, y dio un compost apto como fertilizante agrícola.
- Fuente en corpus: `CHEN Y, 2014, WASTE MANAGE` (en corpus: True)
- Nota: El abstract compara 3 reactores (ordinario, invernadero, solar) y reporta >55 °C durante más de 3 días en el solar.

### Q24. ¿Qué sistema analiza el estudio del secador de invernadero híbrido para tomates y cómo funciona?
- Sección del artículo: Periodo 2020–2025
- Respuesta esperada: Un secador de invernadero híbrido que combina un colector solar térmico y un sistema fotovoltaico: la energía térmica calienta el aire y los paneles alimentan ventiladores (convección forzada), acelerando el secado sin energía externa.
- Fuente en corpus: `AZAM MM, 2020, ENERGY` (en corpus: True)

### Q25. ¿Qué propone el estudio de Bangladesh y Japón sobre azoteas con paneles solares y acuaponía?
- Sección del artículo: Country Analysis
- Respuesta esperada: Un modelo de uso dual del espacio: paneles solares en azoteas generan electricidad mientras bajo su sombra se desarrolla un sistema acuapónico (cultivo de plantas y cría de peces en circuito cerrado), mejorando el uso del suelo urbano, reduciendo costos energéticos y aumentando la producción de alimentos.
- Fuente en corpus: `RONY JH, 2024, J FINANC` (en corpus: True)
- Nota: El abstract lo sitúa en Dhaka y menciona 8 paneles de 500 W y recolección de agua lluvia.

### Q26. ¿Qué herramienta desarrolla el estudio de colaboración entre Italia y Suiza para evaluar sistemas agrovoltaicos?
- Sección del artículo: Country Analysis
- Respuesta esperada: Una herramienta de simulación que evalúa diseños de sistemas agrovoltaicos considerando generación eléctrica e impacto sobre los cultivos, con indicadores (irradiancia, rendimiento agrícola, producción de energía) y análisis multicriterio para comparar configuraciones.
- Fuente en corpus: `BELLONE Y, 2024, ` (en corpus: True)
- Nota: El artículo dice 2020; la BD lo registra en 2024 (error del Word).

### Q27. ¿Qué tratamiento aplica el estudio sobre digestato de estiércol y por qué el artículo lo considera tangencial a los agrovoltaicos?
- Sección del artículo: Author Analysis
- Respuesta esperada: Aplica secado solar combinado con acidificación al digestato para reducir su contenido de agua y las emisiones gaseosas, produciendo fertilizantes; es valorización de residuos y no integra producción agrícola con generación eléctrica.
- Fuente en corpus: `MOREY L, 2023, J ENVIRON MANAGE` (en corpus: True)

### Q28. ¿Qué diseña el estudio del secador solar de invernadero publicado en IPEC 2023?
- Sección del artículo: Author Analysis
- Respuesta esperada: Un sistema de control para un secador solar de invernadero, orientado a la eficiencia térmica y al diseño del secado (reduce el riesgo para trabajadores por altas temperaturas y da flexibilidad); no integra producción simultánea de electricidad y alimentos.
- Fuente en corpus: `BASILIO GA, 2023, J FINANC` (en corpus: True)
- Nota: Contexto de Filipinas en el abstract.

### Q29. ¿Qué sistema evaluó el artículo de Meng et al. (2009) y con qué fin?
- Sección del artículo: Periodo de baja producción
- Respuesta esperada: Un sistema integrado de invernadero y calentador solar para calentar y mantener la temperatura del digestor en la digestión anaerobia de lodos activados excedentes, aumentando la temperatura y la producción de biogás según la estación.
- Fuente en corpus: `MENG C, 2009, ` (en corpus: True)
- Nota: El artículo lo cita como de bajo impacto (13 citas).

### Q30. ¿De qué trata el artículo sobre secado solar de mangos en África occidental francófona?
- Sección del artículo: Periodo de baja producción
- Respuesta esperada: Secado solar de mangos para reducir las pérdidas poscosecha y conservar beta-caroteno (provitamina A), frente a la deficiencia de vitamina A en niños: 3,75 t de mango fresco rindieron 360 kg de mango seco.
- Fuente en corpus: `RANKINS J, 2008, J AM OPTOM ASSOC` (en corpus: True)
- Nota: El artículo lo cita como de bajo impacto (13 citas).

### Q31. ¿Qué proponen Hassanein et al. (2015) sobre biodigestores subterráneos y energía solar?
- Sección del artículo: Periodo 2013–2019
- Respuesta esperada: Según el Word: un invernadero construido sobre biodigestores subterráneos que aprovecha energía solar térmica para calentarlos sin combustibles fósiles, validado con simulación y experimento. PERO este artículo NO está en el corpus Scopus: el sistema debe decir que no lo encuentra.
- Fuente en corpus: `—` (en corpus: False)
- Nota: Pregunta trampa: mide si el sistema inventa. Solo indexado en WoS.

### Q32. ¿Qué tipos de productos agrícolas se secan con energía solar en los artículos del corpus?
- Sección del artículo: Periodo 2020–2025
- Respuesta esperada: Según el Word, la mayoría de trabajos de 2020–2025 implementan secadores solares para productos agrícolas o bioproductos. En el corpus hay 26 artículos con 'dry/drying' en el título; entre ellos tomate, cacao, mango, amla, pescado, residuos de cultivos y lodos.
- Fuente en corpus: `—` (en corpus: None)
- Nota: Pregunta temática: no hay una única fuente.
