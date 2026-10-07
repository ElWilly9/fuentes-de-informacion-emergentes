"""
evaluate.py — Evaluación del agente contra el benchmark de agrovoltaicos
========================================================================
Corre las 30 preguntas de `benchmark/agrovoltaics/dataset_agrovoltaicos.xlsx`
contra `run_agent` y calcula tres bloques de métricas, reportados por separado
(no existe una métrica unificada SQL+RAG):

  SQL puro (Q01-Q12)  → Execution Accuracy (EX) estricta y laxa, contra el
                        resultado de ejecutar el gold SQL en la BD.
  RAG puro (Q13-Q20)  → LLM-as-judge (0/1/2) contra la respuesta de referencia.
  Híbridas (Q21-Q30)  → cifras de la BD presentes en la respuesta (automático)
                        + LLM-as-judge del veredicto (¿concuerda con el artículo?).

Además, para todas: acierto de enrutamiento (sql/rag/hybrid), éxito, latencia.

Uso (desde demo_limpio, con Ollama corriendo):
    python benchmark/evaluate.py
    python benchmark/evaluate.py --only Q01,Q05,Q21
    python benchmark/evaluate.py --no-judge          # sin LLM-as-judge
    python benchmark/evaluate.py --judge-model qwen2.5:7b
"""

import argparse
import ast
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

DATASET = ROOT / "benchmark" / "agrovoltaics" / "dataset_agrovoltaicos.xlsx"
RESULTS_DIR = ROOT / "benchmark" / "agrovoltaics" / "results"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Las "híbridas" del dataset contrastan una afirmación que ya viene en la pregunta con la BD:
# no necesitan recuperar abstracts, así que tanto sql como hybrid son rutas válidas.
EXPECTED_INTENT = {"SQL puro": {"sql"}, "RAG puro": {"rag"}, "Híbrida": {"sql", "hybrid"}}


# ── Carga del dataset ─────────────────────────────────────────────────────────

def load_dataset(path: Path) -> list[dict]:
    ws = openpyxl.load_workbook(path)["preguntas"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    return [dict(zip(header, r)) for r in rows[1:] if r[0]]


# ── EX para SQL ───────────────────────────────────────────────────────────────

def _norm(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 4)
    s = str(v).strip().casefold()
    try:
        return round(float(s), 4)
    except ValueError:
        return s


def _rows_to_tuples(rows: list) -> list[tuple]:
    out = []
    for r in rows:
        vals = r.values() if isinstance(r, dict) else r
        out.append(tuple(_norm(v) for v in vals))
    return out


def execution_accuracy(pred_rows: list, gold_rows: list, ordered: bool) -> tuple[bool, bool]:
    """Devuelve (EX estricta, EX laxa).

    Estricta: mismo conjunto de filas y columnas (en el mismo orden si el gold ordena).
    Laxa: todos los valores escalares del gold aparecen entre los valores predichos
    (tolera columnas extra o nombres de columna distintos).
    """
    p, g = _rows_to_tuples(pred_rows), _rows_to_tuples(gold_rows)
    strict = (p == g) if ordered else (sorted(p, key=repr) == sorted(g, key=repr))
    pred_vals = {v for row in p for v in row}
    lenient = all(v in pred_vals for row in g for v in row)
    return strict, lenient


def run_gold(db_path: Path, sql: str) -> list[list]:
    conn = sqlite3.connect(db_path)
    try:
        return [list(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


# ── Híbridas: cifras de la BD en la respuesta ─────────────────────────────────

def numbers_in(text: str) -> set[float]:
    nums = set()
    for m in re.findall(r"\d+(?:[.,]\d+)*", text):
        for cand in (m.replace(",", "."), m.replace(".", "").replace(",", ".")):
            try:
                nums.add(round(float(cand), 4))
            except ValueError:
                pass
    return nums


def gold_values_in_answer(gold_rows: list[list], answer: str) -> bool:
    ans_nums, ans_low = numbers_in(answer), answer.casefold()
    for row in gold_rows:
        for v in row:
            if isinstance(v, (int, float)):
                if round(float(v), 4) not in ans_nums:
                    return False
            elif v is not None and str(v).casefold() not in ans_low:
                return False
    return True


# ── LLM-as-judge ──────────────────────────────────────────────────────────────

def judge(model: str, prompt: str) -> tuple[int | None, str]:
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "format": "json",
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=180,
        )
        r.raise_for_status()
        content = r.json()["message"]["content"]
        # Algunos modelos (glm4) envuelven el JSON en ```json ... ```
        m = re.search(r"\{.*\}", content, flags=re.S)
        data = json.loads(m.group(0)) if m else {}
        score = int(data["score"])
        if score not in (0, 1, 2):
            raise ValueError(f"puntaje fuera de rango: {score}")
        return score, str(data.get("reason", ""))
    except Exception as e:  # el juez nunca debe tumbar la corrida
        return None, f"error del juez: {e}"


RAG_RUBRIC = """Eres un evaluador estricto. Compara la RESPUESTA del sistema con la REFERENCIA.
Puntúa: 2 = cubre la idea principal de la referencia sin errores; 1 = parcial o con imprecisiones;
0 = incorrecta, ajena o dice que no sabe.

PREGUNTA: {q}
REFERENCIA: {gold}
RESPUESTA: {ans}

Responde solo JSON: {{"score": 0|1|2, "reason": "una frase"}}"""

HYBRID_RUBRIC = """Eres un evaluador estricto. La pregunta contrasta una afirmación de un artículo con una base de datos.
La respuesta correcta debe (a) dar la cifra o dato de la base de datos y (b) decir correctamente si
coincide o no con lo que afirma el artículo.
Puntúa: 2 = dato y veredicto correctos; 1 = solo uno de los dos es correcto; 0 = ninguno.

PREGUNTA: {q}
AFIRMACIÓN DEL ARTÍCULO: {claim}
DATO CORRECTO DE LA BD: {gold}
VEREDICTO CORRECTO: {estado}. {nota}
RESPUESTA: {ans}

Responde solo JSON: {{"score": 0|1|2, "reason": "una frase"}}"""


# ── Evaluación de una pregunta ────────────────────────────────────────────────

def evaluate_one(item: dict, db_path: Path, chroma_dir: Path, args) -> dict:
    from src.layer2_agent.graph import run_agent

    tipo = item["tipo"]
    rec = {
        "id": item["id"], "tipo": tipo, "pregunta": item["pregunta"],
        "intent_esperado": sorted(EXPECTED_INTENT[tipo]),
    }

    t0 = time.time()
    try:
        state = run_agent(item["pregunta"], db_path=str(db_path), chroma_dir=str(chroma_dir))
        rec["error"] = None
    except Exception as e:
        state, rec["error"] = {}, f"{type(e).__name__}: {e}"
    rec["latencia_s"] = round(time.time() - t0, 1)

    answer = state.get("answer") or ""
    sql_result = state.get("sql_result")
    rec.update({
        "intent": state.get("intent"),
        "ruta_correcta": state.get("intent") in EXPECTED_INTENT[tipo],
        "success": bool(state.get("success")),
        "respuesta": answer,
        "sql": state.get("sql_visible") or state.get("generated_sql") or "",
    })

    gold_sql = item.get("gold_sql")
    gold_rows = ast.literal_eval(item["gold_respuesta"]) if gold_sql else None
    if gold_sql:
        # El gold se re-ejecuta sobre la BD actual: no depende de lo escrito en el Excel
        live = run_gold(db_path, gold_sql)
        rec["gold_estable"] = live == gold_rows
        gold_rows = live

    if tipo == "SQL puro":
        pred = list(sql_result.rows) if sql_result and sql_result.success else []
        rec["ex_estricta"], rec["ex_laxa"] = execution_accuracy(
            pred, gold_rows, ordered="order by" in gold_sql.casefold())
    elif tipo == "RAG puro":
        if not args.no_judge:
            rec["juez"], rec["juez_razon"] = judge(args.judge_model, RAG_RUBRIC.format(
                q=item["pregunta"], gold=item["gold_respuesta"], ans=answer))
    else:  # Híbrida
        rec["cifras_bd_en_respuesta"] = gold_values_in_answer(gold_rows, answer)
        if not args.no_judge:
            rec["juez"], rec["juez_razon"] = judge(args.judge_model, HYBRID_RUBRIC.format(
                q=item["pregunta"], claim=item["afirmacion_articulo"],
                gold=json.dumps(gold_rows, ensure_ascii=False),
                estado=item["estado"], nota=item.get("nota") or "", ans=answer))
    return rec


# ── Resumen ───────────────────────────────────────────────────────────────────

def pct(vals: list[bool]) -> str:
    return f"{100 * sum(vals) / len(vals):.1f}% ({sum(vals)}/{len(vals)})" if vals else "n/a"


def summarize(recs: list[dict]) -> str:
    out = []
    for tipo in ("SQL puro", "RAG puro", "Híbrida"):
        rs = [r for r in recs if r["tipo"] == tipo]
        if not rs:
            continue
        out.append(f"\n== {tipo} ({len(rs)} preguntas) ==")
        out.append(f"  Ruta correcta : {pct([r['ruta_correcta'] for r in rs])}")
        out.append(f"  Éxito agente  : {pct([r['success'] for r in rs])}")
        out.append(f"  Latencia media: {sum(r['latencia_s'] for r in rs) / len(rs):.1f}s")
        if tipo == "SQL puro":
            out.append(f"  EX estricta   : {pct([r['ex_estricta'] for r in rs])}")
            out.append(f"  EX laxa       : {pct([r['ex_laxa'] for r in rs])}")
        else:
            if tipo == "Híbrida":
                out.append(f"  Cifras BD en respuesta: {pct([r['cifras_bd_en_respuesta'] for r in rs])}")
            scores = [r["juez"] for r in rs if r.get("juez") is not None]
            if scores:
                out.append(f"  Juez (media/2): {sum(scores) / len(scores):.2f}  "
                           f"[{len(scores)}/{len(rs)} puntuadas]")
    unstable = [r["id"] for r in recs if r.get("gold_estable") is False]
    if unstable:
        out.append(f"\nAVISO: el gold SQL ya no coincide con el Excel en {unstable}; revisar la BD.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", default="Agrovoltaics", help="carpeta en data/sessions")
    ap.add_argument("--only", help="ids separados por coma, p. ej. Q01,Q05")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--judge-model", default=os.getenv("OLLAMA_MODEL", "glm4:9b"))
    args = ap.parse_args()

    sess = ROOT / "data" / "sessions" / args.session
    db_path, chroma_dir = sess / "db" / "bibliometria.db", sess / "chroma"

    items = load_dataset(DATASET)
    if args.only:
        wanted = {x.strip().upper() for x in args.only.split(",")}
        items = [i for i in items if i["id"] in wanted]

    model = os.getenv("OLLAMA_MODEL", "glm4:9b")
    print(f"Modelo: {model} | Juez: {args.judge_model} | Sesión: {args.session} | {len(items)} preguntas")

    recs = []
    for it in items:
        rec = evaluate_one(it, db_path, chroma_dir, args)
        recs.append(rec)
        marca = rec.get("ex_estricta", rec.get("juez", rec.get("cifras_bd_en_respuesta")))
        print(f"  {rec['id']} [{rec['tipo']}] ruta={rec['intent']} resultado={marca} ({rec['latencia_s']}s)")

    summary = summarize(recs)
    print(summary)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"{stamp}_{model.replace(':', '-')}.json"
    out.write_text(json.dumps({
        "fecha": stamp, "modelo": model, "juez": None if args.no_judge else args.judge_model,
        "sesion": args.session, "resumen": summary, "resultados": recs,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultados guardados en {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
