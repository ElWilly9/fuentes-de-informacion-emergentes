"""
diagnostico_arima.py — Diagnóstico del pronóstico ARIMA de la Capa 5 (artículos por año)
========================================================================================
Pedido por William (2026-10-20). No cambia el agente: revisa el método de `trends.arima_forecast`.

  1. Estacionariedad: ADF (H0: raíz unitaria → hay que diferenciar) y KPSS (H0: estacionaria) sobre la
     serie en nivel y diferenciada, con constante y con constante + tendencia.
  2. Selección del modelo con d fijo (el que indican las pruebas) y comparación por AICc entre modelos
     con el mismo d (con d distinto la verosimilitud se calcula sobre datos distintos).
  3. Validación fuera de muestra: se ajusta hasta 2021 y se pronostica 2022–2024; errores (MAE, RMSE, MAPE),
     cobertura del IC 95 % y comparación con pronósticos de referencia (ingenuo, ingenuo con deriva, Poisson).
  4. Residuos del modelo elegido: Ljung-Box (autocorrelación), Jarque-Bera y Shapiro-Wilk (normalidad),
     media cero (t), heterocedasticidad (statsmodels) y ACF/PACF de los residuos.

    python benchmark/series_tiempo/diagnostico_arima.py --session Agrovoltaics
"""

import argparse
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
warnings.simplefilter("ignore")


def load_series(session: str) -> tuple[np.ndarray, np.ndarray]:
    from src.layer5_network.communities import analyze
    r = analyze(str(ROOT / "data" / "sessions" / session / "db" / "bibliometria.db"))
    s = r["total_series"]
    years = np.array(sorted(s))
    return years, np.array([s[y] for y in years], dtype=float)


# ── 1. Estacionariedad ──────────────────────────────────────────────────────────

def stationarity(y: np.ndarray, max_lag: int = 1) -> list[dict]:
    """
    ADF con rezagos fijos (0 y `max_lag`): con 18 datos, el autolag por AIC elegía 7 rezagos y el test pierde
    casi toda su potencia. KPSS con 1 rezago (el automático da lo mismo o 2). KPSS solo tabula p entre 0,01 y 0,10.
    """
    from statsmodels.tsa.stattools import adfuller, kpss
    out = []
    for tname, base in (("conteos", y), ("log(1+y)", np.log1p(y))):
        for name, x in (("nivel", base), ("1.ª dif.", np.diff(base)), ("2.ª dif.", np.diff(base, 2))):
            for reg, label in (("c", "constante"), ("ct", "const. + tendencia")):
                adf = [adfuller(x, maxlag=l, regression=reg, autolag=None) for l in (0, max_lag)]
                kp = kpss(x, regression=reg, nlags=1)
                out.append({"transf": tname, "serie": name, "spec": label, "n": len(x),
                            "adf0": adf[0][:2], "adf1": adf[1][:2], "adf_cv5": adf[0][4]["5%"],
                            "kpss_stat": kp[0], "kpss_p": kp[1], "kpss_cv5": kp[3]["5%"]})
    return out


# ── 2. Modelos candidatos ───────────────────────────────────────────────────────

def aicc(fit, n: int) -> float:
    k = len(fit.params)
    return fit.aic + 2 * k * (k + 1) / max(n - k - 1, 1)


# Familias que dejan abiertas las pruebas de estacionariedad: (nombre, logaritmo, d, términos deterministas)
# Con d = 1, 't' es la deriva (pendiente media de la serie); con d = 2 statsmodels solo admite 'n'.
FAMILIES = [("Conteos, d = 1", False, 1, ("n", "t")),
            ("Conteos, d = 2", False, 2, ("n",)),
            ("log(1+y), d = 1", True, 1, ("n", "t")),
            ("log(1+y), d = 2", True, 2, ("n",))]


def candidates(y: np.ndarray, d: int, log: bool = False, trends=("n", "t")) -> list[dict]:
    """Todos los ARIMA(p,d,q) con p,q ≤ 2 de una familia, ordenados por AICc (todos con el mismo d y transformación)."""
    from statsmodels.tsa.arima.model import ARIMA
    x = np.log1p(y) if log else y
    rows = []
    for tr in trends:
        for p in range(3):
            for q in range(3):
                try:
                    fit = ARIMA(x, order=(p, d, q), trend=tr).fit()
                except Exception:
                    continue
                if np.isfinite(fit.aic) and fit.mle_retvals.get("converged", True):
                    rows.append({"order": (p, d, q), "trend": tr, "log": log, "aic": fit.aic,
                                 "aicc": aicc(fit, len(x) - d), "bic": fit.bic, "fit": fit})
    return sorted(rows, key=lambda r: r["aicc"])


def forecast(c: dict, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Pronóstico y IC 95 % en la escala de conteos (en log: expm1 de la media y de los límites)."""
    fc = c["fit"].get_forecast(steps=h)
    mean, ci = np.asarray(fc.predicted_mean), np.asarray(fc.conf_int(alpha=0.05))
    if c["log"]:
        mean, ci = np.expm1(mean), np.expm1(ci)
    return np.clip(mean, 0, None), np.clip(ci, 0, None)


def label(c: dict) -> str:
    deriva = {"n": "", "t": " con deriva", "c": " con constante", "ct": " con tendencia"}[c["trend"]]
    return f"{'log(1+y) ' if c['log'] else ''}ARIMA{c['order']}{deriva}"


# ── 3. Validación fuera de muestra ──────────────────────────────────────────────

def errors(actual: np.ndarray, pred: np.ndarray) -> dict:
    e = actual - pred
    return {"mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2))),
            "mape": float(np.mean(np.abs(e) / np.where(actual == 0, np.nan, actual)) * 100)}


def baselines(train: np.ndarray, h: int) -> dict[str, np.ndarray]:
    import statsmodels.api as sm
    t = np.arange(len(train))
    pois = sm.GLM(train, sm.add_constant(t), family=sm.families.Poisson()).fit()
    future = np.arange(len(train), len(train) + h)
    drift = (train[-1] - train[0]) / (len(train) - 1)
    return {"Ingenuo (último valor)": np.repeat(train[-1], h),
            "Ingenuo con deriva": train[-1] + drift * np.arange(1, h + 1),
            "Regresión de Poisson (tendencia exponencial)": pois.predict(sm.add_constant(future, has_constant="add"))}


def holdout(y: np.ndarray, h: int, top: int = 3) -> tuple[list[dict], dict]:
    """Ajusta cada familia solo con el entrenamiento, elige por AICc y pronostica los últimos h años."""
    train, test = y[:-h], y[-h:]
    rows = []
    for fam, log, d, trends in FAMILIES:
        for rank, c in enumerate(candidates(train, d, log, trends)[:top], 1):
            mean, ci = forecast(c, h)
            rows.append({**c, "family": fam, "rank": rank, "pred": mean, "ci": ci, **errors(test, mean),
                         "coverage": int(np.sum((test >= ci[:, 0]) & (test <= ci[:, 1])))})
    # El modelo que usa hoy el agente (búsqueda con d ∈ {0,1} y AIC), ajustado solo con el entrenamiento
    cur = agent_select(train, h)
    base = {k: {"pred": v, **errors(test, v)} for k, v in baselines(train, h).items()}
    if cur["ok"]:
        pred = np.array([f["mean"] for f in cur["forecast"]])
        ci = np.array([[f["low"], f["high"]] for f in cur["forecast"]])
        base[f"Agente (regla vigente): ARIMA{cur["order"]}"] = {
            "pred": pred, **errors(test, pred), "coverage": int(np.sum((test >= ci[:, 0]) & (test <= ci[:, 1]))),
            "ci": ci}
    return rows, base


# Modelos fijos que se comparan en el origen móvil y en los residuos, en conteos y en log(1+y)
_ORDERS = [((1, 1, 0), "n"), ((0, 1, 0), "t"), ((1, 1, 0), "t"), ((0, 2, 0), "n"), ((0, 2, 1), "n"), ((1, 2, 0), "n")]
FIXED = [(label({"order": o, "trend": t, "log": log}), log, o, t) for log in (False, True) for o, t in _ORDERS]


def agent_select(train: np.ndarray, h: int) -> dict:
    """La regla vigente del agente (trends.arima_forecast), sin sus mínimos de años/artículos. Hasta el 2026-10-20 era AIC con d ∈ {0,1} en conteos; desde entonces, log(1+y) ARIMA(p,1,q) con deriva, p,q ≤ 1 por AICc."""
    from src.layer5_network import trends
    old = trends.ARIMA_MIN_YEARS, trends.ARIMA_MIN_ARTICLES
    trends.ARIMA_MIN_YEARS = trends.ARIMA_MIN_ARTICLES = 0
    try:
        return trends.arima_forecast({i: v for i, v in enumerate(train)}, horizon=h)
    finally:
        trends.ARIMA_MIN_YEARS, trends.ARIMA_MIN_ARTICLES = old


def fit_fixed(y: np.ndarray, log: bool, order: tuple, trend: str) -> dict:
    from statsmodels.tsa.arima.model import ARIMA
    x = np.log1p(y) if log else y
    fit = ARIMA(x, order=order, trend=trend).fit()
    return {"order": order, "trend": trend, "log": log, "fit": fit, "aicc": aicc(fit, len(x) - order[1])}


def rolling_origin(y: np.ndarray, years: np.ndarray, first_end: int, h: int = 3) -> dict:
    """
    Validación con origen móvil: para cada año de corte desde `first_end` se ajusta con los datos hasta ese año y
    se pronostican los h siguientes (los que existan). Errores por horizonte y cobertura del IC 95 %.
    """
    def agent(train, hh):
        cur = agent_select(train, hh)
        return (np.array([f["mean"] for f in cur["forecast"]]),
                np.array([[f["low"], f["high"]] for f in cur["forecast"]]), f"{cur['order']}")

    def family(log, d, trends):
        def run(train, hh):
            c = candidates(train, d, log, trends)[0]
            return (*forecast(c, hh), label(c))
        return run

    procedures = [("Agente: regla vigente de trends.arima_forecast, reelegida en cada corte", agent)]
    procedures += [(f"{fam}: mejor AICc en cada corte", family(log, d, trends)) for fam, log, d, trends in FAMILIES]
    procedures += [(name, (lambda log, order, trend: lambda train, hh:
                           (*forecast(fit_fixed(train, log, order, trend), hh), ""))(log, order, trend))
                   for name, log, order, trend in FIXED]

    out = {}
    cuts = [i for i, yr in enumerate(years) if yr >= first_end and i < len(y) - 1]
    for name, proc in procedures:
        errs = {k: [] for k in range(1, h + 1)}
        cover, chosen = [], []
        for i in cuts:
            train, test = y[:i + 1], y[i + 1:i + 1 + h]
            try:
                mean, ci, desc = proc(train, len(test))
            except Exception:
                continue
            chosen.append(desc)
            for k, (t, m) in enumerate(zip(test, mean), 1):
                errs[k].append(t - m)
            cover += list((test >= ci[:, 0]) & (test <= ci[:, 1]))
        allerr = np.concatenate([np.array(v) for v in errs.values() if v])
        out[name] = {"mae_h": {k: float(np.mean(np.abs(v))) for k, v in errs.items() if v},
                     "mae": float(np.mean(np.abs(allerr))), "rmse": float(np.sqrt(np.mean(allerr ** 2))),
                     "bias": float(np.mean(allerr)), "coverage": float(np.mean(cover)), "n": len(allerr),
                     "cuts": [int(years[i]) for i in cuts], "chosen": [c for c in chosen if c]}
    for k, v in baselines_rolling(y, years, cuts, h).items():
        out[k] = v
    return out


def baselines_rolling(y, years, cuts, h):
    out = {}
    for name in ("Ingenuo (último valor)", "Ingenuo con deriva", "Regresión de Poisson (tendencia exponencial)"):
        allerr = []
        for i in cuts:
            train, test = y[:i + 1], y[i + 1:i + 1 + h]
            pred = baselines(train, len(test))[name]
            allerr += list(test - pred)
        allerr = np.array(allerr)
        out[name] = {"mae": float(np.mean(np.abs(allerr))), "rmse": float(np.sqrt(np.mean(allerr ** 2))),
                     "bias": float(np.mean(allerr)), "coverage": None, "n": len(allerr)}
    return out


# ── 4. Residuos ─────────────────────────────────────────────────────────────────

def residual_tests(fit, d: int) -> dict:
    from scipy import stats
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.stats.stattools import jarque_bera
    from statsmodels.tsa.stattools import acf, pacf
    # Los primeros d residuos salen de la inicialización difusa (no son errores de pronóstico): se descartan
    r = np.asarray(fit.resid)[d:]
    n = len(r)
    p, _, q = fit.model.order
    lags = [l for l in (3, 4, 5, 6) if l < n // 2]
    lb = acorr_ljungbox(r, lags=lags, model_df=p + q, return_df=True)
    jb_stat, jb_p, skew, kurt = jarque_bera(r)
    sw = stats.shapiro(r)
    tt = stats.ttest_1samp(r, 0.0)
    het = fit.test_heteroskedasticity(method="breakvar")[0]
    nl = min(6, n // 2 - 1)
    return {"n": n, "mean": float(r.mean()), "sd": float(r.std(ddof=1)), "t_p": float(tt.pvalue),
            "ljung_box": [(int(l), float(s), float(pv)) for l, s, pv in zip(lags, lb["lb_stat"], lb["lb_pvalue"])],
            "jb_stat": float(jb_stat), "jb_p": float(jb_p), "skew": float(skew), "kurt": float(kurt),
            "sw_stat": float(sw.statistic), "sw_p": float(sw.pvalue),
            "het_stat": float(het[0]), "het_p": float(het[1]),
            "acf": acf(r, nlags=nl)[1:], "pacf": pacf(r, nlags=nl)[1:], "band": 1.96 / np.sqrt(n), "resid": r}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="Agrovoltaics")
    ap.add_argument("--h", type=int, default=3, help="años fuera de muestra")
    a = ap.parse_args()
    years, y = load_series(a.session)
    print(dict(zip(years.tolist(), y.astype(int).tolist())))
    print("\n== Estacionariedad (serie completa) ==")
    for r in stationarity(y):
        print(f"{r['transf']:9} {r['serie']:9} {r['spec']:19} n={r['n']:2} | ADF(0) {r['adf0'][0]:6.2f} p={r['adf0'][1]:.3f}"
              f" ADF(1) {r['adf1'][0]:6.2f} p={r['adf1'][1]:.3f} | KPSS {r['kpss_stat']:.3f} p={r['kpss_p']:.3f}")
    print(f"\n== Estacionariedad (solo entrenamiento, hasta {years[-a.h - 1]}) ==")
    for r in stationarity(y[:-a.h]):
        print(f"{r['transf']:9} {r['serie']:9} {r['spec']:19} n={r['n']:2} | ADF(0) {r['adf0'][0]:6.2f} p={r['adf0'][1]:.3f}"
              f" ADF(1) {r['adf1'][0]:6.2f} p={r['adf1'][1]:.3f} | KPSS {r['kpss_stat']:.3f} p={r['kpss_p']:.3f}")
    print(f"\n== Fuera de muestra: real {years[-a.h:].tolist()} = {y[-a.h:].tolist()} ==")
    rows, base = holdout(y, a.h)
    for r in rows:
        print(f"{r['family']:16} #{r['rank']} {label(r):38} AICc {r['aicc']:6.1f} | pred {np.round(r['pred'], 1)} "
              f"IC {np.round(r['ci'], 1).tolist()} | MAE {r['mae']:.2f} RMSE {r['rmse']:.2f} MAPE {r['mape']:.0f}% "
              f"cobertura {r['coverage']}/{a.h}")
    for k, v in base.items():
        print(f"{k:55} pred {np.round(v['pred'], 1)} | MAE {v['mae']:.2f} RMSE {v['rmse']:.2f} MAPE {v['mape']:.0f}%"
              + (f" cobertura {v['coverage']}/{a.h}" if "coverage" in v else ""))
    print(f"\n== Origen móvil (cortes desde {years[0] + 9}: al menos 10 años de entrenamiento, pronóstico a 1–{a.h} años) ==")
    ro = rolling_origin(y, years, int(years[0]) + 9, a.h)
    naive = ro["Ingenuo (último valor)"]["mae"]
    for k, v in ro.items():
        cov = "" if v["coverage"] is None else f" cobertura IC95 {v['coverage']:.0%} MAE por horizonte " \
                                               f"{[round(x, 2) for x in v['mae_h'].values()]}"
        ch = f" | elegidos {v['chosen']}" if v.get("chosen") else ""
        print(f"{k:58} MAE {v['mae']:.2f} (×{v['mae'] / naive:.2f} ingenuo) RMSE {v['rmse']:.2f} "
              f"sesgo {v['bias']:+.2f} (n={v['n']}){cov}{ch}")
    print("\n== Residuos (serie completa; se descartan los d primeros) ==")
    for name, log, order, trend in FIXED:
        c = fit_fixed(y, log, order, trend)
        r = residual_tests(c["fit"], order[1])
        print(f"{name}: AICc {c['aicc']:.1f} | params {np.round(c['fit'].params, 3).tolist()} "
              f"p {np.round(c['fit'].pvalues, 3).tolist()}")
        print(f"    n={r['n']} media {r['mean']:+.2f} (t p={r['t_p']:.2f}) | Ljung-Box p "
              f"{[(l, round(p, 3)) for l, _, p in r['ljung_box']]} | Jarque-Bera p={r['jb_p']:.2f} "
              f"Shapiro p={r['sw_p']:.2f} | heteroced. p={r['het_p']:.2f} | ACF {np.round(r['acf'], 2).tolist()} "
              f"(banda ±{r['band']:.2f})")
    print("\n== Serie completa: mejor modelo por familia ==")
    for fam, log, d, trends in FAMILIES:
        for c in candidates(y, d, log, trends)[:3]:
            mean, ci = forecast(c, 3)
            print(f"{fam:16} {label(c):38} AICc {c['aicc']:6.1f} params {np.round(c['fit'].params, 3).tolist()} "
                  f"| {years[-1] + 1}-{years[-1] + 3}: {np.round(mean, 1).tolist()} IC {np.round(ci, 1).tolist()}")
