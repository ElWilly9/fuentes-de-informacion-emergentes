"""
run_hotpotqa.py — Nuestro RAG sobre HotpotQA (distractor), como Vu et al. (ICCIES 2026, Tablas 6-7)
================================================================================================
HotpotQA: preguntas multi-salto sobre Wikipedia; cada una trae 10 párrafos, de los que solo 2 sirven
(los "supporting facts"). Tipos: puente (bridge) y comparación. Vu et al. reportan EM, F1, precisión y
recall de la respuesta (AQO + Gemini 2.5 Pro: EM 0,631 · F1 0,759), sin decir cuántas preguntas usaron.

Nuestro pipeline, adaptado lo mínimo:
  - Los 10 párrafos de cada pregunta van a una colección Chroma en memoria con la misma función de
    embeddings que el agente (nomic-embed-text, coseno) y se recuperan con `retriever._query` (top-k 5).
  - Contexto con `format_rag_context` (abstracts completos) y respuesta de glm4:9b (temp. 0,3) con el prompt
    de `node_rag_search` en inglés. Única adaptación al benchmark: pedir la respuesta corta (EM/F1 la
    comparan con respuestas de pocas palabras: un nombre, una fecha, yes/no).
  - Métricas oficiales de la respuesta (normalización de hotpot_evaluate_v1: minúsculas, sin puntuación,
    sin artículos a/an/the) + recuperación: los 2 párrafos de apoyo dentro del top-k.

Muestra aleatoria fija (semilla 42) del dev distractor (7.405 preguntas):
    python benchmark/externos/hotpotqa/run_hotpotqa.py --n 300
Las respuestas se guardan pregunta a pregunta: si se corta, el mismo comando retoma.
"""

import argparse
import collections
import json
import os
import re
import string
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "hotpot_dev_distractor.parquet"
RESULTS = HERE / "results"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# NO_THINK=1: modelos que razonan (qwen3) sin razonamiento, como glm4. Cambia el valor por defecto de
# ChatOllama, así vale también para las llamadas del agente (src/), que no pasan `reasoning`.
if os.getenv("NO_THINK") == "1":
    from langchain_ollama import ChatOllama as _ChatOllama
    _ChatOllama.model_fields["reasoning"].default = False
    _ChatOllama.model_rebuild(force=True)
TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# Prompt de node_rag_search (graph.py) en inglés + respuesta corta (requisito de EM/F1)
SYSTEM_PROMPT = ("You are an expert. Answer using the retrieved passages. "
                 "Reply with the short answer only (a name, a date, a number or yes/no), without explanation.")


# ── Métricas oficiales de HotpotQA (hotpot_evaluate_v1.py) ──────────────────────

def normalize_answer(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def f1_score(prediction: str, ground_truth: str) -> tuple[float, float, float]:
    pred, gold = normalize_answer(prediction), normalize_answer(ground_truth)
    zero = (0.0, 0.0, 0.0)
    if pred in ("yes", "no", "noanswer") and pred != gold:
        return zero
    if gold in ("yes", "no", "noanswer") and pred != gold:
        return zero
    p_tok, g_tok = pred.split(), gold.split()
    common = collections.Counter(p_tok) & collections.Counter(g_tok)
    same = sum(common.values())
    if same == 0:
        return zero
    precision, recall = same / len(p_tok), same / len(g_tok)
    return 2 * precision * recall / (precision + recall), precision, recall


def exact_match(prediction: str, ground_truth: str) -> float:
    return float(normalize_answer(prediction) == normalize_answer(ground_truth))


# ── Pipeline ────────────────────────────────────────────────────────────────────

def load_sample(n: int, seed: int) -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    return df.sample(n=min(n, len(df)), random_state=seed).reset_index(drop=True)


def _collection():
    """Colección en memoria con la misma función de embeddings que get_abstracts_collection."""
    import chromadb
    from src.layer3_rag.embedder import make_embedding_function
    embed_fn = make_embedding_function(OLLAMA_URL, os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"))
    client = chromadb.EphemeralClient()
    return client, embed_fn


# Recuperación iterativa al estilo CoRAG (Wang et al. 2025), solo con prompt: tras la búsqueda inicial el LLM
# decide si falta un dato y escribe la siguiente búsqueda (p. ej. con la entidad puente que encontró).
STEP_PROMPT = ("You are answering a multi-hop question with passages retrieved so far. If the passages already contain "
               "everything needed, reply exactly 'DONE'. Otherwise reply 'SEARCH: <query>' with one short search query "
               "for the missing information, using names found in the passages when useful. No explanation.")
MAX_STEPS = int(os.getenv("ITER_MAX_STEPS", "2"))
STEP_K = int(os.getenv("ITER_STEP_K", "2"))


def iterative_retrieval(question, col, arts, paragraphs, llm) -> tuple[list[dict], list[str]]:
    from src.layer3_rag.retriever import RAGResult, format_rag_context
    searches = []
    for _ in range(MAX_STEPS):
        for i, a in enumerate(arts, 1):
            a.update(rank=i, abstract=paragraphs[a["title"]], year="N/A", cited_by="N/A", source_title="Wikipedia")
        context = format_rag_context(RAGResult(query=question, articles=arts, total_found=len(arts), success=True))
        reply = llm.invoke([
            {"role": "system", "content": STEP_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nPASSAGES:\n{context}\n\nREPLY:"},
        ]).content.strip()
        m = re.search(r"SEARCH:\s*(.+)", reply)
        if not m:
            break
        query = m.group(1).strip().splitlines()[0][:200]
        searches.append(query)
        new = _query_new(col, query, {a["SR"] for a in arts})
        if not new:
            break
        arts = arts + new
    return arts, searches


def _query_new(col, query, seen):
    from src.layer3_rag.retriever import _query
    return _query(col, query, STEP_K, None, seen)[:STEP_K]


def answer_one(row, client, embed_fn, llm, contexto: str = "top5") -> dict:
    """contexto: 'top5' = búsqueda top-k (el agente); 'todos' = los 10 párrafos (lo estándar en distractor);
    'oro' = solo los 2 párrafos de apoyo (techo del modelo con recuperación perfecta)."""
    from src.layer3_rag.embedder import _build_document
    from src.layer3_rag.retriever import RAGResult, _query, format_rag_context
    titles = list(row.context["title"])
    paragraphs = {t: "".join(s) for t, s in zip(titles, row.context["sentences"])}
    searches, t0 = [], time.time()  # la latencia incluye las búsquedas extra
    if contexto in ("top5", "iterativo"):
        name = f"q_{row.id}"
        col = client.get_or_create_collection(name=name, embedding_function=embed_fn,
                                              metadata={"hnsw:space": "cosine"})
        ids = [f"p{i}" for i in range(len(titles))]
        col.upsert(ids=ids, documents=[_build_document(title=t, abstract=paragraphs[t], keywords="") for t in titles],
                   metadatas=[{"title": t} for t in titles])
        arts = _query(col, row.question, TOP_K, None, set())[:TOP_K]
        if contexto == "iterativo":
            arts, searches = iterative_retrieval(row.question, col, arts, paragraphs, llm)
        client.delete_collection(name)
    else:
        gold = set(row.supporting_facts["title"])
        arts = [{"title": t, "score": "N/A"} for t in titles if contexto == "todos" or t in gold]
    for i, a in enumerate(arts, 1):
        a.update(rank=i, abstract=paragraphs[a["title"]], year="N/A", cited_by="N/A", source_title="Wikipedia")
    context = format_rag_context(RAGResult(query=row.question, articles=arts, total_found=len(arts), success=True))
    response = llm.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"QUESTION: {row.question}\n\nRETRIEVED PASSAGES:\n{context}\n\nANSWER:"},
    ]).content.strip()
    gold_titles = set(row.supporting_facts["title"])
    got = [a["title"] for a in arts]
    f1, prec, rec = f1_score(response, row.answer)
    return {"id": row.id, "type": row.type, "question": row.question, "answer": row.answer, "response": response,
            "em": exact_match(response, row.answer), "f1": f1, "precision": prec, "recall": rec,
            "retrieved": got, "sp_both_in_topk": gold_titles <= set(got),
            "sp_found": len(gold_titles & set(got)), "searches": searches, "latency_s": round(time.time() - t0, 1)}


def run(n: int, seed: int, model: str, contexto: str = "top5", suffix: str = "") -> None:
    from langchain_ollama import ChatOllama
    sample = load_sample(n, seed)
    RESULTS.mkdir(exist_ok=True)
    # la corrida original (top-5, sin prefijos de nomic) conserva su nombre de archivo
    extra = "" if contexto == "top5" else f"_{contexto}"
    tag = f"n{n}_seed{seed}_{model.replace(':', '-')}{extra}{suffix}"
    cache = RESULTS / f"respuestas_{tag}.jsonl"
    done = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done[rec["id"]] = rec
    client, embed_fn = _collection()
    # num_predict: con Ollama 0.31 glm4 a veces se queda repitiendo "@" sin parar (82.000 caracteres, horas)
    # los modelos que razonan (gpt-oss, qwen3) gastan tokens pensando antes de responder: tope mayor
    llm = ChatOllama(base_url=OLLAMA_URL, model=model, temperature=0.3, num_predict=100 if "glm4" in model else 4096)
    for i, row in enumerate(sample.itertuples(), 1):
        if row.id in done:
            continue
        rec = answer_one(row, client, embed_fn, llm, contexto)
        done[row.id] = rec
        with cache.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{len(done)}/{len(sample)}] EM {rec['em']:.0f} F1 {rec['f1']:.2f} SP {rec['sp_found']}/2 "
              f"{rec['latency_s']}s | {rec['response'][:40]!r} vs {rec['answer'][:30]!r}", flush=True)
    report(pd.DataFrame([done[r.id] for r in sample.itertuples()]), tag, model)


def report(df: pd.DataFrame, tag: str, model: str) -> None:
    def row(name, d):
        return (f"| {name} | {len(d)} | {d.em.mean():.4f} | {d.f1.mean():.4f} | {d.precision.mean():.4f} | "
                f"{d.recall.mean():.4f} | {d.sp_both_in_topk.mean():.3f} |")
    lines = [f"# HotpotQA (dev distractor) — {tag}", "",
             f"- Generador: `{model}` · recuperación: nomic-embed-text top-{TOP_K} sobre los 10 párrafos de cada pregunta",
             f"- Fecha: {datetime.now():%Y-%m-%d %H:%M} · latencia media del LLM: {df.latency_s.mean():.1f} s", "",
             "| Subconjunto | n | EM | F1 | Precisión | Recall | 2 párrafos de apoyo en top-k |",
             "|---|---|---|---|---|---|---|",
             row("Todas", df), row("Puente (bridge)", df[df.type == "bridge"]),
             row("Comparación", df[df.type == "comparison"]), "",
             "Vu et al. (AQO): Gemini 2.5 Flash EM 0,6017 · F1 0,7334 · P 0,7517 · R 0,7473; "
             "Gemini 2.5 Pro EM 0,6310 · F1 0,7587 · P 0,7794 · R 0,7710."]
    out = RESULTS / f"hotpotqa_{tag}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=300, help="tamaño de la muestra del dev distractor")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "glm4:9b"))
    p.add_argument("--contexto", choices=("top5", "todos", "oro", "iterativo"), default="top5",
                   help="top5: búsqueda del agente; todos: los 10 párrafos; oro: solo los 2 de apoyo; "
                        "iterativo: top5 + hasta 2 búsquedas más que decide el LLM (estilo CoRAG)")
    p.add_argument("--suffix", default="", help="sufijo del nombre de archivo (p. ej. _prefijos)")
    a = p.parse_args()
    run(a.n, a.seed, a.model, a.contexto, a.suffix)
