"""
trends.py — Series de tiempo anuales, indicadores de crecimiento y ARIMA
=========================================================================
Los corpus son cortos (15–20 años con 1–54 artículos por año), así que:
- El crecimiento de cada tema se mide con una regresión de Poisson del número de
  artículos por año (tasa anual de crecimiento + p-valor), la participación de los
  últimos años y el año medio de publicación.
- El pronóstico (ARIMA) se hace solo sobre series con datos suficientes y siempre con
  su intervalo de confianza del 95 %.
"""

import os
import warnings

import numpy as np

RECENT_YEARS = int(os.getenv("TREND_RECENT_YEARS", "3"))       # ventana de "años recientes"
FORECAST_HORIZON = int(os.getenv("FORECAST_HORIZON", "3"))     # años a pronosticar
ARIMA_MIN_YEARS = int(os.getenv("ARIMA_MIN_YEARS", "10"))      # mínimo de años para ajustar ARIMA
ARIMA_MIN_ARTICLES = int(os.getenv("ARIMA_MIN_ARTICLES", "20"))


def annual_series(years: list[int], start: int | None = None, end: int | None = None) -> dict[int, int]:
    """Número de artículos por año, con ceros en los años sin publicaciones."""
    years = [y for y in years if y]
    if not years:
        return {}
    start = start or min(years)
    end = end or max(years)
    series = {y: 0 for y in range(start, end + 1)}
    for y in years:
        if start <= y <= end:
            series[y] += 1
    return series


def growth_indicators(series: dict[int, int], recent: int = RECENT_YEARS) -> dict:
    """
    Indicadores de crecimiento de una serie anual.

    - growth_rate: crecimiento anual estimado por regresión de Poisson (0.25 = +25 % por año).
    - p_value: significancia de esa tendencia (con pocos artículos suele no ser significativa).
    - recent_share: fracción de los artículos publicada en los últimos `recent` años del corpus.
    - mean_year: año medio de publicación.
    """
    years = np.array(sorted(series))
    counts = np.array([series[y] for y in years])
    total = int(counts.sum())
    out = {"total": total, "first_year": None, "last_year": None, "mean_year": None,
           "recent_share": None, "growth_rate": None, "p_value": None}
    if total == 0:
        return out
    active = years[counts > 0]
    out["first_year"], out["last_year"] = int(active.min()), int(active.max())
    out["mean_year"] = round(float((years * counts).sum() / total), 1)
    out["recent_share"] = round(float(counts[years > years.max() - recent].sum() / total), 2)
    if len(years) >= 3 and total >= 3:
        import statsmodels.api as sm
        x = sm.add_constant(years - years.min())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                fit = sm.GLM(counts, x, family=sm.families.Poisson()).fit()
                out["growth_rate"] = round(float(np.exp(fit.params[1]) - 1), 3)
                out["p_value"] = round(float(fit.pvalues[1]), 4)
            except Exception:
                pass
    return out


def arima_forecast(series: dict[int, int], horizon: int = FORECAST_HORIZON) -> dict:
    """
    Ajusta ARIMA(p,d,q) a la serie anual eligiendo el orden por AIC (p, q ≤ 2; d ≤ 1)
    y pronostica `horizon` años con intervalo de confianza del 95 %.
    """
    years = sorted(series)
    counts = np.array([series[y] for y in years], dtype=float)
    if len(years) < ARIMA_MIN_YEARS or counts.sum() < ARIMA_MIN_ARTICLES:
        return {"ok": False, "reason": f"serie demasiado corta para ARIMA ({len(years)} años, "
                                       f"{int(counts.sum())} artículos; mínimo {ARIMA_MIN_YEARS} años "
                                       f"y {ARIMA_MIN_ARTICLES} artículos)"}
    from statsmodels.tsa.arima.model import ARIMA

    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for d in (0, 1):
            for p in range(3):
                for q in range(3):
                    try:
                        fit = ARIMA(counts, order=(p, d, q), trend="t" if d == 0 else "n").fit()
                    except Exception:
                        continue
                    if np.isfinite(fit.aic) and (best is None or fit.aic < best[1].aic):
                        best = ((p, d, q), fit)
    if best is None:
        return {"ok": False, "reason": "ningún modelo ARIMA convergió"}
    order, fit = best
    fc = fit.get_forecast(steps=horizon)
    mean = np.clip(fc.predicted_mean, 0, None)
    ci = np.clip(fc.conf_int(alpha=0.05), 0, None)
    return {
        "ok": True,
        "order": order,
        "aic": round(float(fit.aic), 1),
        "forecast": [{"year": years[-1] + i + 1, "mean": round(float(mean[i]), 1),
                      "low": round(float(ci[i][0]), 1), "high": round(float(ci[i][1]), 1)}
                     for i in range(horizon)],
    }
