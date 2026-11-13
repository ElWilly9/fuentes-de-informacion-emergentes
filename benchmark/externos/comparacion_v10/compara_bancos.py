"""Compara V10 sin consenso (wt_cmp_v10, SQL_ENSEMBLE=0) con las corridas anteriores (V8) de Spider, BIRD y HotpotQA, por pregunta."""
import json, statistics as st
from math import comb
from pathlib import Path
L = Path(r"C:\Users\PAE ML SQL RAG\Documents\limpio")
OLD = L / "fuentes-de-informacion-emergentes/benchmark/externos"
NEW = L / "wt_cmp_v10/benchmark/externos"

def load(p, key):
    return {r[key]: r for r in map(json.loads, Path(p).read_text(encoding="utf-8").splitlines() if True else []) if r.get("em") is not None or True}

def rd(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]

def mcn(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)

def pair(old, new, f):
    ids = [i for i in old if i in new]
    b = sum(1 for i in ids if f(old[i]) and not f(new[i]))   # V8 sí, V10 no
    c = sum(1 for i in ids if f(new[i]) and not f(old[i]))   # V10 sí, V8 no
    return len(ids), sum(f(old[i]) for i in ids), sum(f(new[i]) for i in ids), b, c, mcn(b, c)

def lat(d, k="latency_s"):
    v = [r[k] for r in d.values() if r.get(k) is not None]
    return round(st.mean(v), 1), round(st.median(v), 1)

def calls(d):
    v = [r["llm_calls"] for r in d.values() if r.get("llm_calls") is not None]
    return round(st.mean(v), 2) if v else None

out = {}
# Spider
so = {r["idx"]: r for r in rd(OLD / "spider/results/predicciones_agente2_n300_seed42_glm4-9b_dual-ddl.jsonl")}
sn = {r["idx"]: r for r in rd(NEW / "spider/results/predicciones_agente2_n300_seed42_glm4-9b_v10sc.jsonl")}
out["spider_EX"] = pair(so, sn, lambda r: int(r["ex"]))
out["spider_lat"] = {"V8": lat(so, "latency_s"), "V10sc": lat(sn, "latency_s")}
out["spider_calls"] = {"V8": calls(so), "V10sc": calls(sn)}
out["spider_errores"] = {"V8": sum("error" in r for r in so.values()), "V10sc": sum("error" in r for r in sn.values())}
# BIRD: probar candidatas de V8
cands = {}
for f in (OLD / "bird/results").glob("predicciones_agente2_n300_seed42_glm4-9b*.jsonl"):
    d = {r["idx"]: r for r in rd(f)}
    cands[f.name] = (len(d), round(sum(r["ex"] for r in d.values()) / len(d), 3), lat(d)[0])
out["bird_candidatas_V8"] = cands
bn = {r["idx"]: r for r in rd(NEW / "bird/results/predicciones_agente2_n300_seed42_glm4-9b_v10sc.jsonl")}
bo = {r["idx"]: r for r in rd(OLD / "bird/results/predicciones_agente2_n300_seed42_glm4-9b_dual-ddl.jsonl")}
out["bird_EX"] = pair(bo, bn, lambda r: int(r["ex"]))
for dif in ("simple", "moderate", "challenging"):
    o = {i: r for i, r in bo.items() if r["difficulty"] == dif}
    out[f"bird_{dif}"] = pair(o, bn, lambda r: int(r["ex"]))
out["bird_lat"] = {"V8": lat(bo), "V10sc": lat(bn)}
out["bird_calls"] = {"V8": calls(bo), "V10sc": calls(bn)}
out["bird_errores"] = {"V8": sum("error" in r for r in bo.values()), "V10sc": sum("error" in r for r in bn.values())}
# HotpotQA
ho = {r["id"]: r for r in rd(OLD / "hotpotqa/results/respuestas_n300_seed42_glm4-9b.jsonl")}
hn = {r["id"]: r for r in rd(NEW / "hotpotqa/results/respuestas_n300_seed42_glm4-9b.jsonl")}
out["hotpot_EM"] = pair(ho, hn, lambda r: int(r["em"] >= 0.999))
out["hotpot_F1"] = {"V8": round(st.mean(r["f1"] for r in ho.values()), 4), "V10sc": round(st.mean(r["f1"] for r in hn.values()), 4)}
out["hotpot_respuestas_distintas"] = sum(ho[i]["response"] != hn[i]["response"] for i in ho if i in hn)
out["hotpot_lat"] = {"V8": lat(ho), "V10sc": lat(hn)}
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
Path("comparacion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

import csv
with open("resultados_por_pregunta.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["banco", "id", "dificultad_o_tipo", "V8_acierto", "V10sc_acierto", "V8_s", "V10sc_s", "V8_llamadas", "V10sc_llamadas"])
    for i in sn: w.writerow(["spider", i, so[i].get("difficulty", ""), so[i]["ex"], sn[i]["ex"], so[i]["latency_s"], sn[i]["latency_s"], so[i].get("llm_calls"), sn[i].get("llm_calls")])
    for i in bn: w.writerow(["bird", i, bn[i].get("difficulty", ""), bo[i]["ex"], bn[i]["ex"], bo[i]["latency_s"], bn[i]["latency_s"], bo[i].get("llm_calls"), bn[i].get("llm_calls")])
    for i in hn: w.writerow(["hotpotqa", i, hn[i].get("type", ""), int(ho[i]["em"] >= .999), int(hn[i]["em"] >= .999), ho[i]["latency_s"], hn[i]["latency_s"], "", ""])
