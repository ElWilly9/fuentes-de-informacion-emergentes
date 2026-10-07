"""
graph.py — Grafo LangGraph que orquesta el flujo completo
==========================================================
Define el grafo de estados del agente RAG Text-to-SQL.

Flujo:
  SchemaContext → intent_classifier → [sql|rag|hybrid]
    → sql_generator → sql_validator → [error? → refiner (3x)] 
    → answer_synthesizer → respuesta

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from src.layer1_schema.models import SchemaContext
from src.layer1_schema.schema_linker import link_schema
from src.layer2_agent.query_rewriter import rewrite_query
from src.layer2_agent.intent_classifier import classify_intent
from src.layer2_agent.sql_generator import generate_sql
from src.layer2_agent.sql_validator import execute_sql, SQLResult
from src.layer2_agent.refiner import refine_sql
from src.layer2_agent.answer_synthesizer import synthesize_answer

load_dotenv()

SQL_MAX_RETRIES = int(os.getenv("SQL_MAX_RETRIES", "3"))
# Máximo de regeneraciones disparadas por la auto-reflexión (además del refine por error)
REFLECT_MAX_RETRIES = int(os.getenv("REFLECT_MAX_RETRIES", "1"))


# ── Estado del grafo ──────────────────────────────────────────────────────────

@dataclass
class AgentState:
    """Estado que se pasa entre nodos del grafo."""
    # Entrada
    user_query: str = ""
    rewritten_query: str = ""  # Query resuelta con el historial

    # Capa 1
    schema_context: SchemaContext | None = None

    # Capa 2
    intent: str = ""               # sql / rag / hybrid
    generated_sql: str = ""
    sql_result: SQLResult | None = None
    retry_count: int = 0
    rag_results: list[str] = field(default_factory=list)

    # Memoria conversacional (multi-turno)
    history: list[dict] = field(default_factory=list)

    # Auto-reflexión
    reflection_feedback: str = ""
    reflect_count: int = 0
    reflection_adequate: bool = True

    # Salida
    answer: str = ""
    sql_visible: str = ""          # SQL para mostrar al usuario
    success: bool = False
    db_path: str = ""               # Ruta a la BD SQLite utilizada
    chroma_dir: str = ""            # Ruta al índice de ChromaDB utilizado


# ── Nodos del grafo ───────────────────────────────────────────────────────────

def node_rewrite_query(state: dict) -> dict:
    """Nodo 0: resuelve anáforas y elipsis usando el historial."""
    query = state["user_query"]
    history = state.get("history")
    rewritten = rewrite_query(query, history)
    state["rewritten_query"] = rewritten
    return state


def node_schema_linking(state: dict) -> dict:
    """Nodo 1: ejecuta la Capa 1 completa."""
    query = state["rewritten_query"] or state["user_query"]
    ctx = link_schema(query, chroma_dir=state.get("chroma_dir"))
    state["schema_context"] = ctx
    state["intent"] = ctx.query_type
    return state


def node_classify_intent(state: dict) -> dict:
    ctx = state["schema_context"]
    intent = classify_intent(ctx, history=state.get("history"))
    state["intent"] = intent
    return state

def node_generate_sql(state: dict) -> dict:
    ctx = state["schema_context"]
    sql = generate_sql(
        ctx,
        history=state.get("history"),
        feedback=state.get("reflection_feedback") or None,
    )
    state["generated_sql"] = sql
    return state

def node_validate_sql(state: dict) -> dict:
    sql = state["generated_sql"]
    db_path = state.get("db_path")
    result = execute_sql(sql, db_path=db_path) if db_path else execute_sql(sql)
    state["sql_result"] = result
    state["sql_visible"] = result.query
    return state

def node_refine_sql(state: dict) -> dict:
    ctx = state["schema_context"]
    result = state["sql_result"]
    refined = refine_sql(ctx, result.query, result.error)
    state["generated_sql"] = refined
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state

def node_synthesize(state: dict) -> dict:
    ctx = state["schema_context"]
    result = state["sql_result"]
    answer = synthesize_answer(ctx, result, history=state.get("history"))
    state["answer"] = answer
    state["success"] = result.success if result else False
    return state


def node_reflect(state: dict) -> dict:
    """
    Nodo de auto-reflexión: juzga si la respuesta realmente responde la pregunta.
    Si no, marca para regenerar el SQL (hasta REFLECT_MAX_RETRIES veces).
    """
    from src.layer2_agent.answer_synthesizer import reflect_on_answer

    result = state.get("sql_result")
    reflect_count = state.get("reflect_count", 0)

    # No reflexionar si no hubo SQL exitoso o ya se agotaron los reintentos
    if not result or not result.success or reflect_count >= REFLECT_MAX_RETRIES:
        state["reflection_adequate"] = True
        return state

    ctx = state["schema_context"]
    adequate, critique = reflect_on_answer(
        ctx, result, state.get("answer", ""), history=state.get("history")
    )
    state["reflection_adequate"] = adequate
    if not adequate:
        state["reflection_feedback"] = critique
        state["reflect_count"] = reflect_count + 1
    return state


def node_hybrid(state: dict) -> dict:
    """
    Nodo hybrid: combina una consulta SQL (cifras exactas) con búsqueda
    semántica RAG (contexto temático) en una sola respuesta.
    """
    from src.layer3_rag.retriever import search_articles
    from src.layer2_agent.refiner import generate_and_validate
    from src.layer2_agent.answer_synthesizer import synthesize_hybrid

    ctx = state["schema_context"]

    # Lado SQL (con generación + validación + refine por error)
    db_path = state.get("db_path")
    sql_result = generate_and_validate(ctx, db_path=db_path) if db_path else generate_and_validate(ctx)
    state["sql_result"] = sql_result
    state["sql_visible"] = sql_result.query if sql_result else ""

    # Lado RAG (búsqueda semántica sobre abstracts)
    rag_result = search_articles(
        ctx.query,
        chroma_dir=state.get("chroma_dir"),
        db_path=state.get("db_path"),
        top_k=int(os.getenv("RAG_TOP_K", "5"))
    )
    if getattr(rag_result, "success", False):
        state["rag_results"] = [a.get("title", "") for a in rag_result.articles]

    # Síntesis combinada
    state["answer"] = synthesize_hybrid(ctx, sql_result, rag_result, state.get("history"))
    state["success"] = bool(
        (sql_result and sql_result.success) or getattr(rag_result, "success", False)
    )
    return state

def node_rag_search(state: dict) -> dict:
    """Nodo RAG: búsqueda semántica sobre abstracts."""
    from src.layer3_rag.retriever import search_articles, format_rag_context

    from src.layer2_agent.answer_synthesizer import _format_history

    ctx = state["schema_context"]
    rag_result = search_articles(
        ctx.query,
        chroma_dir=state.get("chroma_dir"),
        db_path=state.get("db_path"),
        top_k=int(os.getenv("RAG_TOP_K", "5"))
    )

    if rag_result.success:
        context_text = format_rag_context(rag_result)
        # Usar el LLM para sintetizar la respuesta con el contexto RAG
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "glm4:9b"),
            temperature=0.3,
        )
        history_text = _format_history(ctx.query, state.get("history"))
        response = llm.invoke([
            {"role": "system", "content": "Eres un experto en bibliometria. Responde en espanol, citando los articulos encontrados con titulo, ano y revista. Se conciso."},
            {"role": "user", "content": f"{history_text}PREGUNTA: {ctx.query}\n\nARTICULOS ENCONTRADOS:\n{context_text}\n\nRESPUESTA:"},
        ])
        state["answer"] = response.content.strip()
        state["rag_results"] = [a.get("title", "") for a in rag_result.articles]
        state["success"] = True
    else:
        state["answer"] = f"Error en busqueda semantica: {rag_result.error}"
        state["success"] = False

    return state

# ── Funciones de routing ──────────────────────────────────────────────────────

def route_by_intent(state: dict) -> str:
    """Decide el camino según la intención clasificada."""
    intent = state.get("intent", "sql")
    if intent == "rag":
        return "rag"
    if intent == "hybrid":
        return "hybrid"
    return "sql"


def route_after_validation(state: dict) -> str:
    """Decide si el SQL fue exitoso o necesita refinamiento."""
    result = state.get("sql_result")
    retry = state.get("retry_count", 0)

    if result and result.success:
        return "success"
    if retry >= SQL_MAX_RETRIES:
        return "max_retries"
    return "refine"


def route_after_reflect(state: dict) -> str:
    """Tras la auto-reflexión: terminar o regenerar el SQL con la crítica."""
    if state.get("reflection_adequate", True):
        return "done"
    return "retry"


# ── Construcción del grafo ────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construye el grafo LangGraph del agente.

    Flujo:
    rewrite_query → schema_linking → classify_intent → [sql: generate → validate → [refine] → synthesize]
                                       [rag: rag_search]
    """
    graph = StateGraph(dict)

    # Agregar nodos
    graph.add_node("rewrite_query",    node_rewrite_query)
    graph.add_node("schema_linking",   node_schema_linking)
    graph.add_node("classify_intent",  node_classify_intent)
    graph.add_node("generate_sql",     node_generate_sql)
    graph.add_node("validate_sql",     node_validate_sql)
    graph.add_node("refine_sql",       node_refine_sql)
    graph.add_node("synthesize",       node_synthesize)
    graph.add_node("reflect",          node_reflect)
    graph.add_node("rag_search",       node_rag_search)
    graph.add_node("hybrid",           node_hybrid)

    # Flujo principal
    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query", "schema_linking")
    graph.add_edge("schema_linking", "classify_intent")

    # Router por intención
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "sql": "generate_sql",
            "rag": "rag_search",
            "hybrid": "hybrid",
        }
    )

    # Flujo SQL
    graph.add_edge("generate_sql", "validate_sql")

    # Después de validar: éxito, refinar o rendirse
    graph.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "success":     "synthesize",
            "refine":      "refine_sql",
            "max_retries": "synthesize",
        }
    )

    # Refinar vuelve a validar
    graph.add_edge("refine_sql", "validate_sql")

    # Tras sintetizar: auto-reflexión
    graph.add_edge("synthesize", "reflect")
    graph.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {
            "done":  END,
            "retry": "generate_sql",   # regenerar con la crítica de la reflexión
        }
    )

    # Nodos finales
    graph.add_edge("rag_search",  END)
    graph.add_edge("hybrid",      END)

    return graph


def run_agent(query: str, history: list[dict] | None = None, db_path: str | None = None, chroma_dir: str | None = None) -> dict:
    """
    Ejecuta el agente completo para una query.

    Parámetros
    ----------
    query : str
        Pregunta del usuario en español.
    history : list[dict] | None
        Turnos previos de la conversación, cada uno {"question", "answer"}.
        Habilita la memoria conversacional (preguntas de seguimiento).
    db_path : str | None
        Ruta a la base de datos SQLite del corpus.
    chroma_dir : str | None
        Ruta al índice de ChromaDB del corpus.

    Retorna
    -------
    dict
        Estado final con answer, sql_visible, success, etc. Incluye `history`
        con el turno actual ya agregado, listo para la siguiente llamada.
    """
    graph = build_graph()
    app = graph.compile()

    history = list(history or [])

    initial_state = {
        "user_query": query,
        "rewritten_query": "",
        "schema_context": None,
        "intent": "",
        "generated_sql": "",
        "sql_result": None,
        "retry_count": 0,
        "rag_results": [],
        "history": history,
        "reflection_feedback": "",
        "reflect_count": 0,
        "reflection_adequate": True,
        "answer": "",
        "sql_visible": "",
        "success": False,
        "db_path": db_path,
        "chroma_dir": chroma_dir,
    }

    final_state = app.invoke(initial_state)

    # Agregar el turno actual al historial para la siguiente interacción
    final_state["history"] = history + [{
        "question": query,
        "answer": final_state.get("answer", ""),
    }]
    return final_state


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ejecutar el agente RAG Text-to-SQL completo")
    parser.add_argument("--query", "-q", type=str, required=True)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  AGENTE RAG TEXT-TO-SQL")
    print(f"  Query: '{args.query}'")
    print(f"{'='*60}\n")

    result = run_agent(args.query)

    print(f"\n{'='*60}")
    print(f"  RESULTADO")
    print(f"{'='*60}")
    print(f"\n  Éxito:  {result.get('success', False)}")
    print(f"  Canal:  {result.get('intent', 'N/A')}")

    if result.get("sql_visible"):
        print(f"\n  SQL ejecutado:")
        print(f"  {result['sql_visible']}")

    print(f"\n  Respuesta:")
    print(f"  {result.get('answer', 'Sin respuesta')}")
    print(f"\n{'='*60}")
