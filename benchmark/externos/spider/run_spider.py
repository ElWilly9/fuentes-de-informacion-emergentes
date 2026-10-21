"""
run_spider.py — Text-to-SQL en Spider (dev), como Vu et al. (ICCIES 2026, Tabla 8)
==================================================================================
Vu et al. comparan el LLM solo contra el LLM dentro de su agente (Gemini 2.5 Pro: EX 77,8 % → 80,0 %),
con EX (exactitud de ejecución) y EM (exact set match), sin decir cuántas preguntas ni qué partición.

Aquí, con glm4:9b:
  - `solo`:   prompt estándar zero-shot en inglés (CREATE TABLE de la BD + pregunta → SQL), un intento.
  - `agente`: el flujo SQL del agente tal cual (graph.py): generate_sql → execute_sql (clean_sql: reparación
    de alias(col), etc.) → refine_sql hasta SQL_MAX_RETRIES → synthesize_answer → reflect_on_answer → si la
    reflexión la juzga inadecuada, regenera el SQL con la crítica (REFLECT_MAX_RETRIES). Mismos prompts (en
    español) y funciones del agente. Única adaptación: la Capa 1 (schema linking) está hecha para el esquema
    bibliométrico, así que se le pasa el esquema completo de la BD de Spider (tablas, columnas y FKs de
    tables.json) en el SchemaContext. Se omiten los pasos propios del corpus (respaldo a referencias,
    artículos mostrados).

Métricas con el evaluador oficial (taoyds/test-suite-sql-eval, en eval_oficial/): EX sobre la BD original y
EM, por dificultad (easy/medium/hard/extra).

    python benchmark/externos/spider/run_spider.py --mode solo --n 300
    python benchmark/externos/spider/run_spider.py --mode agente --n 300
    python benchmark/externos/spider/run_spider.py --report --n 300     # tabla comparativa
Las predicciones se guardan pregunta a pregunta: si se corta, el mismo comando retoma.
"""

import argparse
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
SPIDER = HERE / "data" / "spider_unz" / "spider_data"
DB_DIR = SPIDER / "database"
EVAL_DIR = HERE / "eval_oficial"
RESULTS = HERE / "results"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

SOLO_SYSTEM = "You are an expert in SQLite. Write a single SQLite query that answers the question. " \
              "Reply with the SQL only, without explanation or markdown."
SOLO_USER = "{schema}\n\n-- Question: {question}\n-- SQL:"


def load_sample(n: int, seed: int) -> list[dict]:
    dev = json.loads((SPIDER / "dev.json").read_text(encoding="utf-8"))
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


def schema_context(question: str, table: dict):
    """SchemaContext con el esquema completo de una BD de Spider (en lugar de la Capa 1)."""
    from src.layer1_schema.models import SchemaContext
    tables = table["table_names_original"]
    cols = {t: [] for t in tables}
    names = table["column_names_original"]
    for t_idx, c in names:
        if t_idx >= 0:
            cols[tables[t_idx]].append(c)
    fks = [f"{tables[names[a][0]]}.{names[a][1]} -> {tables[names[b][0]]}.{names[b][1]}"
           for a, b in table["foreign_keys"]]
    return SchemaContext(query=question, query_type="sql", relevant_tables=list(tables), relevant_columns=cols,
                         foreign_keys=fks, entities={}, confidence=1.0)


def one_line(sql: str) -> str:
    return re.sub(r"\s+", " ", sql or "").strip().rstrip(";").strip() or "SELECT"


def predict_solo(q: dict, llm) -> dict:
    from src.layer2_agent.sql_generator import extract_sql_from_response
    response = llm.invoke([
        {"role": "system", "content": SOLO_SYSTEM},
        {"role": "user", "content": SOLO_USER.format(schema=create_statements(q["db_id"]), question=q["question"])},
    ]).content
    return {"pred": one_line(extract_sql_from_response(response)), "llm_calls": 1}


def predict_agente(q: dict, table: dict) -> dict:
    """El bucle SQL de graph.py (generate → validate → refine → synthesize → reflect → regenerar)."""
    from src.layer2_agent.answer_synthesizer import reflect_on_answer, synthesize_answer
    from src.layer2_agent.graph import REFLECT_MAX_RETRIES, SQL_MAX_RETRIES
    from src.layer2_agent.refiner import refine_sql
    from src.layer2_agent.sql_generator import generate_sql
    from src.layer2_agent.sql_validator import execute_sql
    ctx = schema_context(q["question"], table)
    db = db_path(q["db_id"])
    retry = reflect_count = calls = 0
    feedback, first_sql, trace = None, None, []
    while True:
        result = execute_sql(generate_sql(ctx, feedback=feedback), db_path=db)
        calls += 1
        first_sql = first_sql or result.query
        trace.append(("generate", result.query, result.error))
        while not result.success and retry < SQL_MAX_RETRIES:
            result = execute_sql(refine_sql(ctx, result.query, result.error), db_path=db)
            retry += 1
            calls += 1
            trace.append(("refine", result.query, result.error))
        answer = synthesize_answer(ctx, result)
        calls += 1 if result.success and result.row_count else 0
        if not result.success or reflect_count >= REFLECT_MAX_RETRIES:
            break
        adequate, critique = reflect_on_answer(ctx, result, answer)
        calls += 1
        if adequate:
            break
        feedback = critique
        reflect_count += 1
        trace.append(("reflect", critique, None))
    return {"pred": one_line(result.query), "first_sql": one_line(first_sql), "executed_ok": result.success,
            "refines": retry, "reflections": reflect_count, "llm_calls": calls, "answer": answer, "trace": trace}


def _tag(mode: str, n: int, seed: int, model: str) -> str:
    return f"{mode}_n{n}_seed{seed}_{model.replace(':', '-')}"


def run(mode: str, n: int, seed: int, model: str) -> None:
    from langchain_ollama import ChatOllama
    sample = load_sample(n, seed)
    tables = {t["db_id"]: t for t in json.loads((SPIDER / "tables.json").read_text(encoding="utf-8"))}
    RESULTS.mkdir(exist_ok=True)
    cache = RESULTS / f"predicciones_{_tag(mode, n, seed, model)}.jsonl"
    done = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done[rec["idx"]] = rec
    llm = ChatOllama(base_url=OLLAMA_URL, model=model, temperature=0.0)
    ex_mod = _official()[1]
    for q in sample:
        if q["idx"] in done:
            continue
        t0 = time.time()
        out = predict_solo(q, llm) if mode == "solo" else predict_agente(q, tables[q["db_id"]])
        ex = ex_mod.eval_exec_match(db=db_path(q["db_id"]), p_str=out["pred"], g_str=q["query"], plug_value=False,
                                    keep_distinct=False, progress_bar_for_each_datapoint=False)
        rec = {"idx": q["idx"], "db_id": q["db_id"], "question": q["question"], "gold": q["query"], "ex": ex,
               **out, "latency_s": round(time.time() - t0, 1)}
        done[q["idx"]] = rec
        with cache.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        acc = sum(r["ex"] for r in done.values()) / len(done)
        print(f"[{len(done)}/{len(sample)}] EX {ex} (acum. {acc:.3f}) {rec['latency_s']}s | {out['pred'][:90]}",
              flush=True)
    print(official_eval(mode, n, seed, model))


# ── Evaluador oficial ───────────────────────────────────────────────────────────

def _official():
    if str(EVAL_DIR) not in sys.path:
        sys.path.insert(0, str(EVAL_DIR))
    import evaluation
    import exec_eval
    return evaluation, exec_eval


def official_eval(mode: str, n: int, seed: int, model: str) -> str:
    """Corre evaluation.py (etype all) sobre las predicciones y devuelve el resumen de EX y EM."""
    tag = _tag(mode, n, seed, model)
    recs = {json.loads(l)["idx"]: json.loads(l)
            for l in (RESULTS / f"predicciones_{tag}.jsonl").read_text(encoding="utf-8").splitlines()}
    sample = [q for q in load_sample(n, seed) if q["idx"] in recs]
    gold, pred = RESULTS / f"gold_{tag}.txt", RESULTS / f"pred_{tag}.txt"
    # Una línea en blanco tras cada pregunta: cada una es su propia "sesión" para el evaluador
    gold.write_text("".join(f"{one_line(q['query'])}\t{q['db_id']}\n\n" for q in sample), encoding="utf-8")
    pred.write_text("".join(f"{recs[q['idx']]['pred']}\n\n" for q in sample), encoding="utf-8")
    proc = subprocess.run([sys.executable, "evaluation.py", "--gold", str(gold), "--pred", str(pred),
                           "--db", str(DB_DIR), "--table", str(SPIDER / "tables.json"), "--etype", "all"],
                          cwd=EVAL_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (RESULTS / f"evaluacion_oficial_{tag}.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    lines = proc.stdout.splitlines()
    keep = [l for l in lines if re.match(r"\s+easy\s+medium|(count|execution|exact match)\s", l)]
    return f"## {tag}\n" + "\n".join(keep[:4]) + ("\n" + proc.stderr[-2000:] if proc.returncode else "")


def report(n: int, seed: int, model: str) -> None:
    out = [f"# Spider dev — glm4 solo vs. dentro del agente ({datetime.now():%Y-%m-%d %H:%M})", ""]
    for mode in ("solo", "agente"):
        if (RESULTS / f"predicciones_{_tag(mode, n, seed, model)}.jsonl").exists():
            out += [official_eval(mode, n, seed, model), ""]
    text = "\n".join(out)
    (RESULTS / f"spider_n{n}_seed{seed}_{model.replace(':', '-')}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("solo", "agente"))
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "glm4:9b"))
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    if a.report:
        report(a.n, a.seed, a.model)
    else:
        run(a.mode, a.n, a.seed, a.model)
