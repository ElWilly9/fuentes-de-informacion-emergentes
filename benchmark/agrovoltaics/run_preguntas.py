"""
run_preguntas.py — Corre las 32 preguntas contra el agente y guarda las respuestas
==================================================================================
Sin juez ni puntaje: solo registra lo que responde el agente (ruta, SQL, filas,
respuesta, latencia) junto al gold, para comparar a mano.

Uso (desde demo_limpio, con Ollama corriendo):
    python benchmark/agrovoltaics/run_preguntas.py
    python benchmark/agrovoltaics/run_preguntas.py --only Q01,Q20
Salida: results/respuestas_<fecha>_<modelo>.json y .md
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from src.layer2_agent.graph import run_agent  # noqa: E402

SESSION = ROOT / "data" / "sessions" / "Agrovoltaics"


def render_md(model: str, recs: list[dict]) -> str:
    out = [f"# Respuestas del agente — 32 preguntas agrovoltaicos\n",
           f"Modelo: `{model}` · Corrida: {datetime.now():%Y-%m-%d %H:%M}\n"]
    for r in recs:
        out.append(f"## {r['id']} · {r['tipo']}\n")
        out.append(f"**Pregunta:** {r['pregunta']}\n")
        out.append(f"**Ruta del agente:** `{r['intent']}` · éxito: {r['success']} · {r['latencia_s']} s\n")
        if r.get("respuesta_esperada"):
            out.append(f"**Respuesta esperada:** {r['respuesta_esperada']}\n")
        if r.get("gold_bd") is not None:
            out.append(f"**Resultado en la BD:** `{json.dumps(r['gold_bd'], ensure_ascii=False)[:400]}`\n")
        if r.get("afirmacion_articulo"):
            out.append(f"**Afirmación del Word:** {r['afirmacion_articulo']}\n")
        out.append(f"**Respuesta del agente:** {r['respuesta'] or '(vacía)'}\n")
        if r["sql"]:
            out.append(f"**SQL del agente:** `{r['sql']}`\n")
        if r["error"]:
            out.append(f"**Error:** {r['error']}\n")
        out.append("---\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="ids separados por coma")
    ap.add_argument("--dataset", default="preguntas_32",
                    help="nombre del JSON en esta carpeta, p. ej. preguntas_scopus_32")
    args = ap.parse_args()

    items = json.loads((HERE / f"{args.dataset}.json").read_text(encoding="utf-8"))
    if args.only:
        wanted = {x.strip().upper() for x in args.only.split(",")}
        items = [i for i in items if i["id"] in wanted]

    model = os.getenv("OLLAMA_MODEL", "glm4:9b")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    base = out_dir / f"respuestas_{args.dataset}_{stamp}_{model.replace(':', '-')}"
    print(f"Modelo: {model} | {len(items)} preguntas")

    recs = []
    for it in items:
        t0 = time.time()
        try:
            st = run_agent(it["pregunta"], db_path=str(SESSION / "db" / "bibliometria.db"),
                           chroma_dir=str(SESSION / "chroma"))
            err = None
        except Exception as e:
            st, err = {}, f"{type(e).__name__}: {e}"
        sql_result = st.get("sql_result")
        rec = {
            "id": it["id"], "tipo": it["tipo"], "pregunta": it["pregunta"],
            "afirmacion_articulo": it.get("afirmacion_articulo"),
            "respuesta_esperada": it.get("respuesta_esperada"),
            "gold_bd": it.get("gold_bd"),
            "intent": st.get("intent"), "success": bool(st.get("success")),
            "respuesta": st.get("answer") or "",
            "sql": st.get("sql_visible") or st.get("generated_sql") or "",
            "filas_sql": list(sql_result.rows)[:20] if sql_result and sql_result.success else None,
            "rag_resultados": st.get("rag_results") or [],
            "latencia_s": round(time.time() - t0, 1), "error": err,
        }
        recs.append(rec)
        print(f"  {rec['id']} [{rec['tipo']}] ruta={rec['intent']} ok={rec['success']} ({rec['latencia_s']}s)", flush=True)
        # Se guarda tras cada pregunta: una caída no pierde lo ya corrido
        base.with_suffix(".json").write_text(json.dumps(
            {"modelo": model, "fecha": stamp, "resultados": recs}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
        base.with_suffix(".md").write_text(render_md(model, recs), encoding="utf-8")

    print(f"\nGuardado en {base.with_suffix('.md').relative_to(ROOT)} y .json")


if __name__ == "__main__":
    main()
