"""
query_rewriter.py — Reescritura de queries para soporte multi-turno
===================================================================
Toma la query actual del usuario y el historial de la conversación para
generar una "standalone query" (consulta independiente).

Esto es esencial para resolver anáforas y elipsis (ej. "el primero", "de ese autor").
"""

import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "glm4:9b")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))  # tope de tokens de salida: corta los bucles de texto basura de glm4

REWRITE_SYSTEM_PROMPT = """Eres un experto en procesamiento de lenguaje natural.
Tu tarea es reescribir la pregunta actual del usuario para que sea una consulta independiente y completa,
utilizando el historial de la conversación si es necesario para resolver referencias (como "él", "el primero", "ese autor", "de ese año").

REGLAS:
1. Si la pregunta ya es independiente y completa, devuélvela EXACTAMENTE igual.
2. Si la pregunta contiene referencias al historial, sustitúyelas por la entidad concreta mencionada anteriormente.
3. Mantén el idioma original (español).
4. No respondas la pregunta, SOLO reescríbela.
5. No añadas comentarios como "Aquí tienes la query reescrita:".
6. Sé preciso y directo.

EJEMPLOS:
- Historial: [Usuario: "¿Quién es el autor más citado?", Asistente: "El autor más citado es Juan Pérez."]
  Query: "¿De dónde es?"
  Reescritura: "¿De dónde es el autor Juan Pérez?"

- Historial: [Usuario: "Dame los 5 artículos más citados", Asistente: "1. Art A, 2. Art B..."]
  Query: "¿De qué trata el primero?"
  Reescritura: "¿De qué trata el artículo 'Art A'?"

- Historial: []
  Query: "¿Cuántos artículos hay?"
  Reescritura: "¿Cuántos artículos hay?"
"""

def rewrite_query(query: str, history: list[dict] | None = None) -> str:
    """
    Convierte una query ambigua en una consulta independiente basada en el historial.
    """
    if not history:
        return query

    # Formatear historial para el LLM
    history_text = ""
    for i, turn in enumerate(history, 1):
        history_text += f"Turno {i}:\n Usuario: {turn.get('question', '')}\n Asistente: {turn.get('answer', '')}\n\n"

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.0, # Determinista para reescritura
        num_predict=OLLAMA_NUM_PREDICT,
    )

    user_msg = f"HISTORIAL DE CONVERSACIÓN:\n{history_text}\n\nPREGUNTA ACTUAL: {query}\n\nQUERY REESCRITA:"

    try:
        response = llm.invoke([
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
        rewritten = response.content.strip()

        # Si el LLM devuelve la misma query o algo muy similar, lo aceptamos
        return rewritten if rewritten else query
    except Exception as e:
        print(f"Error en reescritura de query: {e}")
        return query
