#!/bin/bash
# V10 CON consenso (SQL_ENSEMBLE por defecto) en los 7 sets de desarrollo. Retomable por pregunta.
cd "$(dirname "$0")"; HERE="$(pwd)"; mkdir -p logs_bloques
PY="C:/Users/PAE ML SQL RAG/Documents/limpio/fuentes-de-informacion-emergentes/.venv/Scripts/python.exe"; export PYTHONIOENCODING=utf-8
for d in plantillas prueba prueba2 prueba3 prueba4 coffee generalizacion; do
  echo "=== $(date -Iseconds) B1 v10 $d" >> "$HERE/logs_bloques/v10_dev.log"
  "$PY" run_cell.py --config v10 --dev $d --out results_dev >> "$HERE/logs_bloques/b1_v10_${d}.log" 2>&1
  echo "=== fin v10 $d rc=$?" >> "$HERE/logs_bloques/v10_dev.log"
done
echo V10_DEV_COMPLETO >> "$HERE/logs_bloques/v10_dev.log"
