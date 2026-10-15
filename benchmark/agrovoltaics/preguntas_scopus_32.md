# Dataset Scopus — 32 preguntas (agrovoltaicos)

Todas las respuestas esperadas salen del corpus **Scopus** (66 artículos principales), que es lo que consulta el agente. La columna «Relación con el Word» es solo referencia.


## SQL puro (Q01–Q12)

### Q01. ¿Cuántos artículos principales hay en el corpus?
- **Respuesta esperada:** 66 artículos principales.
- Resultado en la BD: `[[66]]`
- SQL de referencia: `select count(*) from Article where ismainarticle=1`
- Relación con el Word: El Word reporta 77 porque une Scopus y WoS.

### Q02. ¿En qué año se publicaron más artículos y cuántos?
- **Respuesta esperada:** 2024, con 13 artículos.
- Resultado en la BD: `[[2024, 13]]`
- SQL de referencia: `select year,count(*) n from Article where ismainarticle=1 group by year order by n desc limit 1`
- Relación con el Word: El Word: 2024 es el año más productivo (Scopus 12).

### Q03. ¿Cuántos artículos se publicaron entre 2020 y 2025?
- **Respuesta esperada:** 45 artículos.
- Resultado en la BD: `[[45]]`
- SQL de referencia: `select count(*) from Article where ismainarticle=1 and year between 2020 and 2025`
- Relación con el Word: El Word: 49 en el periodo 2020–2025 (Scopus + WoS).

### Q04. ¿Qué país aparece en más artículos y en cuántos?
- **Respuesta esperada:** China, en 17 artículos.
- Resultado en la BD: `[["CHINA", 17]]`
- SQL de referencia: `select Country,count(distinct SR) n from Affiliation where SR in (select SR from Article where ismainarticle=1) group by Country order by n desc limit 1`
- Relación con el Word: El Word: China lidera con 21 (Scopus + WoS).

### Q05. ¿En cuántos artículos participa al menos una institución de Alemania?
- **Respuesta esperada:** 7 artículos.
- Resultado en la BD: `[[7]]`
- SQL de referencia: `select count(distinct SR) from Affiliation where Country='GERMANY' and SR in (select SR from Article where ismainarticle=1)`
- Relación con el Word: El Word: 8 (Scopus + WoS).

### Q06. ¿En cuántos artículos participa al menos una institución de India?
- **Respuesta esperada:** 8 artículos.
- Resultado en la BD: `[[8]]`
- SQL de referencia: `select count(distinct SR) from Affiliation where Country='INDIA' and SR in (select SR from Article where ismainarticle=1)`
- Relación con el Word: El Word: 10 (Scopus + WoS).

### Q07. Entre los artículos que tienen revista registrada, ¿qué revista concentra más artículos y cuántos?
- **Respuesta esperada:** Acta Horticulturae (ACTA HORTIC), con 4 artículos.
- Resultado en la BD: `[["ACTA HORTIC", 4]]`
- SQL de referencia: `select source_title,count(*) n from Article where ismainarticle=1 and source_title is not null group by source_title order by n desc limit 1`
- Relación con el Word: Coincide con el Word. Ojo: 26 artículos no tienen revista registrada (source_title vacío).

### Q08. ¿Cuántos artículos del corpus se publicaron en AIP Conference Proceedings?
- **Respuesta esperada:** 3 artículos.
- Resultado en la BD: `[[3]]`
- SQL de referencia: `select count(*) from Article where ismainarticle=1 and source_title='AIP CONF PROC'`
- Relación con el Word: Coincide con el Word.

### Q09. ¿Cuántos artículos tiene Carsten Agert en el corpus y cuántas citas suman?
- **Respuesta esperada:** 3 artículos con 38 citas en total.
- Resultado en la BD: `[[3, 38]]`
- SQL de referencia: `select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR where aa.AuthorID like 'C_AGERT%' and a.ismainarticle=1`
- Relación con el Word: Coincide con la Tabla IV del Word.

### Q10. ¿Cuántos artículos tiene Jason A. Carlyon en el corpus y cuántas citas suman?
- **Respuesta esperada:** 2 artículos con 26 citas en total.
- Resultado en la BD: `[[2, 26]]`
- SQL de referencia: `select count(distinct a.SR),sum(a.cited_by) from ArticleAuthor aa join Article a on a.SR=aa.SR where aa.AuthorID like '%CARLYON%' and a.ismainarticle=1`
- Relación con el Word: Coincide con la Tabla IV del Word.

### Q11. ¿Qué autores tienen 3 o más artículos en el corpus?
- **Respuesta esperada:** 5 autores, todos con 3 artículos: Carsten Agert, Kai Gehrke, Martin Vehse, Nils Neugebohrn y Norbert Osterthun.
- Resultado en la BD: `[["C., AGERT, CARSTEN", 3], ["K., GEHRKE, KAI", 3], ["M., VEHSE, MARTIN", 3], ["N., NEUGEBOHRN, NILS", 3], ["N., OSTERTHUN, NORBERT", 3]]`
- SQL de referencia: `select au.AuthorName,count(distinct aa.SR) n from ArticleAuthor aa join Author au on au.AuthorID=aa.AuthorID where aa.SR in (select SR from Article where ismainarticle=1) group by aa.AuthorID having n>=3 order by n desc, au.AuthorName`
- Relación con el Word: El Word dice que ocho autores tienen tres publicaciones (Scopus + WoS).

### Q12. ¿Cuántas citas suman los artículos publicados en 2014?
- **Respuesta esperada:** 78 citas.
- Resultado en la BD: `[[78]]`
- SQL de referencia: `select sum(cited_by) from Article where ismainarticle=1 and year=2014`
- Relación con el Word: Coincide con el Word.


## Híbridas: SQL + contenido (Q13–Q22)

### Q13. ¿Cuál es el artículo más citado del corpus y de qué trata?
- **Respuesta esperada:** «Powering agriculture: present status, future potential, and challenges of renewable energy applications» (Rahman et al., 2022, Renewable Energy), con 165 citas. Revisa el uso de energías renovables en la agricultura para reducir la dependencia de combustibles fósiles (secado de grano, fertilizantes, maquinaria, electricidad) y sus emisiones.
- Resultado en la BD: `[["RAHMAN MM, 2022, RENEW ENERGY", 2022, 165, "POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS"]]`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and 1=1 order by cited_by desc limit 1`
- Artículo(s) fuente: `RAHMAN MM, 2022, RENEW ENERGY`
- Relación con el Word: El Word no lo menciona.

### Q14. ¿Cuál fue el artículo más citado publicado en 2014 y qué estudió?
- **Respuesta esperada:** Chen et al. (2014, Waste Management), con 59 citas: uso de energía solar en el compostaje de lodos de depuración; comparó reactores ordinario, de invernadero y solar, y el solar dio calor más estable (más de 55 °C durante más de 3 días).
- Resultado en la BD: `[["CHEN Y, 2014, WASTE MANAGE", 2014, 59, "UTILIZATION OF SOLAR ENERGY IN SEWAGE SLUDGE COMPOSTING: FERTILIZER EFFECT AND APPLICATION"]]`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and year=2014 order by cited_by desc limit 1`
- Artículo(s) fuente: `CHEN Y, 2014, WASTE MANAGE`
- Relación con el Word: El Word atribuye a Chen et al. el impulso de las citas de 2014.

### Q15. ¿Cuál fue el artículo más citado publicado en 2015 y de qué trata?
- **Respuesta esperada:** Fasahati et al. (2015, Energy), con 38 citas: impacto económico, energético y ambiental de la tecnología de deshidratación de alcohol en la producción de biocombustible a partir de algas pardas.
- Resultado en la BD: `[["FASAHATI P, 2015, ENERGY", 2015, 38, "ECONOMIC, ENERGY, AND ENVIRONMENTAL IMPACTS OF ALCOHOL DEHYDRATION TECHNOLOGY ON BIOFUEL PRODUCTION FROM BROWN ALGAE"]]`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and year=2015 order by cited_by desc limit 1`
- Artículo(s) fuente: `FASAHATI P, 2015, ENERGY`
- Relación con el Word: El Word dice que el más citado de 2015 es Hassanein et al., que solo está en WoS.

### Q16. Entre los artículos con 'photovoltaic', 'agrivoltaic' o 'PV' en el título, ¿cuál es el más citado y qué sistema analiza?
- **Respuesta esperada:** Azam et al. (2020, Energy), con 69 citas: un secador de invernadero híbrido para tomates que integra un sistema fotovoltaico y un colector solar.
- Resultado en la BD: `[["AZAM MM, 2020, ENERGY", 2020, 69, "THERMAL ANALYSIS OF PV SYSTEM AND SOLAR COLLECTOR INTEGRATED WITH GREENHOUSE DRYER FOR DRYING TOMATOES"]]`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and (title like '%PHOTOVOLT%' or title like '%AGRIVOLT%' or title like '%AGROVOLT%' or title like '% PV %') order by cited_by desc limit 1`
- Artículo(s) fuente: `AZAM MM, 2020, ENERGY`
- Relación con el Word: El Word lo señala como el más citado con esos términos (pero le pone 68 citas y año 2024).

### Q17. ¿Cuáles fueron los artículos más citados publicados entre 2007 y 2012 y de qué tratan?
- **Respuesta esperada:** Dos artículos con 13 citas cada uno: Meng et al. (2009), un sistema integrado de invernadero y calentador solar para la digestión anaerobia de lodos activados; y Rankins et al. (2008), el secado solar de mangos para conservar la provitamina A en África occidental francófona.
- Resultado en la BD: `[["MENG C, 2009, ", 2009, 13, "INTEGRATED SYSTEM OF GREENHOUSE AND SOLAR HEATER FOR ANAEROBIC DIGESTION OF EXCESS ACTIVATED SLUDGE"], ["RANKINS J, 2008, J AM OPTOM ASSOC", 2008, 13, "SOLAR DRYING OF MANGOES: PRESERVATION OF AN IMPORTANT SOURCE OF VITAMIN A IN FRENCH-SPEAKING WEST AFRICA"]]`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and year between 2007 and 2012 order by cited_by desc limit 2`
- Artículo(s) fuente: `MENG C, 2009, `, `RANKINS J, 2008, J AM OPTOM ASSOC`
- Relación con el Word: Coincide con el Word, que cita ambos DOI con 13 citas.

### Q18. ¿Qué artículos tienen autores de Bangladesh y de qué tratan?
- **Respuesta esperada:** 3 artículos: Rahman et al. (2022), revisión de energías renovables en agricultura (165 citas); Rana et al. (2023), acuicultura marina y un secador de pescado inteligente basado en IoT; y Rony et al. (2024), agrovoltaica más acuaponía en azoteas urbanas de Dhaka.
- Resultado en la BD: `[["RAHMAN MM, 2022, RENEW ENERGY", 2022, 165, "POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS"], ["RANA M, 2023, DESALIN WATER TREAT", 2023, 2, "MARINE WATER AQUACULTURE AND AN IOT-BASED SMART FISH DRYER OF THE FUTURE: A SUSTAINABLE ENVIRONMENTAL APPROACH"], ["RONY JH, 2024, J FINANC", 2024, 0, "INTEGRATED AGRIVOLTAICS AND AQUAPONIC SYSTEM F`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and SR in (select SR from Affiliation where Country='BANGLADESH') order by cited_by desc`
- Artículo(s) fuente: `RAHMAN MM, 2022, RENEW ENERGY`, `RANA M, 2023, DESALIN WATER TREAT`, `RONY JH, 2024, J FINANC`
- Relación con el Word: El Word destaca a Bangladesh como el país con más colaboración.

### Q19. ¿Qué artículos publicó el grupo de Carsten Agert y de qué tratan?
- **Respuesta esperada:** 3 artículos (Osterthun et al., 2021–2022), todos sobre celdas solares espectralmente selectivas que combinan fotovoltaica y fotosíntesis: celdas ultradelgadas de germanio (30 citas), su efecto en el crecimiento de microalgas en fotobiorreactores (8 citas) y su desempeño con datos PV-GIS (0 citas).
- Resultado en la BD: `[["OSTERTHUN N, 2021, OPT EXPRESS", 2021, 30, "SPECTRAL ENGINEERING OF ULTRATHIN GERMANIUM SOLAR CELLS FOR COMBINED PHOTOVOLTAIC AND PHOTOSYNTHESIS"], ["OSTERTHUN N, 2021, AIP CONF PROC", 2021, 8, "INFLUENCE OF SPECTRALLY SELECTIVE SOLAR CELLS ON MICROALGAE GROWTH IN PHOTO-BIOREACTORS"], ["OSTERTHUN N, 2022, AIP CONF PROC", 2022, 0, "PERFORMANCE ANALYSIS OF A SPECTRALLY SELECTIVE SOLAR CELL USING `
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and SR in (select SR from ArticleAuthor where AuthorID like 'C_AGERT%') order by cited_by desc`
- Artículo(s) fuente: `OSTERTHUN N, 2021, OPT EXPRESS`, `OSTERTHUN N, 2021, AIP CONF PROC`, `OSTERTHUN N, 2022, AIP CONF PROC`
- Relación con el Word: La Tabla IV del Word sitúa a Agert y su grupo en el núcleo de autores.

### Q20. ¿Qué artículos publicó Jason A. Carlyon y tienen relación con los agrovoltaicos?
- **Respuesta esperada:** 2 artículos sobre la bacteria Anaplasma phagocytophilum (Read et al., 2022, 16 citas; Oki et al., 2015, 10 citas). Son de microbiología y no tienen relación con los agrovoltaicos.
- Resultado en la BD: `[["READ CB, 2022, MBIO", 2022, 16, "THE OBLIGATE INTRACELLULAR BACTERIAL PATHOGEN ANAPLASMA PHAGOCYTOPHILUM EXPLOITS HOST CELL MULTIVESICULAR BODY BIOGENESIS FOR PROLIFERATION AND DISSEMINATION"], ["OKI AT, 2015, MICROBES INFECT", 2015, 10, "DENDRIMER-ENABLED TRANSFORMATION OF ANAPLASMA PHAGOCYTOPHILUM"]]`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and SR in (select SR from ArticleAuthor where AuthorID like '%CARLYON%') order by cited_by desc`
- Artículo(s) fuente: `READ CB, 2022, MBIO`, `OKI AT, 2015, MICROBES INFECT`
- Relación con el Word: El Word lo ubica en una comunidad de autores ajena al tema.

### Q21. ¿Qué artículos publicó Acta Horticulturae en el corpus y de qué tratan?
- **Respuesta esperada:** 4 artículos: arreglos fotovoltaicos sobre un huerto de perales (Singh R., 2024); pepino con solución nutritiva oxigenada en invernaderos (Singh P., 2021); temperatura y humedad en un invernadero plástico asimétrico (Hu, 2018); estrategias pre y poscosecha para compuestos bioactivos (Gil, 2015).
- Resultado en la BD: `[["GIL MI, 2015, ACTA HORTIC", 2015, 3, "PRE- AND POSTHARVEST STRATEGIES TO ENHANCE BIOACTIVE CONSTITUENTS OF FRUITS AND VEGETABLES"], ["SINGH R, 2024, ACTA HORTIC", 2024, 0, "EFFECTS OF ABOVE-CANOPY PHOTOVOLTAIC ARRAYS ON TRANSPIRATION AND ENERGY PRODUCTION IN A PEAR ORCHARD"], ["SINGH P, 2021, ACTA HORTIC", 2021, 0, "RESPONSE OF CUCUMBER PLANTS TO OXYGEN-ENRICHED NUTRIENT SOLUTION UNDER DIFFEREN`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and source_title='ACTA HORTIC' order by cited_by desc`
- Artículo(s) fuente: `GIL MI, 2015, ACTA HORTIC`, `SINGH R, 2024, ACTA HORTIC`, `SINGH P, 2021, ACTA HORTIC`, `HU X, 2018, ACTA HORTIC`
- Relación con el Word: El Word la señala como la revista con más artículos, de bajo impacto.

### Q22. ¿Qué artículos con participación de Alemania se publicaron desde 2022 y cuáles tratan sobre agrovoltaicos?
- **Respuesta esperada:** 4 artículos. Solo uno trata de agrovoltaica: el desempeño de una celda solar espectralmente selectiva con datos PV-GIS (Osterthun, 2022). Los otros tratan de producción agrícola resiliente y climáticamente neutra (Uhl, 2023), manejo de lodos fecales en asentamientos de desplazados (Orugba, 2024) y producción de metanol renovable (Svitnič, 2024).
- Resultado en la BD: `[["SVITNIČ T, 2024, ", 2024, 9, "OPTIMAL DESIGN OF A SECTOR-COUPLED RENEWABLE METHANOL PRODUCTION AMID POLITICAL GOALS AND EXPECTED CONFLICTS: COSTS VS. LAND USE"], ["ORUGBA OH, 2024, ", 2024, 1, "SUSTAINABLE FAECAL SLUDGE MANAGEMENT IN INTERNALLY DISPLACED PERSONS (IDPS) SETTLEMENTS IN TROPICAL CLIMATE: A REVIEW"], ["UHL A, 2023, ", 2023, 1, "ESTABLISHMENT OF A RESEARCH FOCUS ON RESILIENT SUSTAIN`
- SQL de referencia: `select SR,year,cited_by,title from Article where ismainarticle=1 and year>=2022 and SR in (select SR from Affiliation where Country='GERMANY') order by cited_by desc`
- Artículo(s) fuente: `SVITNIČ T, 2024, `, `ORUGBA OH, 2024, `, `UHL A, 2023, `, `OSTERTHUN N, 2022, AIP CONF PROC`
- Relación con el Word: El Word dice que Alemania tiene tres artículos recientes (2022–2024) dedicados a agrovoltaicos.


## RAG puro (Q23–Q32)

### Q23. ¿Qué estudio del corpus usa energía solar para compostar lodos de depuración y qué encontró?
- **Respuesta esperada:** Chen et al. (2014) compararon tres reactores (ordinario, de invernadero y solar) para compostar lodos municipales: el reactor solar dio calor más estable y fue el único que mantuvo más de 55 °C por más de 3 días, mejorando la calidad del compost como fertilizante.
- Artículo(s) fuente: `CHEN Y, 2014, WASTE MANAGE`
- Relación con el Word: Descrito en el Word (periodo 2013–2019).

### Q24. ¿Cómo funciona el secador de invernadero híbrido para tomates estudiado en el corpus?
- **Respuesta esperada:** Es un secador de invernadero autónomo de convección forzada que integra un sistema fotovoltaico y un colector solar; se evaluó con un modelo térmico y distintos pretratamientos del tomate (el escaldado 15 min aceleró el secado), comparado con el secado al sol.
- Artículo(s) fuente: `AZAM MM, 2020, ENERGY`
- Relación con el Word: Descrito en el Word (periodo 2020–2025).

### Q25. ¿Qué propone el estudio sobre agrovoltaica y acuaponía en azoteas urbanas?
- **Respuesta esperada:** Integrar paneles solares (8 de 500 W, unos 4.000 W) y un sistema acuapónico (peces y plantas sin suelo en circuito cerrado) en azoteas de Dhaka, Bangladesh, con recolección de agua lluvia, para producir energía y alimentos donde falta suelo.
- Artículo(s) fuente: `RONY JH, 2024, J FINANC`
- Relación con el Word: Descrito en el Word (colaboración Bangladesh–Japón).

### Q26. ¿Qué herramienta del corpus sirve para comparar y elegir configuraciones de sistemas agrovoltaicos?
- **Respuesta esperada:** Un marco basado en simulación que combina indicadores (proporción de cultivo, energía por hectárea, rendimiento energético específico, eficiencia del agua, inversión inicial) en un análisis multicriterio, y clasifica cuatro configuraciones (vertical, monoaxial interespaciada, monoaxial elevada y biaxial elevada) según el entorno.
- Artículo(s) fuente: `BELLONE Y, 2024, `
- Relación con el Word: Descrito en el Word (Italia–Suiza), que lo fecha en 2020; en el corpus es de 2024.

### Q27. ¿Qué tratamiento se aplica al digestato de estiércol en el estudio de secado solar del corpus?
- **Respuesta esperada:** Secado solar combinado con acidificación del digestato y de su fracción sólida, para reducir el contenido de agua y las emisiones gaseosas; el digestato acidificado conservó más nitrógeno.
- Artículo(s) fuente: `MOREY L, 2023, J ENVIRON MANAGE`
- Relación con el Word: Descrito en el Word (comunidad naranja).

### Q28. ¿Qué diseña el estudio sobre el secador solar de invernadero en Filipinas?
- **Respuesta esperada:** Un sistema de control para un secador solar de invernadero, que reduce el riesgo de los trabajadores expuestos a altas temperaturas y da más flexibilidad al secado de productos agrícolas.
- Artículo(s) fuente: `BASILIO GA, 2023, J FINANC`
- Relación con el Word: Descrito en el Word (comunidad verde).

### Q29. ¿Qué sistema se usó para calentar la digestión anaerobia de lodos activados excedentes?
- **Respuesta esperada:** Un sistema integrado de invernadero y calentador solar que mantuvo la temperatura de digestión mesofílica y termofílica, elevándola entre unos 10 y 28 °C según la estación y aumentando la producción de biogás.
- Artículo(s) fuente: `MENG C, 2009, `
- Relación con el Word: El Word solo cita su DOI y 13 citas.

### Q30. ¿Qué estudio del corpus seca mangos con energía solar y con qué propósito?
- **Respuesta esperada:** Rankins et al. (2008): secado solar de 3,75 t de mango fresco (360 kg secos) para reducir las pérdidas poscosecha y conservar beta-caroteno frente a la deficiencia de vitamina A en África occidental francófona.
- Artículo(s) fuente: `RANKINS J, 2008, J AM OPTOM ASSOC`
- Relación con el Word: El Word solo cita su DOI y 13 citas.

### Q31. ¿Qué tipo de celda solar se propone en el corpus para combinar fotovoltaica y fotosíntesis?
- **Respuesta esperada:** Una celda solar espectralmente selectiva de germanio ultradelgado, cuya transmisión se ajusta al espectro de absorción de la clorofila, para usarla en sistemas agrovoltaicos, invernaderos y fotobiorreactores.
- Artículo(s) fuente: `OSTERTHUN N, 2021, OPT EXPRESS`
- Relación con el Word: El Word solo menciona a sus autores (grupo Agert).

### Q32. ¿Qué tipos de productos agrícolas se secan con energía solar en los artículos del corpus?
- **Respuesta esperada:** Entre otros: tomate (y pasta y hojuelas de tomate), cacao, mango, amla, pescado, residuos de cultivos, digestato y lodos. 26 artículos del corpus tienen 'dry' o 'drying' en el título.
- Relación con el Word: El Word dice que la mayoría de trabajos de 2020–2025 son secadores solares.
