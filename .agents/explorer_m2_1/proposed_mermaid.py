"""
mermaid_generator.py (Upgraded for Vis-network rendering)
  - generate_mermaid()  → raw Mermaid string (kept for the code-preview panel)
  - generate_html()     → full Vis-network force-directed interactive graph
"""
from __future__ import annotations

import os
import json as _json
from laitoxx.shared.graph.model import Graph, Node, SHAPE_ID_TO_TOKENS
from laitoxx.interfaces.gui.translator import translator as _translator

_SAFE_LABEL_CHARS = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789 _-."
)

def _safe_label(text: str) -> str:
    text = text.replace('"', "'")
    needs_quote = any(c not in _SAFE_LABEL_CHARS for c in text)
    return f'"{text}"' if (needs_quote or not text) else text

def _node_line(node: Node) -> str:
    open_tok, close_tok = SHAPE_ID_TO_TOKENS.get(node.mermaid_shape, ("[", "]"))
    return f"    {node.id}{open_tok}{_safe_label(node.label)}{close_tok}"

def generate_mermaid(graph: Graph) -> str:
    lines: list[str] = [f"graph {graph.direction}"]
    for node in graph.nodes:
        lines.append(_node_line(node))
    for node in graph.nodes:
        if node.mermaid_style:
            lines.append(f"    style {node.id} {node.mermaid_style}")
    link_idx = 0
    link_styles: list[str] = []
    for edge in graph.edges:
        line_type = edge.mermaid_line or "-->"
        conn = f"{line_type}|{edge.label.replace('|','/')}|" if edge.label else line_type
        lines.append(f"    {edge.source_id} {conn} {edge.target_id}")
        if edge.mermaid_style:
            link_styles.append(f"    linkStyle {link_idx} {edge.mermaid_style}")
        link_idx += 1
    lines.extend(link_styles)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Vis-network style mapping
# ---------------------------------------------------------------------------

_TYPE_COLORS: dict[str, str] = {
    "Person":   "#f472b6",   # pink
    "Email":    "#60a5fa",   # blue
    "Phone":    "#34d399",   # emerald
    "Website":  "#a78bfa",   # violet
    "Company":  "#fbbf24",   # amber
    "IP":       "#f87171",   # red
    "Address":  "#fb923c",   # orange
    "Document": "#e2e8f0",   # slate
    "Custom":   "#94a3b8",   # grey
}

_TYPE_SYMBOLS: dict[str, str] = {
    "Person":   "👤",
    "Email":    "✉",
    "Phone":    "📞",
    "Website":  "🌐",
    "Company":  "🏢",
    "IP":       "🖧",
    "Address":  "📍",
    "Document": "📄",
    "Custom":   "●",
}

_EDGE_DASH: dict[str, str] = {
    "-->":   "none",
    "==>":   "none",
    "-.->":  "6,3",
    "---":   "none",
    "-...-": "2,4",
    "<-->":  "none",
}

def _parse_style_color(style_str: str, key: str, fallback: str) -> str:
    """Extract e.g. fill:#FFD700 from a CSS-ish style string."""
    for part in style_str.split(","):
        part = part.strip()
        if part.startswith(f"{key}:"):
            return part[len(key) + 1:].strip()
    return fallback

def _get_vis_js() -> str:
    """Read local vis-network.min.js and return its contents, falling back to a mock bridge if missing."""
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    path = os.path.join(base_path, "resources", "js", "vis-network.min.js")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
            
    # Mock fallback if script is missing
    return """
window.vis = {
  Network: function(container, data, options) {
    container.innerHTML = `
      <div style="
        color: #f87171;
        padding: 40px 20px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        text-align: center;
        background: #0d0d1a;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      ">
        <h3 style="margin-bottom: 10px; color: #f472b6; font-size: 18px;">Vis-Network Library Missing</h3>
        <p style="color: #a99fc0; max-width: 400px; font-size: 13px; line-height: 1.6;">
          Could not load <code>resources/js/vis-network.min.js</code>. The interactive network rendering is currently unavailable.
        </p>
        <p style="color: #6b6580; font-size: 12px; margin-top: 15px;">
          Please run the download script or place the <code>vis-network.min.js</code> file manually in <code>resources/js/</code>.
        </p>
      </div>
    `;
    return {
      on: function() {},
      off: function() {},
      setData: function() {},
      destroy: function() {},
      focus: function() {},
      fit: function() {},
      zoomOut: function() {},
      zoomIn: function() {}
    };
  }
};
"""


# ---------------------------------------------------------------------------
# HTML generator using Vis-network
# ---------------------------------------------------------------------------

def generate_html(graph: Graph, lang: str = None, theme: dict = None) -> str:
    """
    Returns a self-contained HTML page with a Vis-network force-directed graph.
    Features:
      - Vis-network interactive nodes and edges
      - Node/Edge selection communicating back to Python GUI
      - Context Menu triggers on right click
      - Glassmorphism tooltip and stats layout
      - Custom SVG node shapes preserving glassmorphism theme and degree sizing
    """
    if lang:
        _translator.set_language(lang)
    def _t(key):
        return _translator.get(key)

    # Extract theme colors
    _td = theme or {}
    _h_accent   = _td.get("accent_color",          "#c084fc")
    _h_accent2  = _td.get("text_secondary_color",  "#a78bfa")
    _h_bg       = _td.get("window_bg_color",        _td.get("text_area_bg_color", "#0d0b1a"))
    _h_bdr      = _td.get("border_color",           _td.get("button_border_color", "rgba(192,132,252,0.35)"))
    _h_txt_pri  = _td.get("text_area_text_color",   "#f1f0ff")
    _h_txt_sec  = _td.get("text_secondary_color",   "#94a3b8")
    _h_body_bg  = f"background: {_h_bg};"

    # Build JSON data
    nodes_data = []
    for n in graph.nodes:
        fill = _parse_style_color(n.mermaid_style, "fill",
                                  _TYPE_COLORS.get(n.node_type, "#94a3b8"))
        nodes_data.append({
            "id":    n.id,
            "label": n.label,
            "type":  n.node_type,
            "desc":  n.description,
            "fill":  fill,
            "icon":  _TYPE_SYMBOLS.get(n.node_type, "●"),
            "meta":  n.metadata,
            "shape": n.mermaid_shape or "rect",
        })

    edges_data = []
    for e in graph.edges:
        stroke = _parse_style_color(e.mermaid_style, "stroke", _h_accent)
        dash   = _EDGE_DASH.get(e.mermaid_line, "none")
        edges_data.append({
            "id":     e.id,
            "source": e.source_id,
            "target": e.target_id,
            "label":  e.label,
            "type":   e.edge_type,
            "stroke": stroke,
            "dash":   dash,
            "arrow":  "-->" not in (e.mermaid_line or "") or True,
        })

    graph_json = _json.dumps({"nodes": nodes_data, "edges": edges_data},
                              ensure_ascii=False)
                              
    vis_network_js = _get_vis_js()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  width: 100vw; height: 100vh; overflow: hidden;
  {_h_body_bg}
  font-family: 'Segoe UI', system-ui, sans-serif;
}}

#network-container {{
  width: 100%; height: 100%;
}}

/* Tooltip */
#tooltip {{
  position: fixed;
  pointer-events: none;
  background: {_h_bg};
  border: 1px solid {_h_accent};
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 12px;
  color: {_h_txt_pri};
  backdrop-filter: blur(8px);
  max-width: 260px;
  line-height: 1.6;
  opacity: 0;
  transition: opacity 0.18s;
  z-index: 100;
}}
#tooltip.visible {{ opacity: 1; }}
#tooltip strong {{ color: {_h_accent}; font-size: 13px; }}
#tooltip .tt-type {{ color: {_h_accent2}; font-size: 10px; letter-spacing: 1px; text-transform: uppercase; }}
#tooltip .tt-sep {{ border: none; border-top: 1px solid {_h_bdr}; margin: 6px 0; }}
#tooltip .tt-row {{ color: {_h_txt_sec}; font-size: 11px; }}
#tooltip .tt-row span {{ color: {_h_txt_pri}; }}

/* Info panel */
#info-panel {{
  position: fixed;
  bottom: 16px; left: 50%;
  transform: translateX(-50%);
  background: {_h_bg};
  border: 1px solid {_h_bdr};
  border-radius: 12px;
  padding: 10px 20px;
  font-size: 11px;
  color: {_h_txt_sec};
  backdrop-filter: blur(12px);
  pointer-events: none;
  letter-spacing: 0.4px;
  transition: opacity 0.3s;
  z-index: 90;
}}
#info-panel kbd {{
  background: {_h_bdr};
  border: 1px solid {_h_accent};
  border-radius: 4px;
  padding: 1px 5px;
  color: {_h_accent};
  font-family: inherit;
  font-size: 11px;
}}

/* Stats badge */
#stats {{
  position: fixed;
  top: 12px; right: 14px;
  background: {_h_bg};
  border: 1px solid {_h_bdr};
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 11px;
  color: {_h_accent2};
  pointer-events: none;
  z-index: 90;
}}
</style>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
{vis_network_js}
</script>
</head>
<body>

<div id="network-container"></div>

<div id="tooltip"></div>
<div id="info-panel">
  <kbd>{_t('ge_d3_zoom')}</kbd> {_t('ge_d3_zoom_hint')} &nbsp;·&nbsp; <kbd>{_t('ge_d3_drag')}</kbd> {_t('ge_d3_drag_hint')} &nbsp;·&nbsp; <kbd>{_t('ge_d3_hover')}</kbd> {_t('ge_d3_hover_hint')}
</div>
<div id="stats"></div>

<script>
const DATA = {graph_json};
const THEME = {{
  bg: "{_h_bg}",
  border_color: "{_h_bdr}",
  accent: "{_h_accent}",
  accent2: "{_h_accent2}",
  text_primary: "{_h_txt_pri}",
  text_secondary: "{_h_txt_sec}"
}};

let BRIDGE = null;
if (window.qt && window.qt.webChannelTransport) {{
  new QWebChannel(qt.webChannelTransport, function(channel) {{
    BRIDGE = channel.objects.bridge || null;
  }});
}}

// Connections degree calculation
const degMap = {{}};
DATA.nodes.forEach(n => degMap[n.id] = 0);
DATA.edges.forEach(e => {{
  degMap[e.source] = (degMap[e.source] || 0) + 1;
  degMap[e.target] = (degMap[e.target] || 0) + 1;
}});

// Custom SVG generation for glassmorphism and icons
function makeNodeSvg(node, degree, theme) {{
  const fill = node.fill;
  const border = theme.border_color;
  const icon = node.icon;
  const shape = node.shape;
  
  let shapeMarkup = '';
  const w = 60, h = 60;
  
  if (shape === 'circle' || shape === 'round') {{
    shapeMarkup = `<circle cx="30" cy="30" r="26" fill="${{fill}}" fill-opacity="0.88" stroke="${{border}}" stroke-width="2" />`;
  }} else if (shape === 'diamond') {{
    shapeMarkup = `<polygon points="30,4 56,30 30,56 4,30" fill="${{fill}}" fill-opacity="0.88" stroke="${{border}}" stroke-width="2" />`;
  }} else if (shape === 'hexagon') {{
    shapeMarkup = `<polygon points="30,4 54,17 54,43 30,56 6,43 6,17" fill="${{fill}}" fill-opacity="0.88" stroke="${{border}}" stroke-width="2" />`;
  }} else if (shape === 'flag') {{
    shapeMarkup = `<polygon points="30,4 56,52 4,52" fill="${{fill}}" fill-opacity="0.88" stroke="${{border}}" stroke-width="2" />`;
  }} else {{
    shapeMarkup = `<rect x="6" y="6" width="48" height="48" rx="6" ry="6" fill="${{fill}}" fill-opacity="0.88" stroke="${{border}}" stroke-width="2" />`;
  }}
  
  const svg = `
  <svg xmlns="http://www.w3.org/2000/svg" width="${{w}}" height="${{h}}">
    <defs>
      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="2" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>
    <g filter="url(#glow)">
      \${shapeMarkup}
    </g>
    <text x="30" y="36" font-size="22" font-family="'Segoe UI', sans-serif" text-anchor="middle" dominant-baseline="middle">\${icon}</text>
  </svg>
  `;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}}

// Map data
const visNodes = DATA.nodes.map(n => {{
  const deg = degMap[n.id] || 0;
  const size = 20 + Math.min(deg, 8) * 3;
  return {{
    id: n.id,
    label: n.label.length > 18 ? n.label.slice(0, 16) + '…' : n.label,
    shape: 'image',
    image: makeNodeSvg(n, deg, THEME),
    size: size,
    title: n.label
  }};
}});

const visEdges = DATA.edges.map(e => {{
  return {{
    id: e.id,
    from: e.source,
    to: e.target,
    label: e.label || '',
    color: {{
      color: e.stroke || THEME.accent,
      highlight: e.stroke || THEME.accent,
      hover: e.stroke || THEME.accent
    }},
    arrows: {{
      to: {{ enabled: e.arrow, scaleFactor: 0.8 }}
    }},
    dashes: e.dash !== 'none',
    width: 2,
    font: {{
      color: THEME.accent2,
      size: 10,
      face: 'Segoe UI, system-ui, sans-serif',
      strokeWidth: 3,
      strokeColor: THEME.bg
    }}
  }};
}});

// Container
const container = document.getElementById('network-container');
const data = {{
  nodes: new vis.DataSet(visNodes),
  edges: new vis.DataSet(visEdges)
}};

// Vis-network Options
const options = {{
  nodes: {{
    font: {{
      color: THEME.text_primary,
      size: 11,
      face: 'Segoe UI, system-ui, sans-serif',
      strokeWidth: 3,
      strokeColor: THEME.bg
    }}
  }},
  edges: {{
    smooth: {{
      enabled: true,
      type: 'cubicBezier',
      roundness: 0.3
    }}
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 200,
    selectConnectedEdges: false
  }},
  physics: {{
    enabled: true,
    barnesHut: {{
      gravitationalConstant: -2000,
      centralGravity: 0.3,
      springLength: 120,
      springConstant: 0.04,
      damping: 0.09,
      avoidOverlap: 1
    }},
    stabilization: {{
      enabled: true,
      iterations: 150,
      updateInterval: 25
    }}
  }}
}};

// Initialize Network
const network = new vis.Network(container, data, options);

// Stats Badge
document.getElementById('stats').innerText = 
  `\${DATA.nodes.length} ${_t('ge_d3_nodes_count')} · \${DATA.edges.length} ${_t('ge_d3_edges_count')}`;

// --- WebChannel Event Bridge Integration ---

// Click / Selection
network.on("click", function(params) {{
  if (params.nodes.length > 0) {{
    const nodeId = params.nodes[0];
    if (BRIDGE) {{
      BRIDGE.onNodeSelected(nodeId);
    }}
  }} else if (params.edges.length > 0) {{
    const edgeId = params.edges[0];
    if (BRIDGE) {{
      BRIDGE.onEdgeSelected(edgeId);
    }}
  }}
}});

// Context Menu (Right Click)
container.addEventListener("contextmenu", function(e) {{
  e.preventDefault();
  const pointer = network.getEventPosition(e);
  const nodeId = network.getNodeAt(pointer);
  const edgeId = network.getEdgeAt(pointer);
  
  let itemType = 'background';
  let itemId = '';
  
  if (nodeId !== undefined) {{
    itemType = 'node';
    itemId = nodeId;
  }} else if (edgeId !== undefined) {{
    itemType = 'edge';
    itemId = edgeId;
  }}
  
  if (BRIDGE) {{
    BRIDGE.onContextMenu(itemType, itemId, Math.round(e.clientX), Math.round(e.clientY));
  }}
}});

// Hover / Tooltip
const tooltip = document.getElementById('tooltip');

network.on("hoverNode", function (params) {{
  const nodeId = params.node;
  const node = DATA.nodes.find(n => n.id === nodeId);
  if (!node) return;
  
  let html = `<strong>\${node.label}</strong><br>
    <span class="tt-type">\${node.type}</span>`;
  if (node.desc) html += `<hr class="tt-sep"><div class="tt-row">\${node.desc}</div>`;
  const metaEntries = Object.entries(node.meta || {{}});
  if (metaEntries.length) {{
    html += `<hr class="tt-sep">`;
    metaEntries.forEach(([k,v]) => {{
      html += `<div class="tt-row">\${k}: <span>\${v}</span></div>`;
    }});
  }}
  html += `<hr class="tt-sep"><div class="tt-row">${_t('ge_d3_connections')}: <span>\${degMap[node.id] || 0}</span></div>`;
  tooltip.innerHTML = html;
  tooltip.classList.add('visible');
}});

network.on("blurNode", function (params) {{
  tooltip.classList.remove('visible');
}});

// Edge Hover
network.on("hoverEdge", function (params) {{
  const edgeId = params.edge;
  const edge = DATA.edges.find(e => e.id === edgeId);
  if (!edge || !edge.label) return;
  
  let html = `<strong>\${edge.label}</strong><br>
    <span class="tt-type">\${edge.type || 'Connection'}</span>`;
  tooltip.innerHTML = html;
  tooltip.classList.add('visible');
}});

network.on("blurEdge", function (params) {{
  tooltip.classList.remove('visible');
}});

// Track mouse for tooltip positioning
container.addEventListener("mousemove", function(event) {{
  if (tooltip.classList.contains('visible')) {{
    const x = event.clientX, y = event.clientY;
    const tw = tooltip.offsetWidth, th = tooltip.offsetHeight;
    const px = x + 14 + tw > window.innerWidth ? x - tw - 14 : x + 14;
    const py = y + 10 + th > window.innerHeight ? y - th - 10 : y + 10;
    tooltip.style.left = px + 'px';
    tooltip.style.top  = py + 'px';
  }}
}});
</script>
</body>
</html>
"""
