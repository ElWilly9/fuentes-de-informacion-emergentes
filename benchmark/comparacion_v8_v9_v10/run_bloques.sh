#!/bin/bash
# Bloques 1-3 (retomable por pregunta: cada celda/benchmark reanuda desde su .jsonl). Lanzar con lanzar.ps1 (independiente de la sesión).
cd "$(dirname "$0")"; HERE="$(pwd)"; mkdir -p logs_bloques
LOG="$HERE/logs_bloques/bloques.log"
PY="C:/Users/PAE ML SQL RAG/Documents/limpio/fuentes-de-informacion-emergentes/.venv/Scripts/python.exe"
export PYTHONIOENCODING=utf-8
st() { echo "=== $(date -Iseconds) $*" >> "$LOG"; }
# Bloque 1: sets de desarrollo, V8 -> V9 -> V10 -> V10 sin consenso (TEMP0=1 lo fija run_cell)
for c in v8 v9 v10 v10_sinconsenso; do
  for d in plantillas prueba prueba2 prueba3 prueba4 coffee generalizacion; do
    st "B1 $c $d"; "$PY" run_cell.py --config $c --dev $d --out results_dev >> "$HERE/logs_bloques/b1_${c}_${d}.log" 2>&1; st "fin B1 $c $d rc=$?"
  done
done
# Bloque 2: V9 en los bancos externos (V8 y V10 sin consenso ya existen)
L="C:/Users/PAE ML SQL RAG/Documents/limpio"
cd "$L/wt_cmp_v9"; export SQL_ENSEMBLE=1 RUN_TAG=_v9
st "B2 spider v9";  "$PY" benchmark/externos/spider/run_spider.py --mode agente2 --n 300 >> "$HERE/logs_bloques/b2_spider.log" 2>&1; st "fin spider rc=$?"
st "B2 bird v9";    "$PY" benchmark/externos/bird/run_bird.py --mode agente2 --n 300 >> "$HERE/logs_bloques/b2_bird.log" 2>&1; st "fin bird rc=$?"
st "B2 hotpot v9";  "$PY" benchmark/externos/hotpotqa/run_hotpotqa.py --n 300 --suffix _v9 >> "$HERE/logs_bloques/b2_hotpot.log" 2>&1; st "fin hotpot rc=$?"
# Bloque 3: WikiEval (RAG idéntico en las 3 versiones: una sola generación con wt_cmp_v10), juez glm4:9b local
unset RUN_TAG SQL_ENSEMBLE; cd "$L/wt_cmp_v10"
# WikiEval omitido por pedido de William                                                                                                                                     
# WikiEval omitido por pedido de William                                                                                                                                                       
echo BLOQUES_COMPLETOS >> "$LOG"
