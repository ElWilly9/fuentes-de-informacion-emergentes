# Prueba Capa 5 — sesión Agrovoltaics

Corrida: 2026-10-14 19:54

## ¿Cuáles son los frentes de investigación del corpus y cuáles son emergentes?

**Ruta:** `community` (esperada `community`) · 87.5 s

**Respuesta:**

Los frentes de investigación del corpus son:

1. **Frente 1 [EMERGENTE]**: Comprende 21 artículos con un total de 322 citas. Este frente se centra en temas como el secado, los invernaderos solares y la almacenamiento de calor. Ha crecido significativamente en los últimos años, con un crecimiento anual del +25 %.

2. **Frente 2 [EMERGENTE]**: Incluye 7 artículos y 218 citas. Los temas principales son la reflexión, la sombra, los combustibles fósiles y el procesamiento de alimentos. Este frente ha experimentado un crecimiento significativo del +58 % anual en los últimos 3 años.

3. **Frente 3 [EMERGENTE]**: Contiene 5 artículos y 32 citas. Se centra en la producción de biogás, la digestión anaeróbica y los fertilizantes. Ha mostrado un crecimiento significativo del +71 % anual en los últimos 3 años.

4. **Frente 4 [SEÑAL DÉBIL]**: Incluye 3 artículos y 32 citas. Los temas son la anaplasmosis, la biotransformación y la microbiología. Aunque ha crecido más que el corpus, esta tendencia no es significativa estadísticamente.

Los temas emergentes del corpus son:

1. **Tema 1 [EMERGENTE]**: GREENHOUSES, DRYING, SOLAR ENERGY, SOLAR DRYERS, AGRICULTURAL PRODUCTS, GREENHOUSE, SOLAR DRYING, PERFORMANCE. Este tema ha crecido significativamente con un crecimiento anual del +34 %.

2. **Tema 5 [EMERGENTE]**: FRUITS, ENERGY EFFICIENCY, SOLAR GREENHOUSE, DRYERS (EQUIPMENT), GREENHOUSE DRYER, LYCOPERSICON ESCULENTUM, PERFORMANCE ASSESSMENT, TOMATO. Este tema también ha mostrado un crecimiento significativo del +54 % anual.

Los temas no emergentes incluyen:

- **Tema 2**: ANAEROBIC DIGESTION, BIOGAS, GREENHOUSE GASES, SOLAR HEATING, SUSTAINABLE DEVELOPMENT, CARBON DIOXIDE, COSTS, BIOGAS PRODUCTION.
- **Tema 3**: AGRICULTURE, FERTILIZERS, ENERGY, GREENHOUSE GAS, FERMENTATION, FERTILIZER, GAS EMISSIONS, GREENHOUSE GAS EMISSIONS.
- **Tema 6**: FOOD PROCESSING, ENERGY CONSERVATION, FOOD PRESERVATION, FOOD TECHNOLOGY, HEATING, REFLECTION, TEMPERATURE PROFILE.

Estos temas no han mostrado un crecimiento significativo en los últimos años.

<details><summary>Análisis que recibió el LLM</summary>

```
MÉTODO: frentes de investigación = comunidades Louvain sobre la red de acoplamiento bibliográfico (dos artículos se unen si citan referencias en común). Temas = comunidades Louvain sobre la red de coocurrencia de palabras clave de autor. Emergente = crece más rápido que el corpus y tiene más peso en los últimos 3 años que el corpus.
CORPUS: 65 artículos (2007–2024), año medio 2019.9, 52 % en los últimos 3 años, crecimiento +22 %/año (significativo, p<0,05).
RED DE ACOPLAMIENTO: 40 de 65 artículos comparten referencias con otro (25 quedan aislados y no pertenecen a ningún frente); modularidad 0.605.

FRENTES DE INVESTIGACIÓN (acoplamiento):
Frente 1 [EMERGENTE]: 21 artículos, 322 citas en total.
  Palabras clave características: DRYING, GREENHOUSES, SOLAR DRYING, SOLAR DRYERS, GREENHOUSE SOLAR DRYER, HEAT STORAGE
  Tendencia: 21 artículos (2008–2024), año medio 2020.3, 57 % en los últimos 3 años, crecimiento +25 %/año (significativo, p<0,05)
  Ubicación en el Tree of Science: trunk: 11, branch_1: 4, branch_3: 3, branch_6: 2, branch_7: 1
  Artículos más citados:
    - THERMAL ANALYSIS OF PV SYSTEM AND SOLAR COLLECTOR INTEGRATED WITH GREENHOUSE DRYER FOR DRYING TOMATOES (2020, 69 citas)
    - UTILIZATION OF SOLAR ENERGY IN SEWAGE SLUDGE COMPOSTING: FERTILIZER EFFECT AND APPLICATION (2014, 59 citas)
    - ECONOMIC, ENERGY, AND ENVIRONMENTAL IMPACTS OF ALCOHOL DEHYDRATION TECHNOLOGY ON BIOFUEL PRODUCTION FROM BROWN ALGAE (2015, 38 citas)
Frente 2 [EMERGENTE]: 7 artículos, 218 citas en total.
  Palabras clave características: REFLECTION, SHADING, FOSSIL FUELS, FOOD PROCESSING
  Tendencia: 7 artículos (2021–2024), año medio 2022.3, 71 % en los últimos 3 años, crecimiento +58 %/año (significativo, p<0,05)
  Ubicación en el Tree of Science: trunk: 5, branch_2: 2
  Artículos más citados:
    - POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS (2022, 165 citas)
    - SPECTRAL ENGINEERING OF ULTRATHIN GERMANIUM SOLAR CELLS FOR COMBINED PHOTOVOLTAIC AND PHOTOSYNTHESIS (2021, 30 citas)
    - SIMULATION-BASED DECISION SUPPORT FOR AGRIVOLTAIC SYSTEMS (2024, 14 citas)
Frente 3 [EMERGENTE]: 5 artículos, 32 citas en total.
  Palabras clave características: BIOGAS, BIOGAS PRODUCTION, SOLAR RADIATION, ANAEROBIC DIGESTION, FERTILIZERS, GREENHOUSE GASES
  Tendencia: 5 artículos (2021–2024), año medio 2022.6, 80 % en los últimos 3 años, crecimiento +71 %/año (significativo, p<0,05)
  Ubicación en el Tree of Science: trunk: 4, branch_4: 1
  Artículos más citados:
    - OPTIMIZATION OF FEEDSTOCK AND INSULATING STRATEGIES TO ENHANCE BIOGAS PRODUCTION OF SOLAR-ASSISTED BIODIGESTER SYSTEM (2022, 12 citas)
    - OPTIMAL DESIGN OF A SECTOR-COUPLED RENEWABLE METHANOL PRODUCTION AMID POLITICAL GOALS AND EXPECTED CONFLICTS: COSTS VS. LAND USE (2024, 9 citas)
    - HYBRIDIZATION OF ANAEROBIC DIGESTION WITH SOLAR ENERGY: A SOLUTION FOR ISOLATED LIVESTOCK FARMS (2023, 8 citas)
Frente 4 [SEÑAL DÉBIL: crece más que el corpus pero sin significancia estadística]: 3 artículos, 32 citas en total.
  Palabras clave características: ANAPLASMA PHAGOCYTOPHILUM, ANAPLASMOSIS, BIOTRANSFORMATION, GENETICS, MICROBIOLOGY, REAL TIME POLYMERASE CHAIN REACTION
  Tendencia: 3 artículos (2015–2023), año medio 2020.0, 67 % en los últimos 3 años, crecimiento +22 %/año (no significativo, p=0.171)
  Artículos más citados:
    - THE OBLIGATE INTRACELLULAR BACTERIAL PATHOGEN ANAPLASMA PHAGOCYTOPHILUM EXPLOITS HOST CELL MULTIVESICULAR BODY BIOGENESIS FOR PROLIFERATION AND DISSEMINATION (2022, 16 citas)
    - DENDRIMER-ENABLED TRANSFORMATION OF ANAPLASMA PHAGOCYTOPHILUM (2015, 10 citas)
    - PHYSIOLOGICAL, PHOTOSYNTHETIC, AND TRANSCRIPTOMICS INSIGHTS INTO THE INFLUENCE OF SHADING ON LEAFY SWEET POTATO (2023, 6 citas)

TEMAS (palabras clave):
Tema 1 [EMERGENTE]: GREENHOUSES, DRYING, SOLAR ENERGY, SOLAR DRYERS, AGRICULTURAL PRODUCTS, GREENHOUSE, SOLAR DRYING, PERFORMANCE
  Tendencia: 20 artículos (2013–2024), año medio 2021.2, 70 % en los últimos 3 años, crecimiento +34 %/año (significativo, p<0,05)
Tema 2: ANAEROBIC DIGESTION, BIOGAS, GREENHOUSE GASES, SOLAR HEATING, SUSTAINABLE DEVELOPMENT, CARBON DIOXIDE, COSTS, BIOGAS PRODUCTION
  Tendencia: 14 artículos (2009–2024), año medio 2019.0, 43 % en los últimos 3 años, crecimiento +16 %/año (significativo, p<0,05)
Tema 3: AGRICULTURE, FERTILIZERS, ENERGY, GREENHOUSE GAS, FERMENTATION, FERTILIZER, GAS EMISSIONS, GREENHOUSE GAS EMISSIONS
  Tendencia: 10 artículos (2014–2023), año medio 2019.7, 50 % en los últimos 3 años, crecimiento +20 %/año (significativo, p<0,05)
Tema 5: FRUITS, ENERGY EFFICIENCY, SOLAR GREENHOUSE, DRYERS (EQUIPMENT), GREENHOUSE DRYER, LYCOPERSICON ESCULENTUM, PERFORMANCE ASSESSMENT, TOMATO
  Tendencia: 6 artículos (2020–2024), año medio 2022.2, 50 % en los últimos 3 años, crecimiento +54 %/año (significativo, p<0,05)
Tema 6: FOOD PROCESSING, ENERGY CONSERVATION, FOOD PRESERVATION, FOOD TECHNOLOGY, HEATING, REFLECTION, TEMPERATURE PROFILE
  Tendencia: 5 artículos (2007–2022), año medio 2015.6, 40 % en los últimos 3 años, crecimiento +0 %/año (no significativo, p=0.9656)
```
</details>

---

## ¿Qué temas principales aparecen según las palabras clave?

**Ruta:** `community` (esperada `community`) · 84.4 s

**Respuesta:**

Los temas principales que aparecen según las palabras clave son:

1. **Frentes de Investigación Emergentes**:
   - **Tema 1 [EMERGENTE]**: Involuciona la utilización de invernaderos, secado solar, energía solar, secadores solares, productos agrícolas y rendimiento. Este frente ha crecido significativamente en los últimos años.
   - **Tema 2 [EMERGENTE]**: Se centra en la digestión anaeróbica, producción de biogás, emisiones de gases de invernadero, calefacción solar, desarrollo sostenible y costos. Este frente también ha experimentado un crecimiento significativo.
   - **Tema 3 [EMERGENTE]**: Aborda la agricultura, fertilizantes, energía, emisiones de gas de invernadero, fermentación y emisiones de gases de invernadero. Este tema ha mostrado un crecimiento significativo en los últimos años.

2. **Temas Emergentes**:
   - **Tema 1 [EMERGENTE]**: GREENHOUSES (invernaderos), DRYING (secado), SOLAR ENERGY (energía solar), SOLAR DRYERS (secadores solares), AGRICULTURAL PRODUCTS (productos agrícolas), GREENHOUSE (invernadero), SOLAR DRYING (secado solar), PERFORMANCE (rendimiento).
   - **Tema 2**: ANAEROBIC DIGESTION (digestión anaeróbica), BIOGAS (biogás), GREENHOUSE GASES (gases de invernadero), SOLAR HEATING (calefacción solar), SUSTAINABLE DEVELOPMENT (desarrollo sostenible), CARBON DIOXIDE (dióxido de carbono), COSTS (costos), BIOGAS PRODUCTION (producción de biogás).
   - **Tema 3**: AGRICULTURE (agricultura), FERTILIZERS (fertilizantes), ENERGY (energía), GREENHOUSE GAS (gas de invernadero), FERMENTATION (fermentación), FERTILIZER (fertilizante), GAS EMISSIONS (emisiones de gas), GREENHOUSE GAS EMISSIONS (emisiones de gas de invernadero).
   - **Tema 5 [EMERGENTE]**: FRUITS (frutas), ENERGY EFFICIENCY (eficiencia energética), SOLAR GREENHOUSE (invernadero solar), DRYERS (secadores) (EQUIPMENT [equipo]), GREENHOUSE DRYER (secador de invernadero), LYCOPERSICON ESCULENTUM (tomate), PERFORMANCE ASSESSMENT (evaluación del rendimiento), TOMATO (tomate).
   - **Tema 6**: FOOD PROCESSING (procesamiento de alimentos), ENERGY CONSERVATION (conservación de energía), FOOD PRESERVATION (preservación de alimentos), FOOD TECHNOLOGY (tecnología de alimentos), HEATING (calefacción), REFLECTION (reflexión), TEMPERATURE PROFILE (perfil de temperatura).

Estos temas emergentes indican una creciente importancia en la investigación académica dentro del corpus analizado.

<details><summary>Análisis que recibió el LLM</summary>

```
MÉTODO: frentes de investigación = comunidades Louvain sobre la red de acoplamiento bibliográfico (dos artículos se unen si citan referencias en común). Temas = comunidades Louvain sobre la red de coocurrencia de palabras clave de autor. Emergente = crece más rápido que el corpus y tiene más peso en los últimos 3 años que el corpus.
CORPUS: 65 artículos (2007–2024), año medio 2019.9, 52 % en los últimos 3 años, crecimiento +22 %/año (significativo, p<0,05).
RED DE ACOPLAMIENTO: 40 de 65 artículos comparten referencias con otro (25 quedan aislados y no pertenecen a ningún frente); modularidad 0.605.

FRENTES DE INVESTIGACIÓN (acoplamiento):
Frente 1 [EMERGENTE]: 21 artículos, 322 citas en total.
  Palabras clave características: DRYING, GREENHOUSES, SOLAR DRYING, SOLAR DRYERS, GREENHOUSE SOLAR DRYER, HEAT STORAGE
  Tendencia: 21 artículos (2008–2024), año medio 2020.3, 57 % en los últimos 3 años, crecimiento +25 %/año (significativo, p<0,05)
  Ubicación en el Tree of Science: trunk: 11, branch_1: 4, branch_3: 3, branch_6: 2, branch_7: 1
  Artículos más citados:
    - THERMAL ANALYSIS OF PV SYSTEM AND SOLAR COLLECTOR INTEGRATED WITH GREENHOUSE DRYER FOR DRYING TOMATOES (2020, 69 citas)
    - UTILIZATION OF SOLAR ENERGY IN SEWAGE SLUDGE COMPOSTING: FERTILIZER EFFECT AND APPLICATION (2014, 59 citas)
    - ECONOMIC, ENERGY, AND ENVIRONMENTAL IMPACTS OF ALCOHOL DEHYDRATION TECHNOLOGY ON BIOFUEL PRODUCTION FROM BROWN ALGAE (2015, 38 citas)
Frente 2 [EMERGENTE]: 7 artículos, 218 citas en total.
  Palabras clave características: REFLECTION, SHADING, FOSSIL FUELS, FOOD PROCESSING
  Tendencia: 7 artículos (2021–2024), año medio 2022.3, 71 % en los últimos 3 años, crecimiento +58 %/año (significativo, p<0,05)
  Ubicación en el Tree of Science: trunk: 5, branch_2: 2
  Artículos más citados:
    - POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS (2022, 165 citas)
    - SPECTRAL ENGINEERING OF ULTRATHIN GERMANIUM SOLAR CELLS FOR COMBINED PHOTOVOLTAIC AND PHOTOSYNTHESIS (2021, 30 citas)
    - SIMULATION-BASED DECISION SUPPORT FOR AGRIVOLTAIC SYSTEMS (2024, 14 citas)
Frente 3 [EMERGENTE]: 5 artículos, 32 citas en total.
  Palabras clave características: BIOGAS, BIOGAS PRODUCTION, SOLAR RADIATION, ANAEROBIC DIGESTION, FERTILIZERS, GREENHOUSE GASES
  Tendencia: 5 artículos (2021–2024), año medio 2022.6, 80 % en los últimos 3 años, crecimiento +71 %/año (significativo, p<0,05)
  Ubicación en el Tree of Science: trunk: 4, branch_4: 1
  Artículos más citados:
    - OPTIMIZATION OF FEEDSTOCK AND INSULATING STRATEGIES TO ENHANCE BIOGAS PRODUCTION OF SOLAR-ASSISTED BIODIGESTER SYSTEM (2022, 12 citas)
    - OPTIMAL DESIGN OF A SECTOR-COUPLED RENEWABLE METHANOL PRODUCTION AMID POLITICAL GOALS AND EXPECTED CONFLICTS: COSTS VS. LAND USE (2024, 9 citas)
    - HYBRIDIZATION OF ANAEROBIC DIGESTION WITH SOLAR ENERGY: A SOLUTION FOR ISOLATED LIVESTOCK FARMS (2023, 8 citas)
Frente 4 [SEÑAL DÉBIL: crece más que el corpus pero sin significancia estadística]: 3 artículos, 32 citas en total.
  Palabras clave características: ANAPLASMA PHAGOCYTOPHILUM, ANAPLASMOSIS, BIOTRANSFORMATION, GENETICS, MICROBIOLOGY, REAL TIME POLYMERASE CHAIN REACTION
  Tendencia: 3 artículos (2015–2023), año medio 2020.0, 67 % en los últimos 3 años, crecimiento +22 %/año (no significativo, p=0.171)
  Artículos más citados:
    - THE OBLIGATE INTRACELLULAR BACTERIAL PATHOGEN ANAPLASMA PHAGOCYTOPHILUM EXPLOITS HOST CELL MULTIVESICULAR BODY BIOGENESIS FOR PROLIFERATION AND DISSEMINATION (2022, 16 citas)
    - DENDRIMER-ENABLED TRANSFORMATION OF ANAPLASMA PHAGOCYTOPHILUM (2015, 10 citas)
    - PHYSIOLOGICAL, PHOTOSYNTHETIC, AND TRANSCRIPTOMICS INSIGHTS INTO THE INFLUENCE OF SHADING ON LEAFY SWEET POTATO (2023, 6 citas)

TEMAS (palabras clave):
Tema 1 [EMERGENTE]: GREENHOUSES, DRYING, SOLAR ENERGY, SOLAR DRYERS, AGRICULTURAL PRODUCTS, GREENHOUSE, SOLAR DRYING, PERFORMANCE
  Tendencia: 20 artículos (2013–2024), año medio 2021.2, 70 % en los últimos 3 años, crecimiento +34 %/año (significativo, p<0,05)
Tema 2: ANAEROBIC DIGESTION, BIOGAS, GREENHOUSE GASES, SOLAR HEATING, SUSTAINABLE DEVELOPMENT, CARBON DIOXIDE, COSTS, BIOGAS PRODUCTION
  Tendencia: 14 artículos (2009–2024), año medio 2019.0, 43 % en los últimos 3 años, crecimiento +16 %/año (significativo, p<0,05)
Tema 3: AGRICULTURE, FERTILIZERS, ENERGY, GREENHOUSE GAS, FERMENTATION, FERTILIZER, GAS EMISSIONS, GREENHOUSE GAS EMISSIONS
  Tendencia: 10 artículos (2014–2023), año medio 2019.7, 50 % en los últimos 3 años, crecimiento +20 %/año (significativo, p<0,05)
Tema 5: FRUITS, ENERGY EFFICIENCY, SOLAR GREENHOUSE, DRYERS (EQUIPMENT), GREENHOUSE DRYER, LYCOPERSICON ESCULENTUM, PERFORMANCE ASSESSMENT, TOMATO
  Tendencia: 6 artículos (2020–2024), año medio 2022.2, 50 % en los últimos 3 años, crecimiento +54 %/año (significativo, p<0,05)
Tema 6: FOOD PROCESSING, ENERGY CONSERVATION, FOOD PRESERVATION, FOOD TECHNOLOGY, HEATING, REFLECTION, TEMPERATURE PROFILE
  Tendencia: 5 artículos (2007–2022), año medio 2015.6, 40 % en los últimos 3 años, crecimiento +0 %/año (no significativo, p=0.9656)
```
</details>

---

## ¿Quiénes son los autores puente del corpus?

**Ruta:** `graph` (esperada `graph`) · 23.8 s

**Respuesta:**

No hay autores puente en este corpus. Esto significa que ningún autor ha publicado artículos en dos o más frentes de investigación distintos dentro del corpus analizado. Los autores con mayor intermediación en la red de acoplamiento son los artículos puente, que conectan diferentes frentes de investigación.

<details><summary>Análisis que recibió el LLM</summary>

```
MÉTODO: red de coautoría (autores unidos si firman un artículo juntos) y red de acoplamiento bibliográfico entre artículos. Autor puente = autor con artículos en dos o más frentes de investigación distintos. Intermediación (betweenness) = cuántos caminos más cortos de la red pasan por el nodo.
RED DE COAUTORÍA: 302 autores, 801 vínculos, 57 grupos desconectados; el grupo más grande tiene 17 autores. Solo 15 autores tienen 2 o más artículos en el corpus.
RED DE ACOPLAMIENTO: 40 de 65 artículos conectados, 83 vínculos, 4 frentes.

AUTORES PUENTE (artículos en 2 o más frentes):
  Ninguno: ningún autor publica en dos frentes distintos de este corpus.
INTERMEDIARIOS EN LA RED DE COAUTORÍA (intermediación > 0):
  - CARLYON, JASON A: intermediación 0.0008, 2 artículos, 12 coautores
  - SUN, JING: intermediación 0.0004, 2 artículos, 8 coautores
  - PILON, LAURENT: intermediación 0.0002, 2 artículos, 9 coautores
  - ZHU, KEYONG: intermediación 0.0002, 2 artículos, 9 coautores
  - PATIL, RAJENDRA C: intermediación 0.0001, 2 artículos, 6 coautores
  - AGERT, CARSTEN: intermediación 0.0, 3 artículos, 16 coautores
  - GEHRKE, KAI: intermediación 0.0, 3 artículos, 16 coautores
  - NEUGEBOHRN, NILS: intermediación 0.0, 3 artículos, 16 coautores
AUTORES CON MÁS ARTÍCULOS:
  - AGERT, CARSTEN: 3 artículos, 16 coautores, países GERMANY
  - GEHRKE, KAI: 3 artículos, 16 coautores, países GERMANY
  - VEHSE, MARTIN: 3 artículos, 16 coautores, países GERMANY
  - NEUGEBOHRN, NILS: 3 artículos, 16 coautores, países GERMANY
  - OSTERTHUN, NORBERT: 3 artículos, 16 coautores, países GERMANY
  - CARLYON, JASON A: 2 artículos, 12 coautores, países UNITED STATES OF AMERICA
  - ZHU, KEYONG: 2 artículos, 9 coautores, países CHINA
  - PILON, LAURENT: 2 artículos, 9 coautores, países UNITED STATES OF AMERICA
ARTÍCULOS PUENTE (mayor intermediación en la red de acoplamiento):
  - WATER AND CARBON FOOTPRINT IMPROVEMENT FOR DRIED TOMATO VALUE CHAIN (2015): intermediación 0.115, enlazado con 11 artículos, conecta los frentes [1, 2]
  - POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS (2022): intermediación 0.093, enlazado con 8 artículos, conecta los frentes [1, 2]
  - CRITICAL REVIEW ON VARIOUS SOLAR DRYING TECHNOLOGIES: DIRECT AND INDIRECT SOLAR DRYER SYSTEMS (2023): intermediación 0.081, enlazado con 13 artículos, conecta los frentes [1, 3]
  - MARINE WATER AQUACULTURE AND AN IOT-BASED SMART FISH DRYER OF THE FUTURE: A SUSTAINABLE ENVIRONMENTAL APPROACH (2023): intermediación 0.063, enlazado con 5 artículos, conecta los frentes [1, 3]
  - DESIGN, FABRICATION, AND EVALUATION OF A LOW-COST PORTABLE SOLAR DRYER FOR SHRIMP FEEDS (2023): intermediación 0.054, enlazado con 8 artículos, conecta los frentes [1, 3]
  - THERMAL ANALYSIS OF PV SYSTEM AND SOLAR COLLECTOR INTEGRATED WITH GREENHOUSE DRYER FOR DRYING TOMATOES (2020): intermediación 0.048, enlazado con 11 artículos, conecta los frentes [1]
```
</details>

---

## ¿Qué autores colaboran más y cómo es la red de coautoría?

**Ruta:** `graph` (esperada `graph`) · 56.2 s

**Respuesta:**

La red de coautoría del corpus académico analizado muestra que hay 302 autores y 801 vínculos entre ellos, distribuidos en 57 grupos desconectados. El grupo más grande tiene 17 autores. Solo 15 autores han participado en dos o más artículos dentro de este corpus.

En la red de acoplamiento bibliográfico, se conectan 40 de los 65 artículos analizados, con un total de 83 vínculos y 4 frentes de investigación diferentes.

No hay autores puente en este corpus, lo que significa que ningún autor ha participado en dos o más frentes de investigación distintos. Los intermediarios en la red de coautoría son aquellos con mayor capacidad para conectar diferentes grupos de autores. Destacan:
- CARLYON, JASON A: intermediación 0.0008.
- SUN, JING: intermediación 0.0004.
- PILON, LAURENT y ZHU, KEYONG: intermediación 0.0002.

Los autores con más artículos son:
- AGERT, CARSTEN, GEHRKE, KAI, VEHSE, MARTIN, NEUGEBOHRN, NILS y OSTERTHUN, NORBERT: cada uno con 3 artículos.
- CARLYON, JASON A, ZHU, KEYONG y PILON, LAURENT: cada uno con 2 artículos.

En la red de acoplamiento bibliográfico, los artículos puente son aquellos que tienen mayor intermediación y conectan diferentes frentes. Destacan:
- WATER AND CARBON FOOTPRINT IMPROVEMENT FOR DRIED TOMATO VALUE CHAIN (2015): intermediación 0.115.
- POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS (2022): intermediación 0.093.
- CRITICAL REVIEW ON VARIOUS SOLAR DRYING TECHNOLOGIES: DIRECT AND INDIRECT SOLAR DRYER SYSTEMS (2023): intermediación 0.081.

Estos resultados indican que la colaboración entre autores es significativa, aunque no hay un autor puente conectando diferentes frentes de investigación. Los artículos con mayor intermediación en la red de acoplamiento son claves para entender las conexiones entre los diferentes frentes de investigación del corpus.

<details><summary>Análisis que recibió el LLM</summary>

```
MÉTODO: red de coautoría (autores unidos si firman un artículo juntos) y red de acoplamiento bibliográfico entre artículos. Autor puente = autor con artículos en dos o más frentes de investigación distintos. Intermediación (betweenness) = cuántos caminos más cortos de la red pasan por el nodo.
RED DE COAUTORÍA: 302 autores, 801 vínculos, 57 grupos desconectados; el grupo más grande tiene 17 autores. Solo 15 autores tienen 2 o más artículos en el corpus.
RED DE ACOPLAMIENTO: 40 de 65 artículos conectados, 83 vínculos, 4 frentes.

AUTORES PUENTE (artículos en 2 o más frentes):
  Ninguno: ningún autor publica en dos frentes distintos de este corpus.
INTERMEDIARIOS EN LA RED DE COAUTORÍA (intermediación > 0):
  - CARLYON, JASON A: intermediación 0.0008, 2 artículos, 12 coautores
  - SUN, JING: intermediación 0.0004, 2 artículos, 8 coautores
  - PILON, LAURENT: intermediación 0.0002, 2 artículos, 9 coautores
  - ZHU, KEYONG: intermediación 0.0002, 2 artículos, 9 coautores
  - PATIL, RAJENDRA C: intermediación 0.0001, 2 artículos, 6 coautores
  - AGERT, CARSTEN: intermediación 0.0, 3 artículos, 16 coautores
  - GEHRKE, KAI: intermediación 0.0, 3 artículos, 16 coautores
  - NEUGEBOHRN, NILS: intermediación 0.0, 3 artículos, 16 coautores
AUTORES CON MÁS ARTÍCULOS:
  - AGERT, CARSTEN: 3 artículos, 16 coautores, países GERMANY
  - GEHRKE, KAI: 3 artículos, 16 coautores, países GERMANY
  - VEHSE, MARTIN: 3 artículos, 16 coautores, países GERMANY
  - NEUGEBOHRN, NILS: 3 artículos, 16 coautores, países GERMANY
  - OSTERTHUN, NORBERT: 3 artículos, 16 coautores, países GERMANY
  - CARLYON, JASON A: 2 artículos, 12 coautores, países UNITED STATES OF AMERICA
  - ZHU, KEYONG: 2 artículos, 9 coautores, países CHINA
  - PILON, LAURENT: 2 artículos, 9 coautores, países UNITED STATES OF AMERICA
ARTÍCULOS PUENTE (mayor intermediación en la red de acoplamiento):
  - WATER AND CARBON FOOTPRINT IMPROVEMENT FOR DRIED TOMATO VALUE CHAIN (2015): intermediación 0.115, enlazado con 11 artículos, conecta los frentes [1, 2]
  - POWERING AGRICULTURE: PRESENT STATUS, FUTURE POTENTIAL, AND CHALLENGES OF RENEWABLE ENERGY APPLICATIONS (2022): intermediación 0.093, enlazado con 8 artículos, conecta los frentes [1, 2]
  - CRITICAL REVIEW ON VARIOUS SOLAR DRYING TECHNOLOGIES: DIRECT AND INDIRECT SOLAR DRYER SYSTEMS (2023): intermediación 0.081, enlazado con 13 artículos, conecta los frentes [1, 3]
  - MARINE WATER AQUACULTURE AND AN IOT-BASED SMART FISH DRYER OF THE FUTURE: A SUSTAINABLE ENVIRONMENTAL APPROACH (2023): intermediación 0.063, enlazado con 5 artículos, conecta los frentes [1, 3]
  - DESIGN, FABRICATION, AND EVALUATION OF A LOW-COST PORTABLE SOLAR DRYER FOR SHRIMP FEEDS (2023): intermediación 0.054, enlazado con 8 artículos, conecta los frentes [1, 3]
  - THERMAL ANALYSIS OF PV SYSTEM AND SOLAR COLLECTOR INTEGRATED WITH GREENHOUSE DRYER FOR DRYING TOMATOES (2020): intermediación 0.048, enlazado con 11 artículos, conecta los frentes [1]
```
</details>

---

## ¿Cómo ha evolucionado el número de artículos y cuál es el pronóstico para los próximos años?

**Ruta:** `forecast` (esperada `forecast`) · 53.9 s

**Respuesta:**

El número de artículos ha experimentado un crecimiento significativo en el corpus académico analizado. En total, hay 65 artículos publicados entre 2007 y 2024, con un promedio anual de 5.2 artículos (año medio 2019.9). El crecimiento anual es del +22 %, lo que se considera una tendencia significativa (p<0,05).

Para los próximos años, el pronóstico realizado mediante el modelo ARIMA(1, 1, 0) indica las siguientes estimaciones:
- En 2025: se espera un total de 13.5 artículos (con un intervalo de confianza del 95 % entre 10.9 y 16.1).
- En 2026: se pronostica un total de 13.8 artículos (con un intervalo de confianza del 95 % entre 9.1 y 18.5).
- En 2027: se espera un total de 13.9 artículos (con un intervalo de confianza del 95 % entre 7.3 y 20.4).

Este pronóstico es orientativo debido a que las series de tiempo son cortas, lo que puede limitar la precisión de las predicciones.

<details><summary>Análisis que recibió el LLM</summary>

```
MÉTODO: series de tiempo anuales del número de artículos. Crecimiento = regresión de Poisson del número de artículos por año. Pronóstico = ARIMA con orden elegido por AIC e intervalo de confianza del 95 %. Las series son cortas: los pronósticos son orientativos.
CORPUS COMPLETO: 65 artículos (2007–2024), año medio 2019.9, 52 % en los últimos 3 años, crecimiento +22 %/año (significativo, p<0,05).
  Artículos por año: 2007: 2, 2008: 1, 2009: 1, 2010: 0, 2011: 0, 2012: 0, 2013: 1, 2014: 3, 2015: 4, 2016: 2, 2017: 2, 2018: 3, 2019: 2, 2020: 4, 2021: 6, 2022: 9, 2023: 12, 2024: 13
  Pronóstico ARIMA(1, 1, 0) (elegido por AIC=62.0), intervalo de confianza 95 %:
    2025: 13.5 artículos (entre 10.9 y 16.1)
    2026: 13.8 artículos (entre 9.1 y 18.5)
    2027: 13.9 artículos (entre 7.3 y 20.4)

TEMA DE LA PREGUNTA: no se encontró en las palabras clave del corpus un tema específico; las cifras de abajo son del corpus completo. Si la pregunta era sobre un tema concreto, dilo.

PALABRAS CLAVE EMERGENTES (crecen más que el corpus, tendencia significativa, ≥3 artículos):
  - SOLAR DRYING: 5 artículos (2015–2023), año medio 2021.2, 80 % en los últimos 3 años, crecimiento +35 %/año (significativo, p<0,05)
  - SOLAR DRYERS: 11 artículos (2013–2024), año medio 2021.1, 73 % en los últimos 3 años, crecimiento +33 %/año (significativo, p<0,05)
  - DRYING: 16 artículos (2015–2024), año medio 2021.5, 69 % en los últimos 3 años, crecimiento +39 %/año (significativo, p<0,05)
  - ENERGY: 6 artículos (2020–2023), año medio 2022.0, 67 % en los últimos 3 años, crecimiento +50 %/año (significativo, p<0,05)
  - SOLAR ENERGY: 13 artículos (2014–2024), año medio 2020.8, 62 % en los últimos 3 años, crecimiento +29 %/año (significativo, p<0,05)
SEÑALES DÉBILES (recientes y en crecimiento, pero sin significancia estadística):
  - HEAT STORAGE: 3 artículos (2023–2024), año medio 2023.7, 100 % en los últimos 3 años, crecimiento +300 %/año (no significativo, p=0.1094)
  - PERFORMANCE: 4 artículos (2023–2024), año medio 2023.5, 100 % en los últimos 3 años, crecimiento +200 %/año (no significativo, p=0.0571)
  - DRYING KINETICS: 3 artículos (2022–2024), año medio 2023.3, 100 % en los últimos 3 años, crecimiento +150 %/año (no significativo, p=0.0943)
  - POSTHARVEST: 3 artículos (2022–2024), año medio 2023.3, 100 % en los últimos 3 años, crecimiento +150 %/año (no significativo, p=0.0943)
  - DRYING METHODS: 3 artículos (2022–2024), año medio 2023.0, 100 % en los últimos 3 años, crecimiento +100 %/año (no significativo, p=0.0896)
  - GREENHOUSE SOLAR DRYER: 3 artículos (2023–2023), año medio 2023.0, 100 % en los últimos 3 años, crecimiento +100 %/año (no significativo, p=0.0896)
  - GAS EMISSIONS: 3 artículos (2022–2023), año medio 2022.7, 100 % en los últimos 3 años, crecimiento +75 %/año (no significativo, p=0.088)
  - GREENHOUSE GAS EMISSIONS: 3 artículos (2022–2023), año medio 2022.7, 100 % en los últimos 3 años, crecimiento +75 %/año (no significativo, p=0.088)

FRENTES DE INVESTIGACIÓN ORDENADOS POR CRECIMIENTO:
  Frente 3 [EMERGENTE] (BIOGAS, BIOGAS PRODUCTION, SOLAR RADIATION, ANAEROBIC DIGESTION): 5 artículos (2021–2024), año medio 2022.6, 80 % en los últimos 3 años, crecimiento +71 %/año (significativo, p<0,05)
  Frente 2 [EMERGENTE] (REFLECTION, SHADING, FOSSIL FUELS, FOOD PROCESSING): 7 artículos (2021–2024), año medio 2022.3, 71 % en los últimos 3 años, crecimiento +58 %/año (significativo, p<0,05)
  Frente 1 [EMERGENTE] (DRYING, GREENHOUSES, SOLAR DRYING, SOLAR DRYERS): 21 artículos (2008–2024), año medio 2020.3, 57 % en los últimos 3 años, crecimiento +25 %/año (significativo, p<0,05)
  Frente 4 [SEÑAL DÉBIL: crece más que el corpus pero sin significancia estadística] (ANAPLASMA PHAGOCYTOPHILUM, ANAPLASMOSIS, BIOTRANSFORMATION, GENETICS): 3 artículos (2015–2023), año medio 2020.0, 67 % en los últimos 3 años, crecimiento +22 %/año (no significativo, p=0.171)
```
</details>

---

## ¿Cuál es la tendencia del secado solar en invernaderos?

**Ruta:** `forecast` (esperada `forecast`) · 63.8 s

**Respuesta:**

La tendencia del secado solar en invernaderos es claramente creciente y emergente. Según el análisis de series de tiempo, el número total de artículos sobre este tema ha aumentado a una tasa significativa de +22 %/año (p<0,05). Además, dentro de este corpus específico, la búsqueda de "SOLAR DRYING + GREENHOUSES" también muestra un crecimiento significativo de +17 %/año (p<0,05).

El pronóstico ARIMA para el número de artículos sobre secado solar en invernaderos es orientativo debido a las series cortas, pero indica que se espera un aumento continuo en los próximos años. Para 2025, se pronostica una cantidad de 13.5 artículos (con un intervalo de confianza del 95 % entre 10.9 y 16.1), y para 2026 y 2027, se prevén 13.8 y 13.9 artículos respectivamente.

Palabras clave emergentes en este campo incluyen "SOLAR DRYING" (5 artículos con un crecimiento de +35 %/año) y "SOLAR DRYERS" (11 artículos con un crecimiento de +33 %/año), lo que refleja una creciente interés en la temática. 

En cuanto a los frentes de investigación, el frente más relevante es "DRYING, GREENHOUSES, SOLAR DRYING, SOLAR DRYERS", clasificado como emergente con un crecimiento significativo de +25 %/año (p<0,05). Esto indica una consolidación y expansión del campo de estudio en los últimos años.

<details><summary>Análisis que recibió el LLM</summary>

```
MÉTODO: series de tiempo anuales del número de artículos. Crecimiento = regresión de Poisson del número de artículos por año. Pronóstico = ARIMA con orden elegido por AIC e intervalo de confianza del 95 %. Las series son cortas: los pronósticos son orientativos.
CORPUS COMPLETO: 65 artículos (2007–2024), año medio 2019.9, 52 % en los últimos 3 años, crecimiento +22 %/año (significativo, p<0,05).
  Artículos por año: 2007: 2, 2008: 1, 2009: 1, 2010: 0, 2011: 0, 2012: 0, 2013: 1, 2014: 3, 2015: 4, 2016: 2, 2017: 2, 2018: 3, 2019: 2, 2020: 4, 2021: 6, 2022: 9, 2023: 12, 2024: 13
  Pronóstico ARIMA(1, 1, 0) (elegido por AIC=62.0), intervalo de confianza 95 %:
    2025: 13.5 artículos (entre 10.9 y 16.1)
    2026: 13.8 artículos (entre 9.1 y 18.5)
    2027: 13.9 artículos (entre 7.3 y 20.4)

TEMA DE LA PREGUNTA (SOLAR DRYING + GREENHOUSES, buscado en título, abstract y palabras clave): 15 artículos (2007–2024), año medio 2019.2, 60 % en los últimos 3 años, crecimiento +17 %/año (significativo, p<0,05).
  Artículos por año: 2007: 1, 2008: 1, 2009: 0, 2010: 0, 2011: 0, 2012: 0, 2013: 1, 2014: 0, 2015: 1, 2016: 0, 2017: 1, 2018: 0, 2019: 0, 2020: 1, 2021: 0, 2022: 2, 2023: 4, 2024: 3
  Pronóstico ARIMA: no se calcula, serie demasiado corta para ARIMA (18 años, 15 artículos; mínimo 10 años y 20 artículos).

PALABRAS CLAVE EMERGENTES (crecen más que el corpus, tendencia significativa, ≥3 artículos):
  - SOLAR DRYING: 5 artículos (2015–2023), año medio 2021.2, 80 % en los últimos 3 años, crecimiento +35 %/año (significativo, p<0,05)
  - SOLAR DRYERS: 11 artículos (2013–2024), año medio 2021.1, 73 % en los últimos 3 años, crecimiento +33 %/año (significativo, p<0,05)
  - DRYING: 16 artículos (2015–2024), año medio 2021.5, 69 % en los últimos 3 años, crecimiento +39 %/año (significativo, p<0,05)
  - ENERGY: 6 artículos (2020–2023), año medio 2022.0, 67 % en los últimos 3 años, crecimiento +50 %/año (significativo, p<0,05)
  - SOLAR ENERGY: 13 artículos (2014–2024), año medio 2020.8, 62 % en los últimos 3 años, crecimiento +29 %/año (significativo, p<0,05)
SEÑALES DÉBILES (recientes y en crecimiento, pero sin significancia estadística):
  - HEAT STORAGE: 3 artículos (2023–2024), año medio 2023.7, 100 % en los últimos 3 años, crecimiento +300 %/año (no significativo, p=0.1094)
  - PERFORMANCE: 4 artículos (2023–2024), año medio 2023.5, 100 % en los últimos 3 años, crecimiento +200 %/año (no significativo, p=0.0571)
  - DRYING KINETICS: 3 artículos (2022–2024), año medio 2023.3, 100 % en los últimos 3 años, crecimiento +150 %/año (no significativo, p=0.0943)
  - POSTHARVEST: 3 artículos (2022–2024), año medio 2023.3, 100 % en los últimos 3 años, crecimiento +150 %/año (no significativo, p=0.0943)
  - DRYING METHODS: 3 artículos (2022–2024), año medio 2023.0, 100 % en los últimos 3 años, crecimiento +100 %/año (no significativo, p=0.0896)
  - GREENHOUSE SOLAR DRYER: 3 artículos (2023–2023), año medio 2023.0, 100 % en los últimos 3 años, crecimiento +100 %/año (no significativo, p=0.0896)
  - GAS EMISSIONS: 3 artículos (2022–2023), año medio 2022.7, 100 % en los últimos 3 años, crecimiento +75 %/año (no significativo, p=0.088)
  - GREENHOUSE GAS EMISSIONS: 3 artículos (2022–2023), año medio 2022.7, 100 % en los últimos 3 años, crecimiento +75 %/año (no significativo, p=0.088)

FRENTES DE INVESTIGACIÓN ORDENADOS POR CRECIMIENTO:
  Frente 3 [EMERGENTE] (BIOGAS, BIOGAS PRODUCTION, SOLAR RADIATION, ANAEROBIC DIGESTION): 5 artículos (2021–2024), año medio 2022.6, 80 % en los últimos 3 años, crecimiento +71 %/año (significativo, p<0,05)
  Frente 2 [EMERGENTE] (REFLECTION, SHADING, FOSSIL FUELS, FOOD PROCESSING): 7 artículos (2021–2024), año medio 2022.3, 71 % en los últimos 3 años, crecimiento +58 %/año (significativo, p<0,05)
  Frente 1 [EMERGENTE] (DRYING, GREENHOUSES, SOLAR DRYING, SOLAR DRYERS): 21 artículos (2008–2024), año medio 2020.3, 57 % en los últimos 3 años, crecimiento +25 %/año (significativo, p<0,05)
  Frente 4 [SEÑAL DÉBIL: crece más que el corpus pero sin significancia estadística] (ANAPLASMA PHAGOCYTOPHILUM, ANAPLASMOSIS, BIOTRANSFORMATION, GENETICS): 3 artículos (2015–2023), año medio 2020.0, 67 % en los últimos 3 años, crecimiento +22 %/año (no significativo, p=0.171)
```
</details>

---

## ¿Cuál es el pronóstico de artículos sobre agrovoltaica?

**Ruta:** `forecast` (esperada `forecast`) · 53.3 s

**Respuesta:**

El pronóstico de artículos sobre agrovoltaica es el siguiente:

- Para el año 2025 se espera que haya 13.5 artículos (con un intervalo de confianza del 95 % entre 10.9 y 16.1 artículos).
- Para el año 2026, se pronostican 13.8 artículos (con un intervalo de confianza del 95 % entre 9.1 y 18.5 artículos).
- Para el año 2027, se prevén 13.9 artículos (con un intervalo de confianza del 95 % entre 7.3 y 20.4 artículos).

El pronóstico se realiza mediante el modelo ARIMA(1, 1, 0), que ha sido elegido por su bajo valor AIC=62.0. Es importante destacar que los pronósticos son orientativos debido a la corta duración de la serie temporal (18 años con solo 7 artículos publicados en total, lo cual es insuficiente para un modelo ARIMA).

<details><summary>Análisis que recibió el LLM</summary>

```
MÉTODO: series de tiempo anuales del número de artículos. Crecimiento = regresión de Poisson del número de artículos por año. Pronóstico = ARIMA con orden elegido por AIC e intervalo de confianza del 95 %. Las series son cortas: los pronósticos son orientativos.
CORPUS COMPLETO: 65 artículos (2007–2024), año medio 2019.9, 52 % en los últimos 3 años, crecimiento +22 %/año (significativo, p<0,05).
  Artículos por año: 2007: 2, 2008: 1, 2009: 1, 2010: 0, 2011: 0, 2012: 0, 2013: 1, 2014: 3, 2015: 4, 2016: 2, 2017: 2, 2018: 3, 2019: 2, 2020: 4, 2021: 6, 2022: 9, 2023: 12, 2024: 13
  Pronóstico ARIMA(1, 1, 0) (elegido por AIC=62.0), intervalo de confianza 95 %:
    2025: 13.5 artículos (entre 10.9 y 16.1)
    2026: 13.8 artículos (entre 9.1 y 18.5)
    2027: 13.9 artículos (entre 7.3 y 20.4)

TEMA DE LA PREGUNTA (AGRIVOLTAICS, buscado en título, abstract y palabras clave): 7 artículos (2021–2024), año medio 2022.9, 71 % en los últimos 3 años, crecimiento +88 %/año (significativo, p<0,05).
  Artículos por año: 2007: 0, 2008: 0, 2009: 0, 2010: 0, 2011: 0, 2012: 0, 2013: 0, 2014: 0, 2015: 0, 2016: 0, 2017: 0, 2018: 0, 2019: 0, 2020: 0, 2021: 2, 2022: 1, 2023: 0, 2024: 4
  Pronóstico ARIMA: no se calcula, serie demasiado corta para ARIMA (18 años, 7 artículos; mínimo 10 años y 20 artículos).

PALABRAS CLAVE EMERGENTES (crecen más que el corpus, tendencia significativa, ≥3 artículos):
  - SOLAR DRYING: 5 artículos (2015–2023), año medio 2021.2, 80 % en los últimos 3 años, crecimiento +35 %/año (significativo, p<0,05)
  - SOLAR DRYERS: 11 artículos (2013–2024), año medio 2021.1, 73 % en los últimos 3 años, crecimiento +33 %/año (significativo, p<0,05)
  - DRYING: 16 artículos (2015–2024), año medio 2021.5, 69 % en los últimos 3 años, crecimiento +39 %/año (significativo, p<0,05)
  - ENERGY: 6 artículos (2020–2023), año medio 2022.0, 67 % en los últimos 3 años, crecimiento +50 %/año (significativo, p<0,05)
  - SOLAR ENERGY: 13 artículos (2014–2024), año medio 2020.8, 62 % en los últimos 3 años, crecimiento +29 %/año (significativo, p<0,05)
SEÑALES DÉBILES (recientes y en crecimiento, pero sin significancia estadística):
  - HEAT STORAGE: 3 artículos (2023–2024), año medio 2023.7, 100 % en los últimos 3 años, crecimiento +300 %/año (no significativo, p=0.1094)
  - PERFORMANCE: 4 artículos (2023–2024), año medio 2023.5, 100 % en los últimos 3 años, crecimiento +200 %/año (no significativo, p=0.0571)
  - DRYING KINETICS: 3 artículos (2022–2024), año medio 2023.3, 100 % en los últimos 3 años, crecimiento +150 %/año (no significativo, p=0.0943)
  - POSTHARVEST: 3 artículos (2022–2024), año medio 2023.3, 100 % en los últimos 3 años, crecimiento +150 %/año (no significativo, p=0.0943)
  - DRYING METHODS: 3 artículos (2022–2024), año medio 2023.0, 100 % en los últimos 3 años, crecimiento +100 %/año (no significativo, p=0.0896)
  - GREENHOUSE SOLAR DRYER: 3 artículos (2023–2023), año medio 2023.0, 100 % en los últimos 3 años, crecimiento +100 %/año (no significativo, p=0.0896)
  - GAS EMISSIONS: 3 artículos (2022–2023), año medio 2022.7, 100 % en los últimos 3 años, crecimiento +75 %/año (no significativo, p=0.088)
  - GREENHOUSE GAS EMISSIONS: 3 artículos (2022–2023), año medio 2022.7, 100 % en los últimos 3 años, crecimiento +75 %/año (no significativo, p=0.088)

FRENTES DE INVESTIGACIÓN ORDENADOS POR CRECIMIENTO:
  Frente 3 [EMERGENTE] (BIOGAS, BIOGAS PRODUCTION, SOLAR RADIATION, ANAEROBIC DIGESTION): 5 artículos (2021–2024), año medio 2022.6, 80 % en los últimos 3 años, crecimiento +71 %/año (significativo, p<0,05)
  Frente 2 [EMERGENTE] (REFLECTION, SHADING, FOSSIL FUELS, FOOD PROCESSING): 7 artículos (2021–2024), año medio 2022.3, 71 % en los últimos 3 años, crecimiento +58 %/año (significativo, p<0,05)
  Frente 1 [EMERGENTE] (DRYING, GREENHOUSES, SOLAR DRYING, SOLAR DRYERS): 21 artículos (2008–2024), año medio 2020.3, 57 % en los últimos 3 años, crecimiento +25 %/año (significativo, p<0,05)
  Frente 4 [SEÑAL DÉBIL: crece más que el corpus pero sin significancia estadística] (ANAPLASMA PHAGOCYTOPHILUM, ANAPLASMOSIS, BIOTRANSFORMATION, GENETICS): 3 artículos (2015–2023), año medio 2020.0, 67 % en los últimos 3 años, crecimiento +22 %/año (no significativo, p=0.171)
```
</details>

---
