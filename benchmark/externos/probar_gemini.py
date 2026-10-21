"""
probar_gemini.py — ¿Sirve la clave de Gemini (nivel gratuito) como juez de RAGAS?
=================================================================================
Lee GEMINI_API_KEY del .env (nunca se imprime), lista los modelos Flash disponibles y hace
una llamada mínima con cada uno de los indicados para ver si responde o si da error de cuota.

    python benchmark/externos/probar_gemini.py
    python benchmark/externos/probar_gemini.py --models gemini-2.5-flash gemini-2.5-flash-lite
"""

import argparse
import os
import sys

import httpx
from dotenv import load_dotenv

API = "https://generativelanguage.googleapis.com/v1beta"

load_dotenv()
key = os.getenv("GEMINI_API_KEY", "").strip()
if not key:
    sys.exit("Falta GEMINI_API_KEY en el .env")
headers = {"x-goog-api-key": key}

p = argparse.ArgumentParser()
p.add_argument("--models", nargs="*")
args = p.parse_args()

r = httpx.get(f"{API}/models", headers=headers, params={"pageSize": 1000}, timeout=30)
if r.status_code != 200:
    sys.exit(f"Listar modelos falló: HTTP {r.status_code} {r.json().get('error', {}).get('message', '')[:300]}")
flash = [m["name"].removeprefix("models/") for m in r.json().get("models", [])
         if "flash" in m["name"] and "generateContent" in m.get("supportedGenerationMethods", [])]
print("Modelos Flash con generateContent:")
for name in flash:
    print("  -", name)

for model in args.models or [m for m in flash if "preview" not in m and "exp" not in m][:4]:
    body = {"contents": [{"parts": [{"text": 'Reply only with the JSON {"ok": true}'}]}]}
    r = httpx.post(f"{API}/models/{model}:generateContent", headers=headers, json=body, timeout=60)
    if r.status_code == 200:
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"[OK]  {model}: {text[:60]}")
    else:
        err = r.json().get("error", {})
        print(f"[ERR] {model}: HTTP {r.status_code} {err.get('status', '')} — {err.get('message', '')[:200]}")
