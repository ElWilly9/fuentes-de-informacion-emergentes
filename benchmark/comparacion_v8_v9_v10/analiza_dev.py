"""Sets de desarrollo + bancos externos: V8 / V9 / V10 sin consenso. Acierto = puntaje 1,0; McNemar exacto bilateral."""
import json, statistics as st, csv
from math import comb
from pathlib import Path
HERE = Path(__file__).resolve().parent
L = Path(r"C:\Users\PAE ML SQL RAG\Documents\limpio")
SETS = "plantillas prueba prueba2 prueba3 prueba4 coffee generalizacion".split()
CFG = {"v8": "V8", "v9": "V9", "v10_sinconsenso": "V10 sin consenso", "v10": "V10 con consenso"}
ok = lambda r: int(r["puntaje"] >= .999)
rd = lambda p: [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
def mcn(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
D = {(c, s): {r["id"]: r for r in rd(HERE / f"results_dev/{c}__{s}.jsonl")} for c in CFG for s in SETS}
out = ["### Sets de desarrollo: aciertos exactos (puntaje 1,0)", "",
       "| Set | n | V8 | V9 | V10 sin consenso | V10 con consenso | s/preg V8 · V9 · V10sc · V10c |", "|---|---|---|---|---|---|---|"]
tot = {c: 0 for c in CFG}; N = 0
for s in SETS:
    n = len(D[("v8", s)]); N += n
    row = {c: sum(ok(r) for r in D[(c, s)].values()) for c in CFG}
    for c in CFG: tot[c] += row[c]
    lat = " · ".join(f"{st.mean(r['latencia_s'] for r in D[(c, s)].values()):.1f}" for c in CFG)
    out.append(f"| {s} | {n} | {row['v8']} | {row['v9']} | {row['v10_sinconsenso']} | {row['v10']} | {lat} |")
lat = " · ".join(f"{st.mean(r['latencia_s'] for s in SETS for r in D[(c, s)].values()):.1f}" for c in CFG)
out.append(f"| **Total** | {N} | **{tot['v8']}** | **{tot['v9']}** | **{tot['v10_sinconsenso']}** | **{tot['v10']}** | {lat} |")
out += ["", "Mediana s/preg y llamadas LLM/preg (todos los sets): " + "; ".join(
    f"{CFG[c]}: {st.median(r['latencia_s'] for s in SETS for r in D[(c, s)].values()):.1f} s, {st.mean(r['llm_calls'] for s in SETS for r in D[(c, s)].values()):.2f} llamadas" for c in CFG), "",
    "### McNemar exacto pareado (b = A sí / B no; c = B sí / A no)", "", "| A vs B | set | n | A | B | b | c | p |", "|---|---|---|---|---|---|---|---|"]
mc = []
for A, B in [("v9", "v8"), ("v10_sinconsenso", "v8"), ("v10_sinconsenso", "v9"), ("v10", "v8"), ("v10", "v9"), ("v10", "v10_sinconsenso")]:
    for s in SETS + ["combinado"]:
        ss = SETS if s == "combinado" else [s]
        pr = [(ok(D[(A, x)][i]), ok(D[(B, x)][i])) for x in ss for i in D[(A, x)]]
        b = sum(1 for x, y in pr if x and not y); c = sum(1 for x, y in pr if y and not x)
        mc.append(dict(A=A, B=B, set=s, n=len(pr), A_ok=sum(x for x, _ in pr), B_ok=sum(y for _, y in pr), b=b, c=c, p=round(mcn(b, c), 4)))
        out.append(f"| {CFG[A]} vs {CFG[B]} | {s} | {len(pr)} | {mc[-1]['A_ok']} | {mc[-1]['B_ok']} | {b} | {c} | {mcn(b, c):.4f} |")
        if s == "combinado":
            ss2 = [x for x in SETS if x != "generalizacion"]
            pr2 = [(ok(D[(A, x)][i]), ok(D[(B, x)][i])) for x in ss2 for i in D[(A, x)]]
            b2 = sum(1 for x, y in pr2 if x and not y); c2 = sum(1 for x, y in pr2 if y and not x)
            mc.append(dict(A=A, B=B, set="combinado sin generalizacion", n=len(pr2), A_ok=sum(x for x, _ in pr2), B_ok=sum(y for _, y in pr2), b=b2, c=c2, p=round(mcn(b2, c2), 4)))
            out.append(f"| {CFG[A]} vs {CFG[B]} | **combinado sin generalización** | {len(pr2)} | {mc[-1]['A_ok']} | {mc[-1]['B_ok']} | {b2} | {c2} | {mcn(b2, c2):.4f} |")
# externos
ex = ["", "### Bancos externos (300, semilla 42)", "", "| Banco · métrica | V8 | V9 | V10 sin consenso |", "|---|---|---|---|"]
O = L / "fuentes-de-informacion-emergentes/benchmark/externos"; N10 = L / "wt_cmp_v10/benchmark/externos"; N9 = L / "wt_cmp_v9/benchmark/externos"
sp = {"v8": {r["idx"]: r for r in rd(O / "spider/results/predicciones_agente2_n300_seed42_glm4-9b_dual-ddl.jsonl")},
      "v9": {r["idx"]: r for r in rd(N9 / "spider/results/predicciones_agente2_n300_seed42_glm4-9b_v9.jsonl")},
      "v10": {r["idx"]: r for r in rd(N10 / "spider/results/predicciones_agente2_n300_seed42_glm4-9b_v10sc.jsonl")}}
bd = {"v8": {r["idx"]: r for r in rd(O / "bird/results/predicciones_agente2_n300_seed42_glm4-9b_dual-ddl.jsonl")},
      "v9": {r["idx"]: r for r in rd(N9 / "bird/results/predicciones_agente2_n300_seed42_glm4-9b_v9.jsonl")},
      "v10": {r["idx"]: r for r in rd(N10 / "bird/results/predicciones_agente2_n300_seed42_glm4-9b_v10sc.jsonl")}}
hp = {"v8": {r["id"]: r for r in rd(O / "hotpotqa/results/respuestas_n300_seed42_glm4-9b.jsonl")},
      "v9": {r["id"]: r for r in rd(N9 / "hotpotqa/results/respuestas_n300_seed42_glm4-9b_v9.jsonl")},
      "v10": {r["id"]: r for r in rd(N10 / "hotpotqa/results/respuestas_n300_seed42_glm4-9b.jsonl")}}
f3 = lambda x: f"{x:.3f}"
ex.append("| Spider EX | " + " | ".join(f"{sum(r['ex'] for r in sp[v].values())/300:.3f}" for v in ("v8", "v9", "v10")) + " |")
ex.append("| BIRD EX | " + " | ".join(f"{sum(r['ex'] for r in bd[v].values())/300:.3f}" for v in ("v8", "v9", "v10")) + " |")
ex.append("| HotpotQA EM · F1 | " + " | ".join(f"{sum(r['em']>=.999 for r in hp[v].values())/300:.3f} · {st.mean(r['f1'] for r in hp[v].values()):.3f}" for v in ("v8", "v9", "v10")) + " |")
ex.append("| s/preg media (Spider · BIRD) — OJO: días distintos | " + " | ".join(f"{st.mean(r['latency_s'] for r in sp[v].values()):.1f} · {st.mean(r['latency_s'] for r in bd[v].values()):.1f}" for v in ("v8", "v9", "v10")) + " |")
ex += ["", "McNemar pareado (V9 vs V8 / V9 vs V10sc):", ""]
for nm, d, key in (("Spider EX", sp, lambda r: int(r["ex"])), ("BIRD EX", bd, lambda r: int(r["ex"])), ("HotpotQA EM", hp, lambda r: int(r["em"] >= .999))):
    for a, b in (("v9", "v8"), ("v9", "v10")):
        bb = sum(1 for i in d[a] if key(d[a][i]) and not key(d[b][i])); cc = sum(1 for i in d[a] if key(d[b][i]) and not key(d[a][i]))
        ex.append(f"- {nm}: {a} vs {b}: b={bb}, c={cc}, p={mcn(bb, cc):.4f}")
(HERE / "tablas_dev_externos.md").write_text("\n".join(out + ex) + "\n", encoding="utf-8")
json.dump(mc, open(HERE / "mcnemar_dev.json", "w"), indent=1)
with open(HERE / "resultados_por_pregunta_dev.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["set", "id", "corpus", "tipo"] + [f"{c}_{k}" for c in CFG for k in ("acierto", "puntaje", "s", "llamadas")])
    for s in SETS:
        for i, m in D[("v8", s)].items():
            w.writerow([s, i, m["corpus"], m["tipo"]] + [v for c in CFG for v in (ok(D[(c, s)][i]), D[(c, s)][i]["puntaje"], D[(c, s)][i]["latencia_s"], D[(c, s)][i]["llm_calls"])])
print("\n".join(out + ex))
