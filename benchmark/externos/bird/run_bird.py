"""
run_bird.py — Text-to-SQL en BIRD (dev), el referente actual de Text-to-SQL sobre una sola BD
==============================================================================================
BIRD (Li et al., NeurIPS 2023): 1.534 preguntas dev sobre 11 BDs grandes y "sucias" (nombres de columna con
espacios, valores con formatos raros). Cada pregunta trae una `evidence` (conocimiento externo: qué significa una
columna, cómo se calcula un indicador); el ranking oficial se reporta CON evidencia, y así se corre aquí.

Mismas configuraciones que run_spider.py:
  - `solo`:    prompt zero-shot en inglés (CREATE TABLE + evidencia + pregunta → SQL), un intento.
  - `agente2`: el flujo SQL del agente (generate → execute → refine → synthesize → reflect) con el esquema completo de
    la BD en el SchemaContext (sin Capa 1) y la evidencia añadida a la pregunta.

EX como el evaluador oficial de BIRD (evaluation.py): conjunto de filas del SQL predicho == conjunto de filas del
gold, con tiempo máximo por consulta.

    python benchmark/externos/bird/run_bird.py --mode solo --n 300
    python benchmark/externos/bird/run_bird.py --mode agente2 --n 300
    python benchmark/externos/bird/run_bird.py --report --n 300
Las predicciones se guardan pregunta a pregunta: si se corta, el mismo comando retoma.
"""

import argparse
import collections
import json
import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
BIRD = HERE / "data" / "unz" / "dev_20240627"
DB_DIR = BIRD / "dev_databases"
RESULTS = HERE / "results"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
QUERY_TIMEOUT_S = 30

# NO_THINK=1: modelos que razonan (qwen3) sin razonamiento, como glm4 (igual que en run_spider.py)
if os.getenv("NO_THINK") == "1":
    from langchain_ollama import ChatOllama as _ChatOllama
    _ChatOllama.model_fields["reasoning"].default = False
    _ChatOllama.model_rebuild(force=True)

SOLO_SYSTEM = "You are an expert in SQLite. Write a single SQLite query that answers the question. " \
              "Reply with the SQL only, without explanation or markdown."
SOLO_USER = "{schema}\n\n-- External knowledge: {evidence}\n-- Question: {question}\n-- SQL:"


def load_sample(n: int, seed: int) -> list[dict]:
    dev = json.loads((BIRD / "dev.json").read_text(encoding="utf-8"))
    for i, q in enumerate(dev):
        q["idx"] = i
    return random.Random(seed).sample(dev, min(n, len(dev)))


def db_path(db_id: str) -> str:
    return str(DB_DIR / db_id / f"{db_id}.sqlite")


def create_statements(db_id: str) -> str:
    conn = sqlite3.connect(db_path(db_id))
    rows = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL").fetchall()
    conn.close()
    return "\n\n".join(r[0].strip() + ";" for r in rows)


def with_evidence(q: dict) -> str:
    return f"{q['question']}\nConocimiento externo (evidence): {q['evidence']}" if q.get("evidence") else q["question"]


def run_query(db: str, sql: str):
    """Filas del SQL o None si falla o pasa de QUERY_TIMEOUT_S (como el evaluador oficial)."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    deadline = time.time() + QUERY_TIMEOUT_S
    conn.set_progress_handler(lambda: int(time.time() > deadline), 10000)
    try:
        return conn.execute(sql).fetchall()
    except Exception:
        return None
    finally:
        conn.close()


def exec_match(db: str, pred: str, gold: str) -> int:
    p = run_query(db, pred)
    return int(p is not None and set(p) == set(run_query(db, gold) or []))


def predict_solo(q: dict, llm) -> dict:
    from src.layer2_agent.sql_generator import extract_sql_from_response
    response = llm.invoke([
        {"role": "system", "content": SOLO_SYSTEM},
        {"role": "user", "content": SOLO_USER.format(schema=create_statements(q["db_id"]),
                                                     evidence=q.get("evidence") or "-", question=q["question"])},
    ]).content
    return {"pred": one_line(extract_sql_from_response(response)), "llm_calls": 1}


def one_line(sql: str) -> str:
    import re
    return re.sub(r"\s+", " ", sql or "").strip().rstrip(";").strip() or "SELECT"


def predict_agente(q: dict, table: dict) -> dict:
    """El bucle SQL del agente, con la evidencia añadida a la pregunta (ver run_spider.predict_agente)."""
    sys.path.insert(0, str(HERE.parent / "spider"))
    import run_spider
    run_spider.db_path = db_path          # el SchemaContext lee los tipos de columna de la BD de BIRD
    q = {**q, "question": with_evidence(q)}
    return run_spider.predict_agente(q, table)


def _tag(mode: str, n: int, seed: int, model: str) -> str:
    return f"{mode}_n{n}_seed{seed}_{model.replace(':', '-')}"


def run(mode: str, n: int, seed: int, model: str) -> None:
    from langchain_ollama import ChatOllama
    sample = load_sample(n, seed)
    tables = {t["db_id"]: t for t in json.loads((BIRD / "dev_tables.json").read_text(encoding="utf-8"))}
    RESULTS.mkdir(exist_ok=True)
    cache = RESULTS / f"predicciones_{_tag(mode, n, seed, model)}.jsonl"
    done = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done[rec["idx"]] = rec
    llm = ChatOllama(base_url=OLLAMA_URL, model=model, temperature=0.0)
    for q in sample:
        if q["idx"] in done:
            continue
        t0 = time.time()
        try:
            out = predict_solo(q, llm) if mode == "solo" else predict_agente(q, tables[q["db_id"]])
        except Exception as e:  # p. ej. Ollama rechaza un prompt > num_ctx: cuenta como fallo
            out = {"pred": "SELECT", "error": f"{type(e).__name__}: {str(e)[:300]}", "llm_calls": None}
        ex = exec_match(db_path(q["db_id"]), out["pred"], q["SQL"])
        rec = {"idx": q["idx"], "db_id": q["db_id"], "difficulty": q["difficulty"], "question": q["question"],
               "evidence": q.get("evidence"), "gold": q["SQL"], "ex": ex, **out,
               "latency_s": round(time.time() - t0, 1)}
        done[q["idx"]] = rec
        with cache.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        acc = sum(r["ex"] for r in done.values()) / len(done)
        print(f"[{len(done)}/{len(sample)}] EX {ex} (acum. {acc:.3f}) {rec['latency_s']}s | {out['pred'][:90]}",
              flush=True)
    report(n, seed, model)


def report(n: int, seed: int, model: str) -> None:
    out = [f"# BIRD dev — {model} ({datetime.now():%Y-%m-%d %H:%M})", "",
           "| Modo | n | EX | simple | moderate | challenging | errores | lat. media (s) | tiempo total (min) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for mode in ("solo", "agente2"):
        f = RESULTS / f"predicciones_{_tag(mode, n, seed, model)}.jsonl"
        if not f.exists():
            continue
        recs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
        by = collections.defaultdict(list)
        for r in recs:
            by[r["difficulty"]].append(r["ex"])
        cell = lambda v: f"{sum(v) / len(v):.3f} ({len(v)})" if v else "-"
        out.append(f"| {mode} | {len(recs)} | {sum(r['ex'] for r in recs) / len(recs):.3f} | {cell(by['simple'])} | "
                   f"{cell(by['moderate'])} | {cell(by['challenging'])} | {sum('error' in r for r in recs)} | "
                   f"{sum(r['latency_s'] for r in recs) / len(recs):.1f} | {sum(r['latency_s'] for r in recs) / 60:.0f} |")
    text = "\n".join(out)
    (RESULTS / f"bird_n{n}_seed{seed}_{model.replace(':', '-')}.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("solo", "agente2"))
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "glm4:9b"))
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    if a.report:
        report(a.n, a.seed, a.model)
    else:
        run(a.mode, a.n, a.seed, a.model)
