# Diagnóstico del pronóstico ARIMA (Capa 5)

> **Actualización 2026-10-20 (tarde): la recomendación de ARIMA(0,2,0) de la sección 4 queda retirada.** Se repitió todo
> en `ai` y `pendulo` y con la transformación log(1+y) (sección 5): ARIMA(0,2,0) solo funciona en Agrovoltaics; en
> `pendulo` pronostica 10 → 5 → 0 artículos y en `ai` es peor que el ingenuo en el corte 2023–2025. Las secciones 1–4
> se conservan como el análisis original de Agrovoltaics.

## Corpus Agrovoltaics (análisis original)

Fecha: 2026-10-20 (pedido por William). Script: `diagnostico_arima.py`; salida completa en `salida_Agrovoltaics.txt`.
No se cambió el agente: esto revisa el método de `src/layer5_network/trends.arima_forecast`.

**Serie**: artículos principales (`ismainarticle = 1`) por año, 2007–2024, n = 18, 65 artículos.

| 2007 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 1 | 0 | 0 | 0 | 1 | 3 | 4 | 2 | 2 | 3 | 2 | 4 | 6 | 9 | 12 | 13 |

## 1. Estacionariedad: ¿cuántas diferencias?

ADF: H0 = raíz unitaria (hay que diferenciar); se rechaza con p < 0,05. KPSS: H0 = estacionaria; se rechaza con p < 0,05
(statsmodels solo tabula el p de KPSS entre 0,01 y 0,10: "0,100" significa ≥ 0,10). ADF con 0 y 1 rezagos fijos: con
18 datos, la selección automática por AIC elegía 7 rezagos y la prueba perdía casi toda su potencia.

**Conteos** (serie completa):

| Serie | Determinista | ADF(0) p | ADF(1) p | KPSS p | Lectura |
|---|---|---|---|---|---|
| Nivel | constante | 0,998 | 0,975 | **0,013** | no estacionaria (ambas) |
| Nivel | const. + tendencia | 0,976 | 0,941 | **0,021** | no estacionaria (ambas) |
| 1.ª diferencia | constante | 0,098 | 0,344 | 0,054 | **en el límite**: ADF no rechaza raíz unitaria; KPSS no rechaza estacionariedad por poco |
| 1.ª diferencia | const. + tendencia | 0,105 | 0,278 | ≥ 0,10 | ADF: no estacionaria; KPSS: estacionaria con tendencia |
| 2.ª diferencia | constante | **0,000** | **0,003** | ≥ 0,10 | estacionaria (ambas) |
| 2.ª diferencia | const. + tendencia | **0,001** | **0,038** | ≥ 0,10 | estacionaria (ambas) |

**log(1 + conteos)**: nivel no estacionario; **1.ª diferencia con constante: ADF(0) p = 0,019 y KPSS p ≥ 0,10 → ambas
coinciden en d = 1**.

Con solo el entrenamiento (2007–2021, n = 15) el cuadro es parecido: 1.ª diferencia de conteos ADF(0) p = 0,057 y KPSS
≥ 0,10 (d = 1 en el límite), 2.ª diferencia estacionaria con ambas.

**Conclusión**: en conteos, d = 0 queda descartado; entre d = 1 y d = 2 las pruebas no coinciden (el ADF pide d = 2;
el KPSS acepta d = 1). Es lo esperable en una serie que **acelera** (crecimiento exponencial): las primeras diferencias
siguen creciendo. En logaritmos el crecimiento se vuelve lineal y basta d = 1. Por eso se validan tres familias:
conteos d = 1, conteos d = 2 y log(1+y) d = 1. Indicio de que d = 2 no es una sobrediferenciación: en ARIMA(0,2,1) el
coeficiente MA es −0,56, lejos de −1.

## 2. Fuera de muestra: entrenar hasta 2021, pronosticar 2022–2024

Real: 2022 = 9, 2023 = 12, 2024 = 13. En cada familia el orden se elige por **AICc** (AIC corregido para muestras
pequeñas), comparando solo modelos con el mismo d y la misma transformación.

| Modelo (ajustado con 2007–2021) | Pronóstico 22 / 23 / 24 | MAE | RMSE | MAPE | Real dentro del IC 95 % |
|---|---|---|---|---|---|
| Agente actual (AIC con d ∈ {0,1}) → ARIMA(0,1,0) | 6,0 / 6,0 / 6,0 | 5,33 | 5,60 | 46 % | 0/3 |
| Conteos d = 1, mejor AICc: ARIMA(0,1,0) | 6,0 / 6,0 / 6,0 | 5,33 | 5,60 | 46 % | 0/3 |
| Conteos d = 1 con deriva: ARIMA(0,1,0) | 6,3 / 6,6 / 6,9 | 4,76 | 4,99 | 41 % | 0/3 |
| Conteos d = 2, mejor AICc: ARIMA(0,2,1) | 6,7 / 7,5 / 8,2 | 3,87 | 4,03 | 33 % | 2/3 |
| **Conteos d = 2: ARIMA(0,2,0)** | **8,0 / 10,0 / 12,0** | **1,33** | **1,41** | **12 %** | **3/3** |
| Conteos d = 2: ARIMA(1,2,0) | 8,0 / 10,0 / 12,0 | 1,33 | 1,41 | 12 % | 3/3 |
| log(1+y) d = 1, mejor AICc: ARIMA(0,1,0) | 6,0 / 6,0 / 6,0 | 5,33 | 5,60 | 46 % | 3/3 (IC muy anchos: hasta 28) |
| Referencia: ingenuo (último valor) | 6 / 6 / 6 | 5,33 | 5,60 | 46 % | — |
| Referencia: ingenuo con deriva | 6,3 / 6,6 / 6,9 | 4,76 | 4,99 | 41 % | — |
| Referencia: regresión de Poisson | 5,3 / 6,1 / 7,1 | 5,15 | 5,26 | 45 % | — |

Un solo corte de 3 puntos es frágil, así que se repitió con **origen móvil**: cortes en 2016, 2017, …, 2023 (siempre
≥ 10 años de entrenamiento) y pronóstico a 1, 2 y 3 años de cada corte (21 errores).

| Modelo | MAE | RMSE | Sesgo (real − pron.) | MAE a 1 / 2 / 3 años | Cobertura IC 95 % |
|---|---|---|---|---|---|
| ARIMA(1,1,0) — agente actual | 2,80 | 3,64 | +2,63 | 1,50 / 2,80 / 4,54 | 67 % |
| ARIMA(1,1,0) con deriva | 2,71 | 3,47 | +2,53 | 1,49 / 2,67 / 4,39 | 67 % |
| **ARIMA(0,2,0)** | **2,00** | **2,86** | **+1,33** | **1,37 / 2,14 / 2,67** | **95 %** |
| ARIMA(0,2,1) | 2,68 | 3,35 | +2,37 | 1,59 / 2,49 / 4,34 | 76 % |
| ARIMA(1,2,0) | 2,37 | 3,05 | +1,79 | 1,57 / 2,34 / 3,45 | 100 % |
| log(1+y) ARIMA(0,1,0) con deriva | 2,54 | 3,36 | +2,41 | 1,36 / 2,53 / 4,11 | 100 % |
| log(1+y) ARIMA(1,1,0) con deriva | 2,52 | 3,25 | +2,31 | 1,39 / 2,42 / 4,13 | 100 % |
| Ingenuo (último valor) | 2,90 | 3,77 | +2,81 | | |
| Ingenuo con deriva | 2,67 | 3,50 | +2,56 | | |
| Regresión de Poisson | 2,63 | 3,35 | +2,05 | | |

(Con cortes desde 2019 el orden es el mismo: ARIMA(0,2,0) MAE 2,42 frente a 4,04 del modelo actual.)

Lectura:
- **El modelo actual del agente apenas mejora al pronóstico ingenuo** (MAE 2,80 frente a 2,90) y **subestima
  sistemáticamente** (sesgo +2,6 artículos): con d = 1 sin deriva no puede seguir una serie que acelera. Su IC 95 %
  solo contiene el valor real el 67 % de las veces (debería ser ~95 %).
- **ARIMA(0,2,0) es el mejor en las dos validaciones**: menor error en todos los horizontes, el menor sesgo y una
  cobertura del IC (95 %) igual a la nominal.
- Los modelos en log tienen IC que siempre cubren, pero porque son muy anchos; su error es mayor.
- Todos los modelos subestiman (sesgo > 0): 2021–2024 creció más rápido que cualquier tendencia anterior.

## 3. Residuos: ¿son ruido blanco?

Ajuste con la serie completa; se descartan los d primeros residuos (salen de la inicialización, no son errores de
pronóstico). Ljung-Box con los grados de libertad del modelo (p + q); bandas de la ACF ±1,96/√n.

| Modelo | n | Media (t, p) | Ljung-Box p (3/4/5/6 rezagos) | Jarque-Bera p | Shapiro-Wilk p | Heterocedast. p | ACF fuera de banda |
|---|---|---|---|---|---|---|---|
| **ARIMA(0,2,0)** | 16 | +0,13 (0,76) | 0,32 / 0,26 / 0,38 / 0,51 | 0,81 | 0,37 | 0,20 | ninguno (máx. \|−0,30\|, banda ±0,49) |
| ARIMA(0,2,1) | 16 | +0,38 (0,29) | 0,60 / 0,35 / 0,49 / 0,61 | 0,25 | 0,13 | 0,16 | ninguno |
| ARIMA(1,2,0) | 16 | +0,20 (0,60) | 0,34 / 0,31 / 0,47 / 0,59 | 0,32 | 0,09 | 0,16 | ninguno |
| ARIMA(1,1,0) — actual | 17 | +0,35 (0,29) | 0,69 / 0,53 / 0,67 / 0,79 | 0,69 | 0,77 | 0,07 | ninguno |
| log(1+y) ARIMA(0,1,0) + deriva | 17 | +0,00 (1,00) | 0,47 / 0,33 / 0,31 / 0,42 | 0,76 | 0,61 | 0,27 | ninguno |

**Todos pasan**: no se rechaza ausencia de autocorrelación (Ljung-Box p > 0,05), normalidad (JB y Shapiro), media cero
ni varianza constante. Los residuos de ARIMA(0,2,0) son compatibles con ruido blanco.
**Cautela**: con 16–17 residuos estas pruebas tienen poca potencia; que todos los modelos pasen significa que los
residuos **no distinguen** entre ellos. La elección se apoya en las pruebas de estacionariedad y en la validación fuera
de muestra. En el modelo actual hay un patrón: 4 de los 5 últimos residuos son positivos (se queda corto justo cuando
la serie acelera), lo mismo que muestra el sesgo de la validación.

## 4. Modelo recomendado: ARIMA(0,2,0)

- Ecuación: Δ²yₜ = εₜ, es decir yₜ = 2yₜ₋₁ − yₜ₋₂ + εₜ, con σ² = 2,375 (p = 0,017). Sin parámetros AR/MA: prolonga
  la última pendiente (tendencia lineal local) y la incertidumbre crece rápido con el horizonte.
- Por qué: (1) el ADF pide d = 2 en conteos; (2) gana en el corte 2022–2024 y en el origen móvil; (3) su IC 95 % cubre
  lo que promete; (4) residuos compatibles con ruido blanco; (5) su AICc (61,5) empata con ARIMA(0,2,1) (61,3;
  diferencia < 2) y es el más parsimonioso.
- Pronóstico con la serie completa:

| Año | ARIMA(0,2,0) | IC 95 % | Modelo actual ARIMA(1,1,0) | IC 95 % |
|---|---|---|---|---|
| 2025 | 14,0 | 11,0 – 17,0 | 13,5 | 10,9 – 16,1 |
| 2026 | 15,0 | 8,2 – 21,8 | 13,8 | 9,1 – 18,5 |
| 2027 | 16,0 | 4,7 – 27,3 | 13,9 | 7,3 – 20,4 |

## Cautelas para la tesis

- Una sola serie de 18 años: las pruebas tienen poca potencia y los resultados valen para este corpus; habría que
  repetir el diagnóstico en `ai` y `pendulo` antes de cambiar la regla general del agente.
- ARIMA(0,2,0) extrapola la pendiente de los dos últimos años: si la serie se estabiliza, sobreestimará. A 3 años el
  intervalo es amplio (4,7–27,3): el pronóstico es orientativo.
- Los 21 errores del origen móvil se solapan (cortes consecutivos comparten años), no son independientes.

---

## 5. Los tres corpus (Agrovoltaics, ai, pendulo), en conteos y en log(1+y)

Salidas completas: `salida_Agrovoltaics.txt`, `salida_ai.txt`, `salida_pendulo.txt`
(`python benchmark/series_tiempo/diagnostico_arima.py --session <sesión>`).

| Corpus | Años | Artículos | Serie |
|---|---|---|---|
| Agrovoltaics | 2007–2024 (18) | 65 | 2, 1, 1, 0, 0, 0, 1, 3, 4, 2, 2, 3, 2, 4, 6, 9, 12, 13 — acelera |
| ai | 2006–2025 (20) | 262 | 2, 1, 1, 1, 3, 6, 3, 2, 5, 5, 3, 6, 6, 12, 12, 25, 24, 39, 52, 54 — acelera mucho |
| pendulo | 2006–2024 (19) | 153 | 1, 1, 1, 3, 7, 8, 13, 9, 9, 1, 9, 15, 6, 4, 8, 11, 12, 20, 15 — ruidosa, sin aceleración clara |

(En `ai` el último año es 2025; si el export se hizo antes de terminar el año, 2025 está incompleto.)

### 5.1 Estacionariedad (ADF con 0 y 1 rezagos; KPSS con 1 rezago)

| Corpus | Conteos | log(1+y) |
|---|---|---|
| Agrovoltaics | nivel no estac.; 1.ª dif. **en el límite** (ADF p 0,10; KPSS p 0,054); 2.ª dif. estac. → d = 1 o 2 | **d = 1** (1.ª dif.: ADF p 0,019; KPSS ≥ 0,10) |
| ai | nivel no estac.; 1.ª dif.: **KPSS rechaza** (p 0,022) y ADF(1) no rechaza (p 0,47); 2.ª dif. estac. → **d = 2** | **d = 1** (1.ª dif.: ADF p ≤ 0,001; KPSS ≥ 0,10) |
| pendulo | nivel dudoso (KPSS rechaza con constante, no con tendencia); 1.ª dif. estac. (ADF p ≤ 0,001; KPSS ≥ 0,10) → **d = 1** | **d = 1** (igual) |

En **logaritmos las pruebas coinciden en d = 1 en los tres corpus**; en conteos piden d distinto según el corpus (las
series que aceleran piden d = 2). Confirmación adicional: en log, ARIMA(0,2,1) estima el MA en **−1,0** en `ai` y
`pendulo` (raíz unitaria en la parte MA = **sobrediferenciación**); con d = 2 en log se está diferenciando de más.

### 5.2 ¿Los otros corpus tienen los mismos errores que Agrovoltaics?

Origen móvil (cortes desde el 10.º año, pronóstico a 1–3 años; MAE relativo al ingenuo "repetir el último valor":
< 1 es mejor que el ingenuo). "Agente actual" = la regla de `trends.arima_forecast` (AIC con d ∈ {0,1}) **reelegida en
cada corte**, como la usaría el agente.

| Error | Agrovoltaics | ai | pendulo |
|---|---|---|---|
| El agente actual no mejora al ingenuo (MAE relativo) | ×1,00 | ×1,01 | ×1,02 |
| Subestima (sesgo = real − pronóstico) | +2,8 | +9,6 | +2,7 |
| Su IC 95 % contiene el valor real | 38 % | 30 % | 88 % |
| Elige a veces modelos sin diferenciar (d = 0) | sí, (2,0,2) | sí, (0,0,2), (0,0,1) | no |

**Sí: los tres errores se repiten.** El agente actual equivale al pronóstico ingenuo en los tres corpus, subestima en los
tres, y en los dos que aceleran su intervalo del 95 % solo acierta 1 de cada 3 veces. Además, en algunos cortes elige
d = 0 (lo permite porque compara por AIC modelos con d distinto), algo que las pruebas descartan.

### 5.3 Residuos en conteos: ¿ruido blanco?

| Corpus | Resultado en conteos |
|---|---|
| Agrovoltaics | Todos los modelos pasan (Ljung-Box, normalidad, media cero, varianza constante). |
| ai | **No.** **Heterocedasticidad en todos los modelos** (p 0,00–0,04: la varianza crece con el nivel); normalidad rechazada (Shapiro p ≤ 0,01) en los de d = 1; **autocorrelación** en ARIMA(0,2,0) (Ljung-Box p 0,019 y 0,039 en 3 y 4 rezagos). |
| pendulo | Todos pasan. |

### 5.4 Con log(1+y)

**Residuos** (escala log): en `ai` **desaparece la heterocedasticidad** (p 0,13–0,88) y la no normalidad (Shapiro p ≥ 0,06);
Ljung-Box no rechaza en ningún corpus. Todos los modelos log con d = 1 pasan las pruebas de ruido blanco en los tres
corpus. Única excepción: log ARIMA(0,2,0) en `pendulo` (Jarque-Bera p 0,01), de una familia ya descartada por
sobrediferenciación. **El log arregla lo que fallaba en conteos.**

**Precisión** (origen móvil, MAE relativo al ingenuo; entre paréntesis la cobertura del IC 95 %):

| Modelo | Agrovoltaics | ai | pendulo | Lectura |
|---|---|---|---|---|
| Agente actual (conteos, AIC, d ≤ 1) | ×1,00 (38 %) | ×1,01 (30 %) | ×1,02 (88 %) | = ingenuo |
| Conteos, d = 2, mejor AICc en cada corte | ×0,91 (76 %) | ×0,66 (63 %) | ×1,01 (83 %) | bueno si acelera; IC cortos |
| Conteos ARIMA(0,2,0) (recomendado antes) | ×0,69 (95 %) | ×0,96 (85 %) | **×1,59** (88 %) | **inestable** |
| Conteos ARIMA(1,2,0) | ×0,81 (100 %) | ×0,60 (81 %) | ×1,37 (79 %) | inestable |
| log, d = 1, mejor AICc en cada corte | ×1,00 (100 %) | ×0,92 (100 %) | ×1,00 (92 %) | el AICc quita la deriva → ingenuo |
| **log ARIMA(0,1,0) con deriva** | **×0,87 (100 %)** | **×0,71 (100 %)** | ×1,08 (92 %) | estable |
| **log ARIMA(1,1,0) con deriva** | **×0,87 (100 %)** | **×0,72 (100 %)** | ×1,03 (92 %) | estable |
| log, d = 2 (0,2,0) | ×1,06 | ×2,23 | **×12,4** | explota al exponenciar |
| Regresión de Poisson (referencia) | ×0,90 | ×0,76 | ×0,86 | la más regular |

**Corte fijo de los últimos 3 años** (MAE; real entre paréntesis):

| Modelo | Agrovoltaics 22–24 (9, 12, 13) | ai 23–25 (39, 52, 54) | pendulo 22–24 (12, 20, 15) |
|---|---|---|---|
| ARIMA(1,1,0), modelo actual | 4,97 | 24,25 | 5,07 |
| ARIMA(0,2,0) | **1,33** | 26,33 | 3,33 |
| ARIMA(1,2,0) | 1,33 | **9,45** | 3,56 |
| log ARIMA(0,1,0) con deriva | 4,42 | 16,56 | 2,49 |
| log ARIMA(1,1,0) con deriva | 4,02 | 14,90 | **2,30** |
| Ingenuo | 5,33 | 24,33 | 4,67 |
| Regresión de Poisson | 5,15 | 14,71 | 3,01 |

**Pronóstico con la serie completa** (próximos 3 años):

| Modelo | Agrovoltaics 2025–27 | ai 2026–28 | pendulo 2025–27 |
|---|---|---|---|
| ARIMA(1,1,0), modelo actual | 13,5 / 13,8 / 13,9 | 54,5 / 54,7 / 54,7 | 15,9 / 15,8 / 15,8 |
| ARIMA(0,2,0) | 14 / 15 / 16 | 56 / 58 / 60 | **10 / 5 / 0** |
| log ARIMA(0,1,0) con deriva | 14,3 / 15,8 / 17,4 (IC 2025: 6,2–31,6) | 63,1 / 73,7 / 86,1 (IC 2026: 28–139) | 17,0 / 19,2 / 21,6 (IC 2025: 3,9–65) |

### 5.5 Conclusiones

1. **Los errores del agente actual son generales**, no de Agrovoltaics: en los tres corpus su pronóstico equivale al
   ingenuo, subestima y en los corpus que aceleran su IC 95 % falla 2 de cada 3 veces.
2. **ARIMA(0,2,0) en conteos no sirve como regla general**: ganó en Agrovoltaics por la forma de esa serie, pero
   extrapola la pendiente de los dos últimos años y en `pendulo` (que bajó de 20 a 15) pronostica 0 artículos en 2027.
   Elegir el modelo con un solo corpus fue un sobreajuste.
3. **log(1+y) con d = 1 y deriva** (crecimiento porcentual constante, el análogo ARIMA de la regresión de Poisson) es
   la opción más coherente: las pruebas ADF/KPSS coinciden en d = 1 en los tres corpus, los residuos son ruido blanco
   en los tres (en conteos `ai` falla), mejora al ingenuo en Agrovoltaics (×0,87) y ai (×0,71) y queda cerca en
   pendulo (×1,03–1,08), y nunca da pronósticos absurdos.
4. **La deriva hay que imponerla**, no dejarla al AICc: con 15–20 datos la deriva no sale significativa y el AICc la
   quita, con lo que el modelo vuelve a ser el ingenuo (fila "log, d = 1, mejor AICc").
5. **Costo del log: intervalos muy anchos** (cobertura 92–100 %, por encima del 95 % nominal en dos corpus): son
   honestos, pero poco informativos a 2–3 años. Conviene reportar solo el año siguiente con IC, o horizontes de 1–2 años.
6. **La regresión de Poisson es la referencia más regular** (×0,76–0,90 en los tres) y el agente ya la calcula para la
   tasa de crecimiento. Su pronóstico podría acompañar al del ARIMA (falta revisar su sobredispersión).

Cautelas: tres series de 18–20 años; los errores del origen móvil se solapan; `ai` puede tener 2025 incompleto.

**Propuesta para el agente (sin aplicar, requiere aprobación)**: en `trends.arima_forecast`, ajustar sobre log(1+y) con
d = 1 y deriva fija, elegir solo p, q ≤ 1 por AICc, devolver el pronóstico con `expm1` e informar el IC; quitar la
comparación por AIC entre d = 0 y d = 1.

---

## 6. Cambio aplicado al agente (2026-10-20, aprobado por William)

`src/layer5_network/trends.arima_forecast` ahora: (1) ajusta sobre log(1 + artículos); (2) d = 1 fijo; (3) deriva
siempre incluida (`trend="t"`); (4) elige p, q ∈ {0, 1} por AICc (4 candidatos); (5) devuelve el pronóstico y el IC
en artículos con expm1 (mediana, no media). Se quitó la comparación por AIC entre d = 0 y d = 1. Devuelve además
`aicc` y `drift_growth` (crecimiento anual implícito de la deriva); `context.py` lo explica al LLM.

AICc de los 4 candidatos con la serie completa (k = parámetros estimados, incluida la varianza):

| Corpus | (0,1,0) k=2 | (0,1,1) k=3 | (1,1,0) k=3 | (1,1,1) k=4 | Elegido | Deriva |
|---|---|---|---|---|---|---|
| Agrovoltaics | **20,64** | 22,95 | 22,85 | 26,85 | (0,1,0) | +9,5 %/año |
| ai | **23,81** | 24,74 | 25,80 | 27,21 | (0,1,0) | +16,5 %/año |
| pendulo | **41,24** | 41,51 | 43,18 | 42,32 | (0,1,0) | +12,2 %/año |

En pendulo el AIC sin corregir habría elegido (1,1,1) (AIC 39,24, el menor), con MA = −0,998 (no invertible); el AICc
lo penaliza y elige (0,1,0).

Origen móvil con la regla nueva reelegida en cada corte (antes → ahora; MAE relativo al ingenuo, cobertura IC 95 %):

| Corpus | Regla anterior | Regla nueva | Sesgo anterior → nuevo |
|---|---|---|---|
| Agrovoltaics | ×1,00 (38 %) | **×0,88 (100 %)** | +2,75 → +2,42 |
| ai | ×1,01 (30 %) | **×0,78 (81 %)** | +9,63 → +7,12 |
| pendulo | ×1,02 (88 %) | ×1,08 (92 %) | +2,67 → −0,23 |

Pronóstico vigente: Agrovoltaics 2025–27: 14,3 / 15,8 / 17,4 (IC 2025: 6,2–31,6); ai 2026–28: 63,1 / 73,7 / 86,1
(IC 2026: 28,3–139,3); pendulo 2025–27: 17,0 / 19,2 / 21,6 (IC 2025: 3,9–65,2).
