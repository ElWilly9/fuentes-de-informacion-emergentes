"""
run_wikieval.py — Nuestro RAG sobre WikiEval, evaluado con RAGAS (como Vu et al., ICCIES 2026)
============================================================================================
Réplica de la evaluación del Knowledge Retriever de "Academic Query Orchestration" (Tabla 4):
WikiEval (50 preguntas sobre 50 páginas de Wikipedia) + las 4 métricas de RAGAS:
faithfulness, answer relevancy, context precision y context recall.

Nuestro pipeline, adaptado lo mínimo:
  - Índice: las 50 páginas (`context_v1`) en una colección Chroma aparte, con el mismo
    `get_abstracts_collection` (nomic-embed-text, coseno) y el mismo `_build_document`.
  - Recuperación: top-k = RAG_TOP_K (5), sin traducción (las preguntas ya están en inglés).
  - Generación: glm4:9b, temperatura 0.3, con el prompt de `node_rag_search`; cambia solo
    el idioma de respuesta (inglés) y "artículos" por "pasajes".
  - Config A ("tal_cual"): `format_rag_context` con cada texto cortado a 300 caracteres (así era el agente
    hasta el 2026-10-16).
    Config B ("completo"): el mismo formato con el pasaje completo.

Los contextos que se pasan a RAGAS son los que vio el LLM.
Pasos separados (las respuestas se guardan y el juez puede repetirse con otro modelo):
    python benchmark/externos/wikieval/run_wikieval.py generate --config tal_cual
    python benchmark/externos/wikieval/run_wikieval.py judge --config tal_cual --judge-model glm4:9b
"""

import argparse
import json
import os
import sys
import time
import types
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "wikieval.parquet"
CHROMA_DIR = HERE / "chroma"
RESULTS = HERE / "results"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# Prompt de node_rag_search (graph.py) con el idioma cambiado
SYSTEM_PROMPT = ("Eres un experto. Responde en ingles, citando los pasajes encontrados por su titulo. "
                 "Se conciso.")


def load_wikieval() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    df["question"] = df["question"].str.replace(r"^\s*Question:\s*", "", regex=True).str.strip()
    df["answer"] = df["answer"].str.replace(r"^\s*Answer:\s*", "", regex=True).str.strip()
    df["page"] = df["context_v1"].map(lambda x: "\n\n".join(x))
    return df


def build_index(df: pd.DataFrame):
    from src.layer3_rag.embedder import get_abstracts_collection, _build_document
    col = get_abstracts_collection(CHROMA_DIR)
    if col.count() != len(df):
        docs = [_build_document(title=s, abstract=p, keywords="") for s, p in zip(df.source, df.page)]
        col.upsert(ids=list(df.source), documents=docs,
                   metadatas=[{"title": s, "ismainarticle": 1} for s in df.source])
    return col


def retrieve(col, question: str, pages: dict[str, str]) -> list[dict]:
    from src.layer3_rag.retriever import _query
    arts = _query(col, question, TOP_K, None, set())[:TOP_K]
    for i, a in enumerate(arts, 1):
        a.update(rank=i, abstract=pages[a["SR"]], year="N/A", cited_by="N/A", source_title="Wikipedia")
    return arts


def format_context(arts: list[dict], config: str) -> tuple[str, list[str]]:
    """Devuelve el texto para el LLM y la lista de contextos (lo que vio el LLM) para RAGAS."""
    from src.layer3_rag.retriever import RAGResult, format_rag_context
    if config == "tal_cual":
        # Como era format_rag_context hasta el 2026-10-16 (cortaba cada texto a 300 caracteres)
        cut = [{**a, "abstract": a["abstract"][:300] + "..."} for a in arts]
        text = format_rag_context(RAGResult(query="", articles=cut, total_found=len(cut), success=True))
        contexts = [f"{a['title']}: {a['abstract'][:300]}..." for a in arts]
    else:
        lines = []
        for a in arts:
            lines += [f"--- Pasaje {a['rank']} (similitud: {a['score']}) ---", f"Titulo: {a['title']}",
                      f"Texto: {a['abstract']}", ""]
        text = "\n".join(lines)
        contexts = [f"{a['title']}: {a['abstract']}" for a in arts]
    return text, contexts


def generate(config: str, model: str, limit: int | None) -> Path:
    from langchain_ollama import ChatOllama
    full = load_wikieval()
    df = full.head(limit) if limit else full
    col = build_index(full)                      # el índice siempre tiene las 50 páginas
    pages = dict(zip(full.source, full.page))
    # Con el texto completo el prompt supera el contexto por defecto de Ollama (se truncaría en silencio)
    llm = ChatOllama(base_url=OLLAMA_URL, model=model, temperature=0.3,
                     num_ctx=16384 if config == "completo" else None)
    rows = []
    for i, r in enumerate(df.itertuples(), 1):
        t0 = time.time()
        arts = retrieve(col, r.question, pages)
        text, contexts = format_context(arts, config)
        answer = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"PREGUNTA: {r.question}\n\nPASAJES ENCONTRADOS:\n{text}\n\nRESPUESTA:"},
        ]).content.strip()
        ranks = [a["SR"] for a in arts]
        rows.append({"id": i, "question": r.question, "reference": r.answer, "source": r.source,
                     "retrieved": ranks, "gold_rank": ranks.index(r.source) + 1 if r.source in ranks else None,
                     "contexts": contexts, "response": answer, "latency_s": round(time.time() - t0, 1)})
        print(f"[{i}/{len(df)}] rank={rows[-1]['gold_rank']} {rows[-1]['latency_s']}s  {r.question[:70]}")
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"respuestas_{config}_{model.replace(':', '-')}.json"
    out.write_text(json.dumps({"config": config, "model": model, "top_k": TOP_K, "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    hits = [r["gold_rank"] for r in rows]
    print(f"Página correcta en top-{TOP_K}: {sum(h is not None for h in hits)}/{len(hits)} · "
          f"en 1.er lugar: {sum(h == 1 for h in hits)}/{len(hits)} → {out}")
    return out


def _import_ragas():
    # ragas 0.4.3 importa ChatVertexAI de langchain_community, que ya no existe en langchain-community 0.4;
    # solo lo usa en una comprobación de tipo, así que basta con una clase vacía.
    name = "langchain_community.chat_models.vertexai"
    try:
        __import__(name)
    except ImportError:
        mod = types.ModuleType(name)
        mod.ChatVertexAI = type("ChatVertexAI", (), {})
        sys.modules[name] = mod
    import ragas  # noqa: F401


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def _is_google(judge_model: str) -> bool:
    return judge_model.startswith(("gemini", "gemma"))


def _judge_llm(judge_model: str, rpm: float):
    """Juez local (Ollama) o de Google AI Studio (Gemini/Gemma) por su endpoint compatible con OpenAI.
    La clave sale del .env (GEMINI_API_KEY)."""
    if not _is_google(judge_model):
        from langchain_ollama import ChatOllama
        return ChatOllama(base_url=OLLAMA_URL, model=judge_model, temperature=0.0, num_ctx=16384)
    import re
    from dotenv import load_dotenv
    from langchain_core.rate_limiters import InMemoryRateLimiter
    from langchain_openai import ChatOpenAI
    load_dotenv(ROOT / ".env")
    if not os.getenv("GEMINI_API_KEY"):
        sys.exit("Falta GEMINI_API_KEY en el .env")
    thought = re.compile(r"<thought>.*?</thought>", re.DOTALL)

    class ChatSinRazonamiento(ChatOpenAI):
        """Gemma 4 devuelve su razonamiento como texto (<thought>…</thought>) y no se puede apagar."""
        def _create_chat_result(self, response, generation_info=None):
            result = super()._create_chat_result(response, generation_info)
            for g in result.generations:
                if isinstance(g.message.content, str):
                    g.message.content = thought.sub("", g.message.content).strip()
                    g.text = g.message.content
            return result

    # Nivel gratuito: el límite de peticiones/min depende del modelo (Gemini Flash 5, Gemma 30); --rpm deja margen
    limiter = InMemoryRateLimiter(requests_per_second=rpm / 60, check_every_n_seconds=0.5, max_bucket_size=1)
    return ChatSinRazonamiento(base_url=GEMINI_URL, api_key=os.environ["GEMINI_API_KEY"], model=judge_model,
                               temperature=0.0, rate_limiter=limiter, max_retries=6, timeout=300)


def judge(config: str, model: str, judge_model: str, limit: int | None, workers: int, rpm: float,
          batch: int = 5) -> None:
    """
    Puntúa por lotes y guarda cada pregunta en un .jsonl (las que quedan sin puntuar no se guardan):
    si se corta (p. ej. cuota diaria de Google), al volver a correr el mismo comando se retoma donde quedó.
    """
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    _import_ragas()
    from langchain_ollama import OllamaEmbeddings
    from ragas import EvaluationDataset, RunConfig, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    src = RESULTS / f"respuestas_{config}_{model.replace(':', '-')}.json"
    rows = json.loads(src.read_text(encoding="utf-8"))["rows"][:limit]
    is_google = _is_google(judge_model)
    # Google no acepta n>1 ("Multiple candidates is not enabled"): bypass_n hace llamadas separadas
    llm = LangchainLLMWrapper(_judge_llm(judge_model, rpm), bypass_n=is_google)
    emb = LangchainEmbeddingsWrapper(OllamaEmbeddings(base_url=OLLAMA_URL, model="nomic-embed-text"))
    run_cfg = RunConfig(max_workers=workers, timeout=900, max_retries=3)

    tag = f"{config}_{model.replace(':', '-')}_juez-{judge_model.replace(':', '-')}"
    cache = RESULTS / f"ragas_{tag}.jsonl"
    done = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done[rec["id"]] = rec
    t0 = time.time()
    pending = [r for r in rows if r["id"] not in done]
    # Lotes de varias preguntas: RAGAS reparte las llamadas de todo el lote entre los workers
    for i in range(0, len(pending), batch):
        chunk = pending[i:i + batch]
        ds = EvaluationDataset.from_list([{"user_input": r["question"], "response": r["response"],
                                           "retrieved_contexts": r["contexts"], "reference": r["reference"]}
                                          for r in chunk])
        res = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                       llm=llm, embeddings=emb, raise_exceptions=False, run_config=run_cfg, show_progress=False)
        table = res.to_pandas()
        n_ok = 0
        for j, r in enumerate(chunk):
            vals = {m: float(table[m].iloc[j]) for m in METRICS}
            if any(v != v for v in vals.values()):   # NaN: no se guarda, se reintenta al volver a correr
                print(f"   [sin puntuar] pregunta {r['id']}: {vals}")
                continue
            n_ok += 1
            done[r["id"]] = {"id": r["id"], "gold_rank": r["gold_rank"], **vals}
            with cache.open("a", encoding="utf-8") as f:
                f.write(json.dumps(done[r["id"]]) + "\n")
            print(f"[{len(done)}/{len(rows)}] q{r['id']} " + " · ".join(f"{m[:12]} {vals[m]:.2f}" for m in METRICS))
        if is_google and n_ok == 0:
            print(f"\nNingún resultado en el lote: probablemente se agotó la cuota de {judge_model} "
                  f"({len(done)}/{len(rows)} puntuadas). Vuelve a correr el mismo comando para continuar.")
            return

    missing = [r["id"] for r in rows if r["id"] not in done]
    if missing:
        print(f"\nFaltan {len(missing)} preguntas sin puntuar ({missing}); vuelve a correr el mismo comando.")
        return
    scores = pd.DataFrame([done[r["id"]] for r in rows])
    scores.to_csv(RESULTS / f"ragas_{tag}.csv", index=False, encoding="utf-8")
    summary = {m: round(float(scores[m].mean()), 4) for m in METRICS}
    nan = {m: int(scores[m].isna().sum()) for m in METRICS}
    metrics = METRICS
    lines = [f"# WikiEval + RAGAS — config `{config}`", "",
             f"- Generador: `{model}` · juez RAGAS: `{judge_model}` · embeddings: nomic-embed-text · top-k {TOP_K}",
             f"- Preguntas: {len(rows)} · tiempo del juez en esta sesión: {round((time.time() - t0) / 60, 1)} min",
             f"- Página correcta en top-{TOP_K}: {sum(r['gold_rank'] is not None for r in rows)}/{len(rows)}"
             f" · en 1.er lugar: {sum(r['gold_rank'] == 1 for r in rows)}/{len(rows)}", "",
             "| Métrica | Media | Sin puntuar (NaN) |", "|---|---|---|"]
    lines += [f"| {m} | {summary[m]} | {nan[m]} |" for m in metrics]
    (RESULTS / f"ragas_{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["generate", "judge"])
    p.add_argument("--config", choices=["tal_cual", "completo"], default="tal_cual")
    p.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "glm4:9b"))
    p.add_argument("--judge-model", default="glm4:9b")
    p.add_argument("--limit", type=int)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--rpm", type=float, default=4, help="peticiones por minuto al juez de Google")
    p.add_argument("--batch", type=int, default=5, help="preguntas evaluadas a la vez")
    a = p.parse_args()
    if a.stage == "generate":
        generate(a.config, a.model, a.limit)
    else:
        judge(a.config, a.model, a.judge_model, a.limit, a.workers, a.rpm, a.batch)
