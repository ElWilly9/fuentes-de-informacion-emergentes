"""
graph.py — Grafo LangGraph que orquesta el flujo completo
==========================================================
Define el grafo de estados del agente RAG Text-to-SQL.

Flujo:
  SchemaContext → intent_classifier → [sql|rag|hybrid|followup|graph|community|forecast]
    → sql_generator → sql_validator → [error? → refiner (3x)] 
    → answer_synthesizer → respuesta

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import os
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from src.layer1_schema.models import SchemaContext
from src.layer1_schema.schema_linker import link_schema, build_value_hints, author_hints, column_types
from src.layer2_agent.query_rewriter import rewrite_query
from src.layer2_agent.intent_classifier import classify_intent
from src.layer2_agent.sql_generator import generate_sql
from src.layer2_agent.sql_validator import execute_sql, SQLResult
from src.layer2_agent.refiner import refine_sql
from src.layer2_agent.answer_synthesizer import synthesize_answer, articles_answer_question

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
    intent: str = ""               # sql / rag / hybrid / followup / graph / community / forecast
    generated_sql: str = ""
    sql_result: SQLResult | None = None
    retry_count: int = 0
    rag_results: list[str] = field(default_factory=list)
    articles_shown: list[dict] = field(default_factory=list)  # [{"sr", "title"}] mostrados en este turno
    network_context: str = ""      # Capa 5: análisis calculado que se le pasó al LLM

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


# ── Utilidades: artículos principales y memoria de artículos ──────────────────

# "de esos cinco", "de los anteriores", "el primero", "cuál de ellos"...
_REFERS_TO_PREVIOUS = re.compile(
    r"\b(es[oa]s|est[oa]s|ell[oa]s|anteriores|mencionad[oa]s|listad[oa]s|"
    r"que me (diste|mostraste)|de la lista|de tu respuesta|"
    r"(el|la) (primer[oa]?|segund[oa]|tercer[oa]?|cuart[oa]|quint[oa]|últim[oa]))\b",
    re.IGNORECASE,
)
_MAIN_FILTER = re.compile(r"\b((?:\w+\.)?ismainarticle)\s*=\s*(?:'1'|1|TRUE)\b", re.IGNORECASE)

NOTE_ONLY_REFERENCES = (
    "NOTA: entre los artículos principales del corpus (ismainarticle = 1) NO hubo resultados. "
    "Los resultados de abajo salen de las REFERENCIAS CITADAS (ismainarticle = 0), que no son "
    "artículos principales. El aviso al usuario ya se agrega aparte: no lo repitas, solo presenta los resultados.\n\n"
)
# Aviso fijo (no depende del LLM) cuando la respuesta sale de las referencias citadas
REFERENCES_PREFIX = (
    "En los artículos principales del corpus no hay resultados para esta consulta. "
    "Busqué en las referencias citadas (artículos que no son principales) y encontré esto:\n\n"
)
RAG_REFERENCES_PREFIX = (
    "En los artículos principales del corpus no encontré nada que responda esta pregunta. "
    "Busqué en las referencias citadas (artículos que no son principales) y encontré esto:\n\n"
)


def _fallback_to_references(result: SQLResult | None, db_path: str | None) -> SQLResult | None:
    """
    Si una consulta filtrada a artículos principales no devolvió filas, repite la misma
    consulta sobre las referencias citadas. Devuelve ese resultado o None si tampoco hay nada.
    """
    if not result or not result.success or result.row_count > 0:
        return None
    query = result.query or ""
    if not (_MAIN_FILTER.search(query) or re.search(r"\bcorpus_articles\b", query)):
        return None
    # La consulta estaba limitada a principales, ya sea por el filtro del LLM o por la vista corpus_articles
    alt_sql = re.sub(r"\bcorpus_articles\b", "reference_articles", _MAIN_FILTER.sub(r"\1 = 0", query))
    alt = execute_sql(alt_sql, db_path=db_path) if db_path else execute_sql(alt_sql)
    return alt if alt.success and alt.row_count > 0 else None


def _articles_from_sql(result: SQLResult | None, db_path: str | None, limit: int = 15) -> list[dict]:
    """Identifica (SR, título) de los artículos que aparecen en las filas de un resultado SQL."""
    if not result or not result.success or not result.rows or not db_path:
        return []
    cols = {c.lower(): c for c in result.columns}
    if "sr" not in cols and "title" not in cols:
        return []
    out, conn = [], sqlite3.connect(db_path)
    for row in result.rows[:limit]:
        if "sr" in cols:
            r = conn.execute("SELECT SR, title FROM Article WHERE SR = ? ORDER BY ismainarticle DESC",
                             (row.get(cols["sr"]),)).fetchone()
        else:
            r = conn.execute("SELECT SR, title FROM Article WHERE UPPER(TRIM(title)) = UPPER(TRIM(?)) "
                             "ORDER BY ismainarticle DESC", (str(row.get(cols["title"]) or ""),)).fetchone()
        if r and r[0] not in {a["sr"] for a in out}:
            out.append({"sr": r[0], "title": r[1]})
    conn.close()
    return out


def _articles_from_rag(rag_result) -> list[dict]:
    if not rag_result or not getattr(rag_result, "success", False):
        return []
    return [{"sr": a["SR"], "title": a.get("title", "")} for a in rag_result.articles]


def _rag_labels(articles: list[dict]) -> list[str]:
    """Títulos para la lista de fuentes, marcando de dónde sale cada uno."""
    tag = {"principal": "[corpus]", "referencia": "[referencia citada]", "anterior": "[respuesta anterior]"}
    return [f"{tag.get(a.get('origen'), '')} {a.get('title', '')}".strip() for a in articles]


def _previous_articles(state: dict) -> list[dict]:
    """Artículos mostrados en el turno anterior, si la pregunta actual se refiere a ellos."""
    history = state.get("history") or []
    if not history or not _REFERS_TO_PREVIOUS.search(state.get("user_query", "")):
        return []
    return history[-1].get("articles") or []


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
    ctx.value_hints = build_value_hints(state.get("db_path"), ctx.relevant_tables) + author_hints(state.get("db_path"), query)
    ctx.column_types = column_types(state.get("db_path"), ctx.relevant_tables)
    state["schema_context"] = ctx
    state["intent"] = ctx.query_type
    return state


def node_classify_intent(state: dict) -> dict:
    ctx = state["schema_context"]
    # Pregunta sobre artículos que el agente ya mostró: se responde con esos artículos
    if _previous_articles(state):
        intent = "followup"
    else:
        # Redes, frentes y tendencias se detectan con reglas (Capa 5); el resto lo decide el LLM
        from src.layer5_network.context import detect_network_intent
        intent = detect_network_intent(state.get("user_query", "")) or classify_intent(ctx, history=state.get("history"))
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
    note = ""
    alt = _fallback_to_references(result, state.get("db_path"))
    if alt:
        result, note = alt, NOTE_ONLY_REFERENCES
        state["sql_result"] = result
        state["sql_visible"] = result.query
    answer = synthesize_answer(ctx, result, history=state.get("history"), note=note)
    state["answer"] = (REFERENCES_PREFIX if note else "") + answer
    state["success"] = result.success if result else False
    state["articles_shown"] = _articles_from_sql(result, state.get("db_path"))
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
    from src.layer3_rag.retriever import search_by_origin
    from src.layer2_agent.refiner import generate_and_validate
    from src.layer2_agent.answer_synthesizer import synthesize_hybrid

    ctx = state["schema_context"]

    # Lado SQL (con generación + validación + refine por error)
    db_path = state.get("db_path")
    sql_result = generate_and_validate(ctx, db_path=db_path) if db_path else generate_and_validate(ctx)
    note = ""
    alt = _fallback_to_references(sql_result, db_path)
    if alt:
        sql_result, note = alt, NOTE_ONLY_REFERENCES
    state["sql_result"] = sql_result
    state["sql_visible"] = sql_result.query if sql_result else ""

    # Lado RAG (búsqueda semántica sobre abstracts de los artículos principales)
    rag_result = search_by_origin(
        ctx.query,
        chroma_dir=state.get("chroma_dir"),
        db_path=state.get("db_path"),
        top_k=int(os.getenv("RAG_TOP_K", "5"))
    )
    if getattr(rag_result, "success", False):
        state["rag_results"] = _rag_labels(rag_result.articles)
    state["articles_shown"] = _articles_from_sql(sql_result, db_path) + _articles_from_rag(rag_result)

    # Síntesis combinada
    answer = synthesize_hybrid(ctx, sql_result, rag_result, state.get("history"), note=note)
    state["answer"] = (REFERENCES_PREFIX if note else "") + answer
    state["success"] = bool(
        (sql_result and sql_result.success) or getattr(rag_result, "success", False)
    )
    return state

def node_rag_search(state: dict) -> dict:
    """Nodo RAG: búsqueda semántica sobre abstracts."""
    from src.layer3_rag.retriever import search_by_origin, format_rag_context

    from src.layer2_agent.answer_synthesizer import _format_history
    from langchain_ollama import ChatOllama

    ctx = state["schema_context"]
    llm = ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "glm4:9b"),
        temperature=0.3,
        num_predict=int(os.getenv("OLLAMA_NUM_PREDICT", "2048")),
    )
    history_text = _format_history(ctx.query, state.get("history"))

    def answer_with(rag_result) -> str:
        """Sintetiza con el LLM a partir de los artículos recuperados."""
        response = llm.invoke([
            {"role": "system", "content": "Eres un experto en bibliometria. Responde en espanol, citando los articulos encontrados con titulo, ano y revista. Se conciso."},
            {"role": "user", "content": f"{history_text}PREGUNTA: {ctx.query}\n\nARTICULOS ENCONTRADOS:\n{format_rag_context(rag_result)}\n\nRESPUESTA:"},
        ])
        return response.content.strip()

    def search(origin: str):
        return search_by_origin(ctx.query, chroma_dir=state.get("chroma_dir"),
                                db_path=state.get("db_path"), origin=origin,
                                top_k=int(os.getenv("RAG_TOP_K", "5")))

    # 1) Artículos principales del corpus; 2) solo si un juez dice que no responden, referencias citadas
    principales = search("principal")
    if not principales.success:
        state["answer"] = f"Error en busqueda semantica: {principales.error}"
        state["success"] = False
        return state
    shown = list(principales.articles)
    answer = None
    if not articles_answer_question(ctx.query, principales):
        referencias = search("referencia")
        if referencias.success and articles_answer_question(ctx.query, referencias):
            shown += referencias.articles
            answer = RAG_REFERENCES_PREFIX + answer_with(referencias)
    if answer is None:
        # Si las referencias tampoco sirven, se responde con los principales (el juez puede equivocarse)
        answer = answer_with(principales)

    state["answer"] = answer
    state["rag_results"] = _rag_labels(shown)
    state["articles_shown"] = [{"sr": a["SR"], "title": a.get("title", "")} for a in shown]
    state["success"] = True
    return state

def node_followup(state: dict) -> dict:
    """
    Nodo followup: la pregunta se refiere a artículos que el agente ya mostró
    ("de esos cinco, ¿cuál…?"). Responde con esos artículos y, aparte, sugiere
    otros del corpus que no estaban en la lista.
    """
    from src.layer3_rag.retriever import search_by_origin, _enrich_with_db
    from src.layer2_agent.answer_synthesizer import synthesize_followup

    ctx = state["schema_context"]
    previous = _previous_articles(state)
    db_path = state.get("db_path")

    anteriores = _enrich_with_db(
        [{"SR": a["sr"], "title": a["title"], "rank": i, "score": "-", "origen": "anterior"}
         for i, a in enumerate(previous, 1)], db_path)
    suggestions = search_by_origin(
        ctx.query, chroma_dir=state.get("chroma_dir"), db_path=db_path,
        top_k=int(os.getenv("FOLLOWUP_SUGGESTIONS", "3")), exclude_srs=[a["sr"] for a in previous])
    for a in getattr(suggestions, "articles", []):
        a["rank"] += len(anteriores)  # numeración continua: no confundir sugerencias con los anteriores

    state["answer"] = synthesize_followup(ctx, anteriores, suggestions, db_path, state.get("history"))
    state["rag_results"] = _rag_labels(anteriores) + _rag_labels(getattr(suggestions, "articles", []))
    state["articles_shown"] = previous + _articles_from_rag(suggestions)
    state["success"] = True
    return state


def node_network(state: dict) -> dict:
    """
    Nodo Capa 5 (graph / community / forecast): calcula redes, comunidades o series de tiempo
    sobre la BD de la sesión y el LLM solo redacta la respuesta con esas cifras.
    """
    from src.layer5_network.context import network_context
    from src.layer2_agent.answer_synthesizer import synthesize_network, log_error

    intent = state.get("intent", "community")
    query = state.get("rewritten_query") or state["user_query"]
    try:
        context, articles = network_context(intent, state.get("db_path"), query)
    except Exception as e:
        log_error(f"network_context ({intent})", e)
        state["answer"] = f"No se pudo calcular el análisis de redes: {type(e).__name__}: {e}"
        state["success"] = False
        return state
    state["network_context"] = context
    state["answer"] = synthesize_network(query, intent, context, state.get("history"))
    state["articles_shown"] = articles
    state["success"] = True
    return state


# ── Funciones de routing ──────────────────────────────────────────────────────

def route_by_intent(state: dict) -> str:
    """Decide el camino según la intención clasificada."""
    intent = state.get("intent", "sql")
    if intent == "rag":
        return "rag"
    if intent == "hybrid":
        return "hybrid"
    if intent == "followup":
        return "followup"
    if intent in ("graph", "community", "forecast"):
        return "network"
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
    graph.add_node("followup",         node_followup)
    graph.add_node("network",          node_network)

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
            "followup": "followup",
            "network": "network",
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
    graph.add_edge("followup",    END)
    graph.add_edge("network",     END)

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
        "articles_shown": [],
        "history": history,
        "reflection_feedback": "",
        "reflect_count": 0,
        "reflection_adequate": True,
        "answer": "",
        "network_context": "",
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
        "articles": final_state.get("articles_shown", []),
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
