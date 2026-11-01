"""
intent_classifier.py — Clasificación de intención con LLM
==========================================================
Re-verifica la clasificación sql/rag/hybrid que hizo la Capa 1,
usando el LLM para mayor precisión en casos ambiguos.

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from src.layer1_schema.models import SchemaContext

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "glm4:9b")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))  # tope de tokens de salida: corta los bucles de texto basura de glm4

INTENT_SYSTEM_PROMPT = """Eres un clasificador de intención para un sistema de consulta bibliométrica.
Dada una pregunta del usuario, determina el canal de respuesta.

CANALES:
- sql: La pregunta tiene respuesta exacta con una consulta SQL.
  Ejemplos: conteos, rankings, filtros por año/país/cuartil, top-N, promedios.
  
- rag: La pregunta necesita búsqueda semántica en los abstracts/contenido.
  Ejemplos: "papers sobre X", "artículos que hablan de Y", "temas relacionados con Z".

- hybrid: La pregunta necesita AMBOS — SQL para filtrar + RAG para buscar por contenido.
  Ejemplos: "los 5 papers más citados sobre innovación" (citados=SQL, innovación=RAG).

Responde ÚNICAMENTE con una de estas tres palabras: sql, rag, hybrid"""

INTENT_USER_TEMPLATE = """Clasifica esta pregunta:

PREGUNTA: {query}

ENTIDADES DETECTADAS: {entities}

CANAL (responde solo sql, rag o hybrid):"""


def classify_intent(ctx: SchemaContext, history: list[dict] | None = None) -> str:
    """
    Re-clasifica la intención de la query usando el LLM.

    Si el LLM no da una respuesta válida, mantiene la clasificación
    original de la Capa 1.

    Parámetros
    ----------
    ctx : SchemaContext
        Contexto producido por la Capa 1.
    history : list[dict] | None
        Turnos previos de la conversación, para clasificar bien preguntas
        de seguimiento que dependen del contexto anterior.

    Retorna
    -------
    str
        "sql", "rag" o "hybrid"
    """
    from src.layer2_agent.answer_synthesizer import _format_history

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.0,
        num_predict=OLLAMA_NUM_PREDICT,
    )

    user_msg = _format_history(ctx.query, history) + INTENT_USER_TEMPLATE.format(
        query=ctx.query,
        entities=ctx.entities,
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ])

        # Extraer la clasificación de la respuesta
        answer = response.content.strip().lower()

        # Buscar sql, rag o hybrid en la respuesta
        for canal in ["hybrid", "rag", "sql"]:
            if canal in answer:
                return canal

        # Fallback: mantener clasificación de Capa 1
        return ctx.query_type

    except Exception:
        # Si el LLM falla, mantener la clasificación de Capa 1
        return ctx.query_type


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.layer1_schema.schema_linker import link_schema

    import argparse
    parser = argparse.ArgumentParser(description="Clasificar intención de una query")
    parser.add_argument("--query", "-q", type=str, required=True)
    args = parser.parse_args()

    ctx = link_schema(args.query)
    canal_capa1 = ctx.query_type
    canal_llm   = classify_intent(ctx)

    print(f"\n  Query: '{args.query}'")
    print(f"  Canal Capa 1 (regex):  {canal_capa1}")
    print(f"  Canal LLM (verificado): {canal_llm}")
    if canal_capa1 != canal_llm:
        print(f"  ⚠ Discrepancia — se usa el del LLM: {canal_llm}")
    else:
        print(f"  ✓ Coinciden")
