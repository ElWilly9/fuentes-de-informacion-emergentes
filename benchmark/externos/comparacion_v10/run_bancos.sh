#!/bin/bash
# V10 sin consenso (SQL_ENSEMBLE=0) en los bancos externos, desde el worktree limpio wt_cmp_v10 (dfccb2d). Retomable.
cd "$(dirname "$0")"; LOG="$(pwd)/logs"
PY="C:/Users/PAE ML SQL RAG/Documents/limpio/fuentes-de-informacion-emergentes/.venv/Scripts/python.exe"
cd "C:/Users/PAE ML SQL RAG/Documents/limpio/wt_cmp_v10"
export SQL_ENSEMBLE=0 RUN_TAG=_v10sc PYTHONIOENCODING=utf-8
run() { n=$1; shift; echo "=== $(date -Iseconds) $n" >> "$LOG/bancos.log"; "$PY" "$@" >> "$LOG/$n.log" 2>&1; echo "=== fin $n rc=$? $(date -Iseconds)" >> "$LOG/bancos.log"; }
run spider  benchmark/externos/spider/run_spider.py --mode agente2 --n 300
run hotpotqa benchmark/externos/hotpotqa/run_hotpotqa.py --n 300
# omitido por pedido de William                                                             
run bird    benchmark/externos/bird/run_bird.py --mode agente2 --n 300
echo BANCOS_COMPLETOS >> "$LOG/bancos.log"
