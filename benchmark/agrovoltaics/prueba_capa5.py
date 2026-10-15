"""
Prueba de la Capa 5 (redes, frentes y series de tiempo) contra el agente completo.

Uso: python benchmark/agrovoltaics/prueba_capa5.py [--session Agrovoltaics]
Guarda las respuestas en results/prueba_capa5_<fecha>.md (con el análisis que recibió el LLM).
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from src.layer2_agent.graph import run_agent  # noqa: E402

PREGUNTAS = [
    ("community", "¿Cuáles son los frentes de investigación del corpus y cuáles son emergentes?"),
    ("community", "¿Qué temas principales aparecen según las palabras clave?"),
    ("graph", "¿Quiénes son los autores puente del corpus?"),
    ("graph", "¿Qué autores colaboran más y cómo es la red de coautoría?"),
    ("forecast", "¿Cómo ha evolucionado el número de artículos y cuál es el pronóstico para los próximos años?"),
    ("forecast", "¿Cuál es la tendencia del secado solar en invernaderos?"),
    ("forecast", "¿Cuál es el pronóstico de artículos sobre agrovoltaica?"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="Agrovoltaics")
    args = ap.parse_args()
    s = ROOT / "data" / "sessions" / args.session
    out = [f"# Prueba Capa 5 — sesión {args.session}\n", f"Corrida: {datetime.now():%Y-%m-%d %H:%M}\n"]
    for esperado, q in PREGUNTAS:
        t = time.time()
        st = run_agent(q, db_path=str(s / "db" / "bibliometria.db"), chroma_dir=str(s / "chroma"))
        dt = time.time() - t
        print(f"[{st['intent']}] (esperada {esperado}) {dt:.1f}s  {q}", flush=True)
        out += [f"## {q}\n", f"**Ruta:** `{st['intent']}` (esperada `{esperado}`) · {dt:.1f} s\n",
                f"**Respuesta:**\n\n{st['answer']}\n",
                "<details><summary>Análisis que recibió el LLM</summary>\n\n```\n"
                f"{st.get('network_context', '')}\n```\n</details>\n", "---\n"]
    path = ROOT / "benchmark" / "agrovoltaics" / "results" / f"prueba_capa5_{args.session}_{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print("Guardado en", path)


if __name__ == "__main__":
    main()
