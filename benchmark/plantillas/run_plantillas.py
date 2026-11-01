"""
run_plantillas.py — Corre el benchmark por plantillas contra el agente y lo puntúa solo
========================================================================================
Lee preguntas_plantillas.json (build_plantillas.py), llama a run_agent con la BD y el Chroma de cada
corpus y puntúa de forma automática (0–1 por pregunta):
  - SQL: fracción de cifras del gold que aparecen en la respuesta; si hay `alguno_de` (país o año en
    empate), además debe aparecer uno de ellos (en inglés o en español).
  - Híbrida / RAG: fracción de títulos del gold nombrados en la respuesta (un título cuenta si aparece
    el 60 % de sus palabras de 4+ letras), hasta `minimo`.
No mide la calidad de la explicación, solo que la cifra o el artículo sean los correctos.

    python benchmark/plantillas/run_plantillas.py                    # los 3 corpus
    python benchmark/plantillas/run_plantillas.py --corpus ai
    python benchmark/plantillas/run_plantillas.py --report
Guarda cada pregunta al terminarla (results/plantillas_<modelo>.jsonl): si se corta, el mismo comando retoma.
"""

import argparse
import collections
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

# NO_THINK=1: modelos que razonan (qwen3) sin razonamiento, como glm4 (igual que en benchmark/externos)
if os.getenv("NO_THINK") == "1":
    from langchain_ollama import ChatOllama as _ChatOllama
    _ChatOllama.model_fields["reasoning"].default = False
    _ChatOllama.model_rebuild(force=True)

SESSIONS = ROOT / "data" / "sessions"
RESULTS = HERE / "results"
MODEL = os.getenv("OLLAMA_MODEL", "glm4:9b")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9.,]+", " ", text)


def numbers_in(text: str) -> list[float]:
    """Cifras de la respuesta: '1.234' y '1,234' como miles, '11,8' y '11.8' como decimales."""
    out = []
    for tok in re.findall(r"\d[\d.,]*", text):
        tok = tok.rstrip(".,")
        if re.fullmatch(r"\d{1,3}([.,]\d{3})+", tok):
            out.append(float(re.sub(r"[.,]", "", tok)))
        else:
            try:
                out.append(float(tok.replace(",", ".")))
            except ValueError:
                pass
    return out


def has_number(gold: float, found: list[float]) -> bool:
    tol = 0.051 if gold != int(gold) else 0      # decimales: vale el redondeo a 1 cifra
    return any(abs(f - gold) <= tol for f in found)


def has_title(title: str, answer: str) -> bool:
    words = [w for w in norm(title).split() if len(w) >= 4]
    ans = set(norm(answer).split())
    return bool(words) and sum(w in ans for w in words) / len(words) >= 0.6


def score(item: dict, answer: str) -> float:
    g = item["gold"]
    if item["tipo"] == "SQL":
        found = numbers_in(answer)
        parts = [has_number(n, found) for n in g.get("numeros", [])]
        if g.get("alguno_de"):
            ans = norm(answer)
            parts.append(any(norm(a).strip() in ans for alts in g["alguno_de"] for a in alts))
        return sum(parts) / len(parts)
    hits = sum(has_title(t, answer) for t in g["titulos"])
    return min(hits, g["minimo"]) / g["minimo"]


def cache_path() -> Path:
    return RESULTS / f"plantillas_{MODEL.replace(':', '-')}.jsonl"


def run(corpora: list[str]) -> None:
    from src.layer2_agent.graph import run_agent
    items = [i for i in json.loads((HERE / "preguntas_plantillas.json").read_text(encoding="utf-8"))
             if i["corpus"] in corpora]
    RESULTS.mkdir(exist_ok=True)
    done = set()
    if cache_path().exists():
        done = {json.loads(l)["id"] for l in cache_path().read_text(encoding="utf-8").splitlines()}
    print(f"Modelo: {MODEL} | {len(items)} preguntas ({len(done)} ya hechas)", flush=True)
    for it in items:
        if it["id"] in done:
            continue
        session = SESSIONS / it["corpus"]
        t0 = time.time()
        try:
            st = run_agent(it["pregunta"], db_path=str(session / "db" / "bibliometria.db"),
                           chroma_dir=str(session / "chroma"))
            err = None
        except Exception as e:
            st, err = {}, f"{type(e).__name__}: {e}"
        answer = st.get("answer") or ""
        rec = {**it, "intent": st.get("intent"), "respuesta": answer,
               "sql": st.get("sql_visible") or st.get("generated_sql") or "", "error": err,
               "puntaje": round(score(it, answer), 3), "latencia_s": round(time.time() - t0, 1),
               "fecha": datetime.now().isoformat(timespec="seconds")}
        with cache_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {rec['id']} [{rec['tipo']}] ruta={rec['intent']} puntaje={rec['puntaje']} ({rec['latencia_s']}s)",
              flush=True)
    report()


def report() -> None:
    recs = [json.loads(l) for l in cache_path().read_text(encoding="utf-8").splitlines()]
    route_ok = {"SQL": {"sql"}, "Híbrida": {"hybrid", "sql"}, "RAG": {"rag", "hybrid"}}
    by = collections.defaultdict(list)
    for r in recs:
        by[(r["corpus"], r["tipo"])].append(r)
    corpora = list(dict.fromkeys(r["corpus"] for r in recs))
    mean = lambda v: sum(v) / len(v) if v else float("nan")
    out = [f"# Benchmark por plantillas — {MODEL} ({datetime.now():%Y-%m-%d %H:%M})", "",
           "Puntaje automático 0–1 (cifras o títulos correctos). Ruta esperada: SQL → sql; híbrida → hybrid o sql; "
           "RAG → rag o hybrid.", "",
           "| Corpus | SQL | Híbridas | RAG | Total | Ruta esperada | Lat. media (s) | Tiempo total (min) |",
           "|---|---|---|---|---|---|---|---|"]
    for c in corpora:
        rs = [r for r in recs if r["corpus"] == c]
        cells = [f"{mean([r['puntaje'] for r in by[(c, t)]]):.2f} ({len(by[(c, t)])})" for t in ("SQL", "Híbrida", "RAG")]
        ruta = mean([r["intent"] in route_ok[r["tipo"]] for r in rs])
        out.append(f"| {c} | " + " | ".join(cells) + f" | **{mean([r['puntaje'] for r in rs]):.2f}** | {ruta:.0%} | "
                   f"{mean([r['latencia_s'] for r in rs]):.0f} | {sum(r['latencia_s'] for r in rs) / 60:.0f} |")
    out += ["", "## Detalle", "", "| ID | Ruta | Puntaje | s | Respuesta (inicio) |", "|---|---|---|---|---|"]
    for r in recs:
        resp = (r["respuesta"] or r["error"] or "").replace("\n", " ").replace("|", "/")[:140]
        out.append(f"| {r['id']} | {r['intent']} | {r['puntaje']} | {r['latencia_s']} | {resp} |")
    text = "\n".join(out)
    (RESULTS / f"plantillas_{MODEL.replace(':', '-')}.md").write_text(text + "\n", encoding="utf-8")
    print("\n".join(out[:4 + 2 + len(corpora) + 2]))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", help="uno de Agrovoltaics, ai, pendulo (por defecto los 3)")
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    if a.report:
        report()
    else:
        run([a.corpus] if a.corpus else ["Agrovoltaics", "ai", "pendulo"])
