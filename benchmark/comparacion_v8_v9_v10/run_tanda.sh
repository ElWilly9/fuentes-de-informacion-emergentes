#!/bin/bash
# Tanda única: 5 configuraciones x 3 sets, en orden set-mayor para repartir la deriva del equipo entre versiones.
cd "$(dirname "$0")"
PY="C:/Users/PAE ML SQL RAG/Documents/limpio/fuentes-de-informacion-emergentes/.venv/Scripts/python.exe"
mkdir -p logs
{ date -Iseconds; curl -s localhost:11434/api/version; echo; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv; } > logs/entorno_inicio.txt 2>&1
for s in 3 4 5; do
  for c in v8 glm4solo v9 v10 v10_sinconsenso; do
    echo "=== $(date -Iseconds) $c set$s" >> logs/tanda.log
    PYTHONIOENCODING=utf-8 "$PY" run_cell.py --config $c --set $s >> logs/${c}__set${s}.log 2>&1
    echo "=== fin $c set$s rc=$?" >> logs/tanda.log
  done
done
curl -s localhost:11434/api/ps > logs/ollama_ps_fin.json
echo TANDA_COMPLETA >> logs/tanda.log
