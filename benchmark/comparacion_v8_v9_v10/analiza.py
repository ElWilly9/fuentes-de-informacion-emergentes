"""
analiza.py — Tablas, McNemar exacto y CSV de la comparación V8/V9/V10 (+ glm4 solo, + V10 sin consenso).
Acierto = puntaje >= 0,999 (igual que compara_heldout4/5). McNemar exacto bilateral sobre las discordantes.
Salida: resumen.json, resultados_por_pregunta.csv, tablas.md (insumos del INFORME.md).
"""
import csv
import json
import statistics as st
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
LIMPIO = HERE.parents[5]
CONFIGS = ["v8", "glm4solo", "v9", "v10", "v10_sinconsenso"]
NOMBRE = {"v8": "V8", "glm4solo": "glm4 solo", "v9": "V9", "v10": "V10", "v10_sinconsenso": "V10 sin consenso"}
SETS = [3, 4, 5]
TIPOS = ["SQL", "Híbrida", "RAG"]


def load(p):
    p = Path(p)
    if not p.exists():
        return None
    return {json.loads(l)["id"]: json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


ok = lambda r: int(r["puntaje"] >= 0.999)
data = {(c, s): load(RES / f"{c}__set{s}.jsonl") for c in CONFIGS for s in SETS}
qids = {}
for s in SETS:
    base = next(d for (c, ss), d in data.items() if ss == s and d)
    qids[s] = list(base)


def stats(rs):
    lat = [r["latencia_s"] for r in rs]
    calls = [r.get("llm_calls", 0) for r in rs]
    return {"n": len(rs), "aciertos": sum(ok(r) for r in rs), "puntaje": round(sum(r["puntaje"] for r in rs) / len(rs), 3),
            "s_media": round(st.mean(lat), 1), "s_mediana": round(st.median(lat), 1),
            "llamadas_media": round(st.mean(calls), 2), "llamadas_mediana": st.median(calls),
            "errores": sum(1 for r in rs if r.get("error"))}


lines = []
summary = {}
for s in SETS + ["comb"]:
    lines += [f"### {'Set ' + str(s) if s != 'comb' else 'Combinado (3 sets)'}", "",
              "| Configuración | Aciertos | % | SQL | Híbrida | RAG | s/preg (media · mediana) | llamadas LLM/preg (media · mediana) |",
              "|---|---|---|---|---|---|---|---|"]
    for c in CONFIGS:
        sets = SETS if s == "comb" else [s]
        rs = [r for ss in sets if data[(c, ss)] for r in data[(c, ss)].values()]
        if not rs or (s == "comb" and any(data[(c, ss)] is None or len(data[(c, ss)]) < len(qids[ss]) for ss in SETS)):
            lines.append(f"| {NOMBRE[c]} | (incompleta) | | | | | | |")
            continue
        S = stats(rs)
        cat = {}
        for t in TIPOS:
            sub = [r for r in rs if r["tipo"] == t]
            cat[t] = (sum(ok(r) for r in sub), len(sub), round(st.mean(r["latencia_s"] for r in sub), 1) if sub else None,
                      round(st.median(r["latencia_s"] for r in sub), 1) if sub else None,
                      round(st.mean(r.get("llm_calls", 0) for r in sub), 2) if sub else None)
        summary[f"{c}|{s}"] = {**S, "categorias": {t: dict(zip(["ok", "n", "s_media", "s_mediana", "llamadas_media"], v)) for t, v in cat.items()}}
        cell = lambda t: f"{cat[t][0]}/{cat[t][1]}" if cat[t][1] else "—"
        lines.append(f"| {NOMBRE[c]} | {S['aciertos']}/{S['n']} | {S['aciertos'] / S['n']:.1%} | {cell('SQL')} | {cell('Híbrida')} | "
                     f"{cell('RAG')} | {S['s_media']} · {S['s_mediana']} | {S['llamadas_media']} · {S['llamadas_mediana']} |")
    lines.append("")
    lines += ["Latencia y llamadas por categoría (media s · mediana s · llamadas/preg):", "",
              "| Configuración | SQL | Híbrida | RAG |", "|---|---|---|---|"]
    for c in CONFIGS:
        k = summary.get(f"{c}|{s}")
        if not k:
            continue
        f = lambda t: (f"{k['categorias'][t]['s_media']} · {k['categorias'][t]['s_mediana']} · {k['categorias'][t]['llamadas_media']}"
                       if k["categorias"][t]["n"] else "—")
        lines.append(f"| {NOMBRE[c]} | {f('SQL')} | {f('Híbrida')} | {f('RAG')} |")
    lines.append("")

# ── McNemar ───────────────────────────────────────────────────────────────────────────────────────────────
PAIRS = [("v10", "v8"), ("v10", "v9"), ("v9", "v8"), ("v8", "glm4solo"), ("v9", "glm4solo"), ("v10", "glm4solo"),
         ("v10", "v10_sinconsenso"), ("v10_sinconsenso", "v8"), ("v10_sinconsenso", "glm4solo")]
lines += ["### McNemar exacto pareado (acierto = puntaje 1,0; bilateral)", "",
          "| A vs B | corte | n | A acierta | B acierta | b (A sí, B no) | c (B sí, A no) | p |", "|---|---|---|---|---|---|---|---|"]
mc = []
for A, B in PAIRS:
    for s in SETS + ["comb"]:
        for corte in ["TOTAL"] + TIPOS:
            sets = SETS if s == "comb" else [s]
            pairs = []
            for ss in sets:
                dA, dB = data[(A, ss)], data[(B, ss)]
                if not dA or not dB:
                    continue
                for i in qids[ss]:
                    if i in dA and i in dB and (corte == "TOTAL" or dA[i]["tipo"] == corte):
                        pairs.append((ok(dA[i]), ok(dB[i])))
            if not pairs or (corte != "TOTAL" and s != "comb" and False):
                continue
            b = sum(1 for x, y in pairs if x and not y)
            c = sum(1 for x, y in pairs if y and not x)
            p = mcnemar_p(b, c)
            mc.append({"A": A, "B": B, "set": s, "corte": corte, "n": len(pairs), "A_ok": sum(x for x, _ in pairs),
                       "B_ok": sum(y for _, y in pairs), "b": b, "c": c, "p": round(p, 4)})
            lines.append(f"| {NOMBRE[A]} vs {NOMBRE[B]} | {corte} · {'set ' + str(s) if s != 'comb' else 'combinado'} | {len(pairs)} | "
                         f"{sum(x for x, _ in pairs)} | {sum(y for _, y in pairs)} | {b} | {c} | {p:.4f} |")
(HERE / "tablas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(HERE / "resumen.json").write_text(json.dumps({"resumen": summary, "mcnemar": mc}, ensure_ascii=False, indent=1), encoding="utf-8")

# ── CSV por pregunta ──────────────────────────────────────────────────────────────────────────────────────
cols = ["set", "id", "corpus", "tipo", "plantilla"]
for c in CONFIGS:
    cols += [f"{c}_acierto", f"{c}_puntaje", f"{c}_s", f"{c}_llamadas", f"{c}_ruta"]
with (HERE / "resultados_por_pregunta.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for s in SETS:
        for i in qids[s]:
            meta = next(data[(c, s)][i] for c in CONFIGS if data[(c, s)] and i in data[(c, s)])
            row = [s, i, meta["corpus"], meta["tipo"], meta.get("plantilla", "")]
            for c in CONFIGS:
                r = (data[(c, s)] or {}).get(i)
                row += [ok(r), r["puntaje"], r["latencia_s"], r.get("llm_calls"), r["intent"]] if r else ["", "", "", "", ""]
            w.writerow(row)

# ── reproducibilidad frente a corridas anteriores (otro momento, mismo equipo) ─────────────────────────────
FR = LIMPIO / "fuentes-de-informacion-emergentes" / ".claude" / "worktrees" / "frosty-saha-2fd9f9" / "benchmark"
PREV = {
    ("v8", 3): FR / "heldout3/results/heldout3_glm4-9b_temp0_base.jsonl" if (FR / "heldout3/results/heldout3_glm4-9b_temp0_base.jsonl").exists() else LIMPIO / "fuentes-de-informacion-emergentes/benchmark/heldout3/results/heldout3_glm4-9b_temp0_base.jsonl",
    ("glm4solo", 3): FR / "mcnemar/raw/heldout3_glm4-9b_temp0_v8solo.jsonl",
    ("v8", 4): LIMPIO / "wt_v8/benchmark/heldout4/results/heldout4_glm4-9b_temp0_v8_r1.jsonl",
    ("glm4solo", 4): LIMPIO / "wt_v8/benchmark/heldout4/results/heldout4_glm4-9b_temp0_solo_r1.jsonl",
    ("v9", 4): FR / "heldout4/results/heldout4_glm4-9b_temp0_v9_r1.jsonl",
    ("v10", 4): FR / "heldout4/results/heldout4_glm4-9b_temp0_v10dev.jsonl",
    ("v8", 5): LIMPIO / "wt_v8/benchmark/heldout5/results/heldout5_glm4-9b_temp0_v8_r1.jsonl",
    ("glm4solo", 5): LIMPIO / "wt_v8/benchmark/heldout5/results/heldout5_glm4-9b_temp0_solo_r1.jsonl",
    ("v9", 5): LIMPIO / "wt_v9/benchmark/heldout5/results/heldout5_glm4-9b_temp0_v9_r1.jsonl",
    ("v10", 5): FR / "heldout5/results/heldout5_glm4-9b_temp0_v10_r1.jsonl",
}
rl = ["### Celdas que ya existían vs esta tanda (mismo equipo, otro momento)", "",
      "| Celda | antes: aciertos | ahora: aciertos | preguntas que cambian de acierto (antes→ahora) | antes: s/preg | ahora: s/preg |",
      "|---|---|---|---|---|---|"]
prev_summary = {}
for (c, s), p in PREV.items():
    old, new = load(p), data[(c, s)]
    if not old or not new:
        rl.append(f"| {NOMBRE[c]} set {s} | (sin archivo: {p.name}) | | | | |")
        continue
    ids = [i for i in qids[s] if i in old and i in new]
    o = sum(ok(old[i]) for i in ids)
    n = sum(ok(new[i]) for i in ids)
    ch = sum(1 for i in ids if ok(old[i]) != ok(new[i]))
    up = sum(1 for i in ids if ok(new[i]) and not ok(old[i]))
    lo = sum(ok(old[i]) for i in ids)
    so = st.mean(old[i]["latencia_s"] for i in ids)
    sn = st.mean(new[i]["latencia_s"] for i in ids)
    prev_summary[f"{c}|{s}"] = {"antes": o, "ahora": n, "n": len(ids), "cambian": ch, "s_antes": round(so, 1), "s_ahora": round(sn, 1)}
    rl.append(f"| {NOMBRE[c]} set {s} | {o}/{len(ids)} | {n}/{len(ids)} | {ch} (+{up} / −{ch - up}) | {so:.1f} | {sn:.1f} |")
(HERE / "tablas.md").write_text("\n".join(lines + [""] + rl) + "\n", encoding="utf-8")
(HERE / "reproducibilidad.json").write_text(json.dumps(prev_summary, ensure_ascii=False, indent=1), encoding="utf-8")
print((HERE / "tablas.md").read_text(encoding="utf-8"))
