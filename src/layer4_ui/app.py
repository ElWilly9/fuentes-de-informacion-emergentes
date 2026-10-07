import os
import sys
import shutil
from pathlib import Path
from typing import Optional

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

import streamlit as st
from dotenv import load_dotenv

# Import project components
from src.layer2_agent.graph import run_agent
from src.services.ingestion_service import IngestionService

load_dotenv()

# Global Configuration
BASE_SESSIONS_DIR = Path("data/sessions")
BASE_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="📚 RAG Text-to-SQL: Demo Limpio", layout="wide")

# ── CSS for better look ─────────────────────────────────────────────────────────
st.markdown("""
    <style>
    .stChatMessage {
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .sql-block {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.9em;
        color: #31333F;
        border-left: 5px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# ── Session State Initialization ───────────────────────────────────────────────
if "app_state" not in st.session_state:
    st.session_state.app_state = "SETUP"  # SETUP or CHAT

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_session" not in st.session_state:
    st.session_state.current_session = None

# ── Helper: Get Active Session Paths ──────────────────────────────────────────
def get_session_paths(session_name: str):
    session_dir = BASE_SESSIONS_DIR / session_name
    return {
        "root": session_dir,
        "db": session_dir / "db" / "bibliometria.db",
        "chroma": session_dir / "chroma"
    }

# ── Sidebar: Session Management ────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuración")

    # 1. Session Selection
    available_sessions = [d.name for d in BASE_SESSIONS_DIR.iterdir() if d.is_dir()]

    if available_sessions:
        selected_session = st.selectbox(
            "Selecciona una Sesión activa",
            available_sessions,
            index=0 if not st.session_state.current_session else
                    available_sessions.index(st.session_state.current_session) if st.session_state.current_session in available_sessions else 0
        )
        if selected_session != st.session_state.current_session:
            st.session_state.current_session = selected_session
            st.session_state.app_state = "CHAT"
            st.session_state.messages = [] # Reset chat when switching session
            st.rerun()

        # Botón para borrar la sesión seleccionada
        if st.button("🗑️ Borrar Sesión Seleccionada"):
            session_path = BASE_SESSIONS_DIR / selected_session
            if session_path.exists():
                shutil.rmtree(session_path)

            st.session_state.current_session = None
            st.session_state.app_state = "SETUP"
            st.session_state.messages = []
            st.rerun()
    else:
        st.info("No hay sesiones creadas todavía.")

    st.divider()

    # 2. Upload New Corpus
    st.subheader("📤 Cargar Nuevo Corpus")
    new_corpus_name = st.text_input("Nombre de la Sesión", placeholder="Ej: Agrovoltaics_2024")
    uploaded_file = st.file_uploader("Sube el Excel de Scopus (.xlsx)", type=["xlsx"])

    if st.button("🚀 Iniciar Pipeline de Ingesta"):
        if not new_corpus_name or not uploaded_file:
            st.error("Por favor, ingresa un nombre para la sesión y sube un archivo.")
        else:
            try:
                with st.status("🚀 Preparando Corpus...", expanded=True) as status:
                    st.write("Guardando archivo...")

                    # Create session folders
                    session_dir = BASE_SESSIONS_DIR / new_corpus_name
                    raw_dir = session_dir / "raw"
                    raw_dir.mkdir(parents=True, exist_ok=True)

                    raw_path = raw_dir / uploaded_file.name
                    with open(raw_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Initialize Service
                    service = IngestionService(BASE_SESSIONS_DIR)

                    # Callback for progress bar
                    progress_bar = st.progress(0.0)
                    status_display = st.empty()
                    all_logs = []

                    def ui_callback(msg, perc):
                        all_logs.append(msg)
                        # Show only the last 3 updates to keep it clean
                        recent_logs = "\n".join([f"🔹 {l}" for l in all_logs[-3:]])
                        status_display.markdown(recent_logs)
                        progress_bar.progress(perc)

                    st.write("Cargando base de datos SQL...")
                    service.prepare_corpus(
                        corpus_name=new_corpus_name,
                        xlsx_file=raw_path,
                        progress_callback=ui_callback
                    )

                    with st.expander("Ver registro completo de ingesta"):
                        for log in all_logs:
                            st.write(f"🔹 {log}")


                    status.update(label="✅ Corpus Listo!", state="complete", expanded=False)

                st.session_state.current_session = new_corpus_name
                st.session_state.app_state = "CHAT"
                st.success(f"Sesión '{new_corpus_name}' creada exitosamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error durante la ingesta: {e}")

# ── Main Chat Interface ──────────────────────────────────────────────────────
if st.session_state.app_state == "SETUP":
    st.title("📚 Bienvenido al Asistente Bibliométrico")
    st.info("Para comenzar, por favor sube un corpus en la barra lateral izquierda y asígnale un nombre.")

    # Centrar imagen usando columnas
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://img.icons8.com/clouds/500/database.png", width=300)
else:
    st.title(f"📚 Chat: {st.session_state.current_session}")
    st.markdown("""
        Haz preguntas en lenguaje natural sobre tu corpus bibliométrico.
        El sistema decidirá si usar **SQL** (para estadísticas), **RAG** (para conceptos) o un enfoque **Híbrido**.
    """)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sql" in message:
                st.markdown(f'<div class="sql-block"><b>SQL:</b> {message["sql"]}</div>', unsafe_allow_html=True)
            if "rag" in message:
                with st.expander("📚 Fuentes RAG"):
                    st.markdown(message["rag"])

    # Chat input
    if prompt := st.chat_input("Ej: ¿Quién es el autor más citado?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                # Prepare history
                proper_history = []
                for i in range(0, len(st.session_state.messages)-1, 2):
                    if i+1 < len(st.session_state.messages):
                        proper_history.append({
                            "question": st.session_state.messages[i]["content"],
                            "answer": st.session_state.messages[i+1]["content"]
                        })

                try:
                    # Get paths for current session
                    paths = get_session_paths(st.session_state.current_session)

                    # Run the agent
                    result = run_agent(
                        query=prompt,
                        history=proper_history,
                        db_path=str(paths["db"]),
                        chroma_dir=str(paths["chroma"])
                    )

                    answer = result.get("answer", "No pude generar una respuesta.")
                    sql = result.get("sql_visible", "")
                    rag_results = result.get("rag_results", [])

                    st.markdown(answer)
                    if sql:
                        st.markdown(f'<div class="sql-block"><b>SQL:</b> {sql}</div>', unsafe_allow_html=True)
                    if rag_results:
                        with st.expander("📚 Fuentes RAG"):
                            for res in rag_results:
                                st.markdown(f"- {res}")

                    msg_data = {"role": "assistant", "content": answer}
                    if sql: msg_data["sql"] = sql
                    if rag_results: msg_data["rag"] = "\n".join([f"- {r}" for r in rag_results])
                    st.session_state.messages.append(msg_data)

                except Exception as e:
                    st.error(f"Error al ejecutar el agente: {e}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
