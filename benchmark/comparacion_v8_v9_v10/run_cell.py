"""
run_cell.py — Corre UNA celda (configuración × set held-out) de la comparación V8/V9/V10.

  python run_cell.py --config v10 --set 5

Configuraciones (cada una desde su worktree/commit, sin tocar src/ ni la carpeta principal):
  v8               wt_cmp_v8  (3875669)                                   dos modelos: glm4:9b + qwen2.5-coder:7b
  glm4solo         wt_cmp_v8  + OLLAMA_SQL_MODEL=glm4:9b SQL_PROMPT=agente
  v9               wt_cmp_v9  (28b1a39)                                   consenso de 3 candidatas
  v10              wt_cmp_v10 (dfccb2d)
  v10_sinconsenso  wt_cmp_v10 + SQL_ENSEMBLE=0                            una sola candidata (coder/ddl)

Mismo puntaje automático que run_plantillas.py (copia en run_plantillas_ref.py), TEMP0=1. Además de lo habitual guarda
el número de llamadas a ChatOllama.invoke por pregunta (total y por modelo; no cuenta embeddings ni la traducción por
HTTP) contando desde fuera, sin modificar el agente. Retoma si se corta.
"""

import argparse
import collections
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMPIO = Path(r"C:\Users\PAE ML SQL RAG\Documents\limpio")
CONFIGS = {
    "v8": ("wt_cmp_v8", {}),
    "glm4solo": ("wt_cmp_v8", {"OLLAMA_SQL_MODEL": "glm4:9b", "SQL_PROMPT": "agente"}),
    "v9": ("wt_cmp_v9", {}),
    "v10": ("wt_cmp_v10", {}),
    "v10_sinconsenso": ("wt_cmp_v10", {"SQL_ENSEMBLE": "0"}),
}

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True, choices=list(CONFIGS))
ap.add_argument("--set", type=int, choices=[3, 4, 5])
ap.add_argument("--dev", help="set de desarrollo (plantillas, prueba, prueba2, prueba3, prueba4, coffee, generalizacion)")
ap.add_argument("--limit", type=int, default=0, help="solo las primeras N preguntas (prueba de humo)")
ap.add_argument("--out", default="results")
args = ap.parse_args()
# (16-nov) V10 con consenso en sets de desarrollo: reactivado por pedido de William

tree_name, extra_env = CONFIGS[args.config]
TREE = LIMPIO / tree_name
os.environ.update({"TEMP0": "1", **extra_env})
for k in ("OLLAMA_SQL_MODEL", "SQL_PROMPT", "SQL_ENSEMBLE"):
    if k not in extra_env:
        os.environ.pop(k, None)
os.chdir(TREE)
sys.path.insert(0, str(TREE))
sys.path.insert(0, str(HERE))

import run_plantillas_ref as rp  # noqa: E402  (aplica TEMP0 y el tope de espera al importarse)
from langchain_ollama import ChatOllama  # noqa: E402

# run_plantillas_ref inserta SU raíz (este worktree, con otro src/) en sys.path: dejar solo el árbol de la versión primero.
sys.path[:] = [str(TREE)] + [p for p in sys.path if Path(p or ".").resolve() not in (HERE.parent.parent.resolve(), TREE.resolve())]

# ── contador de llamadas (por encima del parche TEMP0, sin tocar el agente) ──────────────────────────────────
CALLS = collections.Counter()
_inv = ChatOllama.invoke


def _counted(self, *a, **k):
    CALLS[self.model] += 1
    return _inv(self, *a, **k)


ChatOllama.invoke = _counted


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def src_hash(root: Path) -> str:
    h = hashlib.sha256()
    for f in sorted((root / "src").rglob("*.py")):
        h.update(f.relative_to(root).as_posix().encode())
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


DATA = HERE / "datos"
SETNAME = args.dev or f"set{args.set}"
if args.dev:
    qfile = DATA / "dev" / f"preguntas_{args.dev}.json"
    raw = qfile.read_bytes()
    h_raw = hashlib.sha256(raw).hexdigest()
else:
    qfile = DATA / f"preguntas_heldout{args.set}.json"
    frozen = json.loads((DATA / f"congelado_heldout{args.set}.json").read_text(encoding="utf-8"))
    raw = qfile.read_bytes()
    h_raw = hashlib.sha256(raw).hexdigest()
    h_crlf = hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
    if frozen["dataset_sha256"] not in (h_raw, h_crlf):
        sys.exit(f"El dataset del set {args.set} NO coincide con el congelado: abortando.")
head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, cwd=TREE).strip()
dirty = subprocess.check_output(["git", "status", "--short", "--", ":(glob)src/**/*.py"], text=True, cwd=TREE).strip()
if dirty:
    sys.exit(f"src/ de {tree_name} tiene cambios sin commit: abortando.\n{dirty}")
SH = src_hash(TREE)
EXPECTED = {"wt_cmp_v8": "dd489e0d489f", "wt_cmp_v9": "ba0ec83cb347", "wt_cmp_v10": "a7f6aa75e5e6"}
if SH[:12] != EXPECTED[tree_name]:
    sys.exit(f"CHECK_SRC: src {SH[:12]} no es el de {tree_name}: abortando.")
print(f"[verif] config={args.config} set={SETNAME} dataset verificado; árbol {tree_name} HEAD {head}; src {SH[:12]}",
      flush=True)

items = json.loads(raw.decode("utf-8"))
if args.limit:
    items = items[: args.limit]
out_dir = HERE / args.out
out_dir.mkdir(exist_ok=True)
cache = out_dir / f"{args.config}__{SETNAME}.jsonl"
done = {json.loads(l)["id"] for l in cache.read_text(encoding="utf-8").splitlines()} if cache.exists() else set()

# ── calentamiento (fuera de los tiempos): carga glm4, el coder (si se usa) y el embedder ─────────────────────
import requests  # noqa: E402

for m in {"glm4:9b", os.environ.get("OLLAMA_SQL_MODEL", "qwen2.5-coder:7b")}:
    try:
        requests.post("http://localhost:11434/api/generate",
                      json={"model": m, "prompt": "hola", "stream": False, "options": {"num_predict": 4}}, timeout=300)
    except Exception as e:
        print("calentamiento falló", m, e)
requests.post("http://localhost:11434/api/embeddings", json={"model": "nomic-embed-text", "prompt": "hola"}, timeout=120)

from src.layer2_agent.graph import run_agent  # noqa: E402
import src.layer2_agent.graph as _g  # noqa: E402
if Path(_g.__file__).resolve().parents[2] != TREE.resolve():
    sys.exit(f"Se importó src/ de otro árbol: {_g.__file__}")
print("[verif] src importado desde", _g.__file__, flush=True)

SESSIONS = TREE / "data" / "sessions"
print(f"{len(items)} preguntas ({len(done)} ya hechas)", flush=True)
for it in items:
    if it["id"] in done:
        continue
    session = SESSIONS / it["corpus"]
    CALLS.clear()
    t0 = time.time()
    try:
        st = run_agent(it["pregunta"], db_path=str(session / "db" / "bibliometria.db"),
                       chroma_dir=str(session / "chroma"))
        err = None
    except Exception as e:
        st, err = {}, f"{type(e).__name__}: {e}"
    dt = round(time.time() - t0, 1)
    answer = st.get("answer") or ""
    rec = {**it, "config": args.config, "set": SETNAME, "intent": st.get("intent"), "respuesta": answer,
           "sql": st.get("sql_visible") or st.get("generated_sql") or "", "error": err,
           "puntaje": round(rp.score(it, answer), 3), "latencia_s": dt,
           "llm_calls": sum(CALLS.values()), "llm_calls_por_modelo": dict(CALLS),
           "head": head, "src_sha": SH[:12], "fecha": datetime.now().isoformat(timespec="seconds")}
    with cache.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  {rec['id']} [{rec['tipo']}] ruta={rec['intent']} puntaje={rec['puntaje']} ({dt}s, {rec['llm_calls']} llamadas)",
          flush=True)

if sha(qfile) != h_raw:
    sys.exit("El dataset cambió durante la corrida: INVÁLIDA.")
print("[verif] dataset sin cambios al terminar; src:", "igual" if src_hash(TREE) == SH else "CAMBIÓ", flush=True)
