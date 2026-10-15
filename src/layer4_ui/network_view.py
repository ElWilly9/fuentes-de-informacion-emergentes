"""
network_view.py — Visor interactivo de las redes de la Capa 5
=============================================================
Genera una página HTML autocontenida con force-graph (2D) o 3d-force-graph (3D), que se
muestra en Streamlit con st.iframe. Interacción: arrastrar nodos, zoom con la rueda, rotar
(3D), pasar el cursor para ver el detalle y resaltar vecinos, clic para centrar y fijar el
panel de información, y buscador por nombre.

Los textos de los nodos se escapan en Python (export.py) antes de llegar aquí.
"""

import json

FORCE_GRAPH_2D = "https://cdn.jsdelivr.net/npm/force-graph@1.43.5/dist/force-graph.min.js"
FORCE_GRAPH_3D = "https://cdn.jsdelivr.net/npm/3d-force-graph@1.73.3/dist/3d-force-graph.min.js"

_TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  :root { --bg: __BG__; --panel: __PANEL__; --text: __TEXT__; --muted: __MUTED__; --border: __BORDER__; }
  html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
               font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; overflow: hidden; }
  #wrap { position: relative; width: 100%; height: __HEIGHT__px; }
  #graph { position: absolute; inset: 0; }
  .panel { position: absolute; background: var(--panel); border: 1px solid var(--border);
           border-radius: 10px; padding: 10px 12px; font-size: 12px; line-height: 1.45;
           box-shadow: 0 4px 16px rgba(0,0,0,.12); }
  #legend { top: 12px; left: 12px; max-width: 280px; max-height: 45%; overflow: auto; }
  #legend .row { display: flex; align-items: center; gap: 8px; margin: 3px 0; cursor: pointer; }
  #legend .row.off { opacity: .35; }
  #legend .dot { width: 11px; height: 11px; border-radius: 50%; flex: none; }
  #legend .title { font-weight: 600; margin-bottom: 4px; }
  #info { right: 12px; top: 12px; width: 280px; max-height: 70%; overflow: auto; display: none; }
  #info .close { float: right; cursor: pointer; color: var(--muted); font-size: 14px; }
  #info .neigh { margin-top: 6px; color: var(--muted); max-height: 160px; overflow: auto; }
  #search { position: absolute; left: 12px; bottom: 12px; width: 260px; padding: 7px 10px;
            border-radius: 8px; border: 1px solid var(--border); background: var(--panel);
            color: var(--text); font-size: 13px; }
  #hint { position: absolute; right: 12px; bottom: 12px; color: var(--muted); font-size: 11px; }
  /* tooltip de force-graph / 3d-force-graph (el nombre de la clase cambia entre versiones) */
  .scene-tooltip, .float-tooltip-kap, .graph-tooltip {
    background: var(--panel) !important; color: var(--text) !important; border: 1px solid var(--border);
    border-radius: 8px; padding: 6px 9px !important; font: 12px/1.4 system-ui, sans-serif !important;
    max-width: 320px; white-space: normal !important; box-shadow: 0 4px 14px rgba(0,0,0,.18); }
</style></head>
<body><div id="wrap">
  <div id="graph"></div>
  <div id="legend" class="panel"><div class="title">Grupos (clic para ocultar)</div></div>
  <div id="info" class="panel"><span class="close" id="close">✕</span><div id="infobody"></div></div>
  <input id="search" placeholder="Buscar nodo y pulsar Enter…">
  <div id="hint">__HINT__</div>
</div>
<script src="__LIB__"></script>
<script>
const DATA = __DATA__;
const IS3D = __IS3D__;
const DIM = "__DIM__";
const elem = document.getElementById("graph");

// Vecinos de cada nodo (para resaltar)
const byId = new Map(DATA.nodes.map(n => [n.id, n]));
DATA.nodes.forEach(n => { n.neighbors = new Set(); n.links = []; });
DATA.links.forEach(l => {
  const a = byId.get(l.source), b = byId.get(l.target);
  if (!a || !b) return;
  a.neighbors.add(b); b.neighbors.add(a); a.links.push(l); b.links.push(l);
});
const maxW = Math.max(1, ...DATA.links.map(l => l.weight));
let hoverNode = null, selected = null;
const hiddenGroups = new Set();
const hlNodes = new Set(), hlLinks = new Set();

function setHighlight(node) {
  hlNodes.clear(); hlLinks.clear();
  if (node) { hlNodes.add(node); node.neighbors.forEach(n => hlNodes.add(n)); node.links.forEach(l => hlLinks.add(l)); }
}
const visible = n => !hiddenGroups.has(n.group);
const nodeColor = n => (hlNodes.size && !hlNodes.has(n)) ? DIM : n.color;
const linkColor = l => hlLinks.has(l) ? "__LINKHL__" : "__LINK__";
const linkWidth = l => (hlLinks.has(l) ? 2.5 : 0.4) + 2.5 * l.weight / maxW;

const G = (IS3D ? ForceGraph3D() : ForceGraph())(elem)
  .width(elem.clientWidth).height(elem.clientHeight)
  .backgroundColor("__BG__")
  .graphData({ nodes: DATA.nodes, links: DATA.links })
  .nodeId("id").nodeVal("val").nodeLabel("label")
  .nodeColor(nodeColor).nodeVisibility(visible)
  .linkVisibility(l => visible(typeof l.source === "object" ? l.source : byId.get(l.source)) &&
                       visible(typeof l.target === "object" ? l.target : byId.get(l.target)))
  .linkColor(linkColor).linkWidth(linkWidth)
  .onNodeHover(node => {
    hoverNode = node || null;
    elem.style.cursor = node ? "pointer" : null;
    setHighlight(hoverNode || selected);
    refresh();
  })
  .onNodeClick(node => { selected = node; setHighlight(node); showInfo(node); focus(node); refresh(); })
  .onBackgroundClick(() => { selected = null; setHighlight(null); hideInfo(); refresh(); });

// Repulsión acotada: con muchos grupos desconectados (coautoría) se alejaban fuera de la vista
G.d3Force("charge").strength(-25).distanceMax(150);
G.cooldownTime(6000);

if (IS3D) {
  G.nodeOpacity(0.95).linkOpacity(0.35).nodeResolution(12);
} else {
  G.autoPauseRedraw(false)
   .nodeCanvasObjectMode(() => "after")
   .nodeCanvasObject((n, ctx, scale) => {
     const r = Math.sqrt(Math.max(0, n.val || 1)) * 4;   // mismo radio que dibuja force-graph (relSize 4)
     if (n.bridge) { ctx.beginPath(); ctx.arc(n.x, n.y, r + 1.5, 0, 2 * Math.PI);
                     ctx.lineWidth = 2 / scale * 1.5; ctx.strokeStyle = "__RING__"; ctx.stroke(); }
     if (scale > 2.2 || hlNodes.has(n) || n === selected) {
       const fs = 11 / scale;
       ctx.font = `${fs}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "top";
       ctx.fillStyle = "__TEXT__"; ctx.fillText(n.name, n.x, n.y + r + 2 / scale);
     }
   });
}

function refresh() {
  if (IS3D) { G.nodeColor(G.nodeColor()); G.linkColor(G.linkColor()); G.linkWidth(G.linkWidth()); }
}
function focus(node) {
  if (!node) return;
  if (IS3D) {
    const d = 90, k = 1 + d / Math.hypot(node.x, node.y, node.z || 1);
    G.cameraPosition({ x: node.x * k, y: node.y * k, z: node.z * k }, node, 1200);
  } else { G.centerAt(node.x, node.y, 800); G.zoom(4, 800); }
}
function showInfo(node) {
  const names = [...node.neighbors].map(n => n.name).sort().slice(0, 25);
  document.getElementById("infobody").innerHTML = node.label +
    `<div class="neigh"><b>${node.neighbors.size} conexiones</b>` +
    (names.length ? "<br>" + names.map(x => "· " + x.replace(/[<>&]/g, "")).join("<br>") : "") + "</div>";
  document.getElementById("info").style.display = "block";
}
function hideInfo() { document.getElementById("info").style.display = "none"; }
document.getElementById("close").onclick = () => { selected = null; setHighlight(null); hideInfo(); refresh(); };

// Leyenda: clic para ocultar / mostrar un grupo
const legend = document.getElementById("legend");
DATA.legend.forEach((g, i) => {
  const row = document.createElement("div"); row.className = "row";
  const dot = document.createElement("span"); dot.className = "dot"; dot.style.background = g.color;
  const txt = document.createElement("span"); txt.textContent = g.label;
  row.append(dot, txt);
  const group = g.group;
  if (group !== undefined && group !== null) {
    row.onclick = () => {
      hiddenGroups.has(group) ? hiddenGroups.delete(group) : hiddenGroups.add(group);
      row.classList.toggle("off");
      G.nodeVisibility(G.nodeVisibility()); G.linkVisibility(G.linkVisibility());
    };
  } else { row.style.cursor = "default"; }
  legend.appendChild(row);
});

// Buscador
document.getElementById("search").addEventListener("keydown", e => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim().toLowerCase();
  if (!q) return;
  const node = DATA.nodes.find(n => n.name.toLowerCase().includes(q) || String(n.id).toLowerCase().includes(q));
  if (node) { selected = node; setHighlight(node); showInfo(node); focus(node); refresh(); }
});

// Encuadrar al terminar la simulación (solo la primera vez)
let fitted = false;
G.onEngineStop(() => { if (!fitted) { G.zoomToFit(600, 40); fitted = true; } });
window.addEventListener("resize", () => G.width(elem.clientWidth).height(elem.clientHeight));
</script></body></html>
"""

_THEMES = {
    False: {"BG": "#fbfbfd", "PANEL": "rgba(255,255,255,.94)", "TEXT": "#1f2937", "MUTED": "#6b7280",
            "BORDER": "#e5e7eb", "DIM": "#e5e7eb", "LINK": "rgba(100,116,139,.25)",
            "LINKHL": "rgba(30,41,59,.85)", "RING": "#111827"},
    True: {"BG": "#0b1220", "PANEL": "rgba(17,24,39,.92)", "TEXT": "#e5e7eb", "MUTED": "#9ca3af",
           "BORDER": "#334155", "DIM": "#334155", "LINK": "rgba(148,163,184,.35)",
           "LINKHL": "rgba(255,255,255,.9)", "RING": "#ffffff"},
}


def network_html(data: dict, mode_3d: bool = False, height: int = 640) -> str:
    """Página HTML con el grafo interactivo. `data` viene de layer5_network.export.graph_data."""
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    theme = _THEMES[mode_3d]
    hint = ("Arrastra para rotar · rueda para zoom · clic derecho para desplazar · clic en un nodo para fijarlo"
            if mode_3d else "Arrastra nodos o el fondo · rueda para zoom · clic en un nodo para fijarlo")
    out = _TEMPLATE
    for key, value in {**theme, "HEIGHT": str(height), "LIB": FORCE_GRAPH_3D if mode_3d else FORCE_GRAPH_2D,
                       "IS3D": "true" if mode_3d else "false", "HINT": hint}.items():
        out = out.replace(f"__{key}__", value)
    return out.replace("__DATA__", payload)
