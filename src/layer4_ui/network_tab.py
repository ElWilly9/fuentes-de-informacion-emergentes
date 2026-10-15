"""
network_tab.py — Vista "Red del corpus" de la app Streamlit
===========================================================
Muestra las redes de la Capa 5 (frentes, temas, coautoría) en un grafo interactivo 2D/3D y,
debajo, la tabla de grupos con la misma clasificación (emergente / señal débil) que usa el chat.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.layer4_ui.network_view import network_html
from src.layer5_network.communities import analyze
from src.layer5_network.context import _tag, _trend_line
from src.layer5_network.export import KINDS, graph_data


@st.cache_data(show_spinner="Calculando la red…")
def _cached_graph(db_path: str, mtime: float, kind: str, min_weight: int, hide_isolated: bool) -> dict:
    return graph_data(db_path, kind, min_weight=min_weight, hide_isolated=hide_isolated)


def _groups_table(db_path: str, kind: str) -> pd.DataFrame | None:
    r = analyze(db_path)
    corpus = r["total_trend"]
    clase = lambda t: _tag(t, corpus).replace(" — Clasificación: ", "")
    if kind == "frentes":
        return pd.DataFrame([{"Frente": f["id"], "Artículos": f["size"], "Citas": f["citations"],
                              "Palabras clave": ", ".join(f["keywords"][:5]).lower(),
                              "Crecimiento anual": f["trend"]["growth_rate"],
                              "Año medio": f["trend"]["mean_year"], "Clasificación": clase(f["trend"])}
                             for f in r["fronts"]])
    if kind == "temas":
        return pd.DataFrame([{"Tema": t["id"], "Artículos": t["n_articles"],
                              "Palabras clave": ", ".join(t["keywords"][:6]).lower(),
                              "Crecimiento anual": t["trend"]["growth_rate"],
                              "Año medio": t["trend"]["mean_year"], "Clasificación": clase(t["trend"])}
                             for t in r["themes"]])
    rows = r["bridge_authors"] or []
    if not rows:
        return None
    return pd.DataFrame([{"Autor puente": a["name"], "Artículos": a["articles"],
                          "Frentes": ", ".join(map(str, a["fronts"])), "Coautores": a["coauthors"],
                          "Países": ", ".join(a["countries"])} for a in rows])


def render_network_view(db_path: Path) -> None:
    st.title("🕸️ Red del corpus")
    if not db_path.exists():
        st.warning("Esta sesión todavía no tiene base de datos.")
        return

    c1, c2, c3, c4 = st.columns([3, 1.2, 1.5, 1.3], vertical_alignment="bottom")
    kind = c1.selectbox("Red", list(KINDS), format_func=KINDS.get, key="net_kind")
    mode = c2.segmented_control("Vista", ["2D", "3D"], default="2D", required=True, key="net_mode")
    min_weight = c3.number_input("Peso mínimo del enlace", min_value=1, max_value=50, value=1, step=1,
                                 key="net_minw",
                                 help="Frentes: referencias compartidas · Temas: artículos en común · "
                                      "Coautoría: artículos firmados juntos")
    hide_isolated = c4.toggle("Ocultar aislados", value=True, key="net_hide")

    data = _cached_graph(str(db_path), db_path.stat().st_mtime, kind, int(min_weight), hide_isolated)
    st.caption(f"{data['summary']} Se muestran {len(data['nodes'])} nodos y {len(data['links'])} enlaces.")
    if not data["nodes"]:
        st.info("Con ese peso mínimo no queda ningún enlace. Baja el peso mínimo.")
        return
    st.iframe(network_html(data, mode_3d=(mode == "3D"), height=640), height=650)

    table = _groups_table(str(db_path), kind)
    if table is not None and not table.empty:
        st.subheader("Grupos" if kind != "coautoria" else "Autores puente")
        cfg = {"Crecimiento anual": st.column_config.NumberColumn(format="percent")}
        st.dataframe(table, hide_index=True, column_config=cfg)
    elif kind == "coautoria":
        st.info("Ningún autor publica en dos o más frentes de este corpus, así que no hay autores puente.")
    with st.expander("Cómo leer esta red"):
        st.markdown(
            "- **Frentes de investigación**: cada nodo es un artículo principal; dos artículos se unen si citan "
            "referencias en común (acoplamiento bibliográfico). Los colores son comunidades Louvain.\n"
            "- **Temas**: cada nodo es una palabra clave de autor que aparece en al menos 2 artículos; se unen si "
            "aparecen en el mismo artículo.\n"
            "- **Coautoría**: cada nodo es un autor; se unen si firmaron un artículo juntos. En dorado, los autores "
            "puente (publican en dos o más frentes).\n"
            "- **Emergente**: crece más rápido que el corpus, con tendencia significativa (p < 0,05), y pesa más en los "
            "últimos 3 años que el corpus. **Señal débil**: lo mismo pero sin significancia estadística.")
