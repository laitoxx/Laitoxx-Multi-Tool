"""
mermaid_generator.py
  - generate_mermaid()  → raw Mermaid string (kept for the code-preview panel)
  - generate_html()     → full vis-network interactive graph
"""

from __future__ import annotations

import json as _json

from laitoxx.interfaces.gui.translator import translator as _translator
from laitoxx.shared.graph.model import SHAPE_ID_TO_D3, SHAPE_ID_TO_TOKENS, Edge, Graph, Node

_SAFE_LABEL_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-."
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
        conn = (
            f"{line_type}|{edge.label.replace('|', '/')}|" if edge.label else line_type
        )
        lines.append(f"    {edge.source_id} {conn} {edge.target_id}")
        if edge.mermaid_style:
            link_styles.append(f"    linkStyle {link_idx} {edge.mermaid_style}")
        link_idx += 1
    lines.extend(link_styles)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# colour palette per node type
# ---------------------------------------------------------------------------

_TYPE_COLORS: dict[str, str] = {
    "Person": "#f472b6",  # pink
    "Email": "#60a5fa",  # blue
    "Phone": "#34d399",  # emerald
    "Website": "#a78bfa",  # violet
    "Company": "#fbbf24",  # amber
    "IP": "#f87171",  # red
    "Address": "#fb923c",  # orange
    "Document": "#e2e8f0",  # slate
    "Custom": "#94a3b8",  # grey
}

_TYPE_SYMBOLS: dict[str, str] = {
    "Person": "👤",
    "Email": "✉",
    "Phone": "📞",
    "Website": "🌐",
    "Company": "🏢",
    "IP": "🖧",
    "Address": "📍",
    "Document": "📄",
    "Custom": "●",
}

_EDGE_DASH: dict[str, str] = {
    "-->": "none",
    "==>": "none",
    "-.->": "6,3",
    "---": "none",
    "-...-": "2,4",
    "<-->": "none",
}


def _parse_style_color(style_str: str, key: str, fallback: str) -> str:
    """Extract e.g. fill:#FFD700 from a CSS-ish style string."""
    for part in style_str.split(","):
        part = part.strip()
        if part.startswith(f"{key}:"):
            return part[len(key) + 1 :].strip()
    return fallback


# ---------------------------------------------------------------------------
# vis-network HTML generator
# ---------------------------------------------------------------------------


def generate_html(graph: Graph, lang: str = None, theme: dict = None) -> str:
    """
    Returns a self-contained HTML page with a vis-network interactive graph.
    Features:
      - Custom SVG shapes per node shape
      - Dynamic custom tooltips
      - Integrated event handlers for selections and context menus
      - Stats badge
    """
    import os

    # Load vis-network.min.js content
    current_dir = os.path.dirname(os.path.abspath(__file__))
    resources_dir = os.path.abspath(
        os.path.join(current_dir, "..", "..", "..", "..", "resources")
    )
    js_path = os.path.join(resources_dir, "js", "vis-network.min.js")
    try:
        with open(js_path, encoding="utf-8") as f:
            vis_js_content = f.read()
    except Exception:
        vis_js_content = "/* vis-network.min.js load failed */"

    # Use provided lang or current translator lang
    if lang:
        _translator.set_language(lang)

    def _t(key):
        return _translator.get(key)

    # Extract theme colors (fall back to defaults if no theme provided)
    _td = theme or {}
    _h_accent = _td.get("accent_color", "#c084fc")
    _h_accent2 = _td.get("text_secondary_color", "#a78bfa")
    _h_bg = _td.get("window_bg_color", _td.get("text_area_bg_color", "#0d0b1a"))
    _h_bdr = _td.get(
        "border_color", _td.get("button_border_color", "rgba(192,132,252,0.35)")
    )
    _h_txt_pri = _td.get("text_area_text_color", "#f1f0ff")
    _h_txt_sec = _td.get("text_secondary_color", "#94a3b8")
    _h_body_bg = f"background: {_h_bg};"

    # Build JSON data
    nodes_data = []
    for n in graph.nodes:
        fill = _parse_style_color(
            n.mermaid_style, "fill", _TYPE_COLORS.get(n.node_type, "#94a3b8")
        )
        nodes_data.append(
            {
                "id": n.id,
                "label": n.label,
                "type": n.node_type,
                "desc": n.description,
                "fill": fill,
                "icon": _TYPE_SYMBOLS.get(n.node_type, "●"),
                "meta": n.metadata,
                "shape": SHAPE_ID_TO_D3.get(n.mermaid_shape, "circle"),
                "valid_from": getattr(n, "valid_from", None) or "",
                "valid_to": getattr(n, "valid_to", None) or "",
            }
        )

    edges_data = []
    for e in graph.edges:
        stroke = _parse_style_color(e.mermaid_style, "stroke", _h_accent)
        dash = _EDGE_DASH.get(e.mermaid_line, "none")
        edges_data.append(
            {
                "id": e.id,
                "source": e.source_id,
                "target": e.target_id,
                "label": e.label,
                "type": e.edge_type,
                "stroke": stroke,
                "dash": dash,
                "arrow": "-->" not in (e.mermaid_line or "") or True,
                "valid_from": getattr(e, "valid_from", None) or "",
                "valid_to": getattr(e, "valid_to", None) or "",
            }
        )

    graph_json = _json.dumps(
        {"nodes": nodes_data, "edges": edges_data, "direction": graph.direction},
        ensure_ascii=False,
    )

    html = f"""<!DOCTYPE html>
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

#canvas {{
  width: 100%; height: 100%;
}}

/* Tooltip styling */
div.vis-tooltip {{
  position: absolute;
  background: {_h_bg} !important;
  border: 1px solid {_h_accent} !important;
  border-radius: 10px !important;
  padding: 10px 14px !important;
  font-family: 'Segoe UI', system-ui, sans-serif !important;
  font-size: 12px !important;
  color: {_h_txt_pri} !important;
  backdrop-filter: blur(8px) !important;
  max-width: 260px !important;
  line-height: 1.6 !important;
  z-index: 100 !important;
  box-shadow: 0 4px 15px rgba(0,0,0,0.5) !important;
}}
div.vis-tooltip hr {{
  border: none;
  border-top: 1px solid {_h_bdr};
  margin: 6px 0;
}}
div.vis-tooltip strong {{ color: {_h_accent}; font-size: 13px; }}
div.vis-tooltip .tt-type {{ color: {_h_accent2}; font-size: 10px; letter-spacing: 1px; text-transform: uppercase; }}
div.vis-tooltip .tt-sep {{ border: none; border-top: 1px solid {_h_bdr}; margin: 6px 0; }}
div.vis-tooltip .tt-row {{ color: {_h_txt_sec}; font-size: 11px; }}
div.vis-tooltip .tt-row span {{ color: {_h_txt_pri}; }}


</style>
</head>
<body>

<div id="canvas"></div>

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
/*VIS_JS_PLACEHOLDER*/
</script>
<script>
const DATA = {graph_json};

let BRIDGE = null;
if (window.qt && window.qt.webChannelTransport) {{
  new QWebChannel(qt.webChannelTransport, function(channel) {{
    BRIDGE = channel.objects.bridge || null;
  }});
}}



// Prepare datasets
const nodesDataset = new vis.DataSet();
const edgesDataset = new vis.DataSet();

// Build SVG helper
function makeSvgDataUrl(n) {{
  const fill = n.fill || '#94a3b8';
  const stroke = "{_h_accent}";
  const icon = n.icon || '●';
  const shape = n.shape || 'circle';

  let svg = '';
  if (shape === 'rect') {{
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">` +
          `<rect x="5" y="5" width="50" height="50" fill="${{fill}}" stroke="${{stroke}}" stroke-width="3" rx="0"/>` +
          `<text x="30" y="37" font-size="24" text-anchor="middle" fill="#0d0b1a">${{icon}}</text>` +
          `</svg>`;
  }} else if (shape === 'round') {{
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">` +
          `<rect x="5" y="5" width="50" height="50" fill="${{fill}}" stroke="${{stroke}}" stroke-width="3" rx="10" ry="10"/>` +
          `<text x="30" y="37" font-size="24" text-anchor="middle" fill="#0d0b1a">${{icon}}</text>` +
          `</svg>`;
  }} else if (shape === 'diamond') {{
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">` +
          `<polygon points="30,5 55,30 30,55 5,30" fill="${{fill}}" stroke="${{stroke}}" stroke-width="3"/>` +
          `<text x="30" y="38" font-size="22" text-anchor="middle" fill="#0d0b1a">${{icon}}</text>` +
          `</svg>`;
  }} else if (shape === 'hexagon') {{
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">` +
          `<polygon points="30,5 51.65,17.5 51.65,42.5 30,55 8.35,42.5 8.35,17.5" fill="${{fill}}" stroke="${{stroke}}" stroke-width="3"/>` +
          `<text x="30" y="37" font-size="22" text-anchor="middle" fill="#0d0b1a">${{icon}}</text>` +
          `</svg>`;
  }} else if (shape === 'flag') {{
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">` +
          `<polygon points="5,5 55,5 42.5,30 55,55 5,55" fill="${{fill}}" stroke="${{stroke}}" stroke-width="3"/>` +
          `<text x="25" y="37" font-size="24" text-anchor="middle" fill="#0d0b1a">${{icon}}</text>` +
          `</svg>`;
  }} else if (shape === 'trapez') {{
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">` +
          `<polygon points="15,5 45,5 55,55 5,55" fill="${{fill}}" stroke="${{stroke}}" stroke-width="3"/>` +
          `<text x="30" y="38" font-size="24" text-anchor="middle" fill="#0d0b1a">${{icon}}</text>` +
          `</svg>`;
  }} else {{
    // Default circle
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">` +
          `<circle cx="30" cy="30" r="23" fill="${{fill}}" stroke="${{stroke}}" stroke-width="3"/>` +
          `<text x="30" y="37" font-size="24" text-anchor="middle" fill="#0d0b1a">${{icon}}</text>` +
          `</svg>`;
  }}
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}}

// Build Tooltip HTML helper
function makeTooltipHtml(n) {{
  let html = `<strong>${{n.label}}</strong><br>` +
             `<span class="tt-type">${{n.type}}</span>`;
  if (n.desc) html += `<hr class="tt-sep"><div class="tt-row">${{n.desc}}</div>`;
  const metaEntries = Object.entries(n.meta || {{}});
  if (metaEntries.length) {{
    html += `<hr class="tt-sep">`;
    metaEntries.forEach(([k,v]) => {{
      html += `<div class="tt-row">${{k}}: <span>${{v}}</span></div>`;
    }});
  }}
  return html;
}}

// Add nodes
DATA.nodes.forEach(n => {{
  nodesDataset.add({{
    id: n.id,
    label: n.label,
    shape: 'image',
    image: makeSvgDataUrl(n),
    title: makeTooltipHtml(n)
  }});
}});

// Add edges
DATA.edges.forEach(e => {{
  let dash = false;
  if (e.dash && e.dash !== 'none') {{
    dash = true;
  }}
  let edgeOpt = {{
    id: e.id,
    from: e.source,
    to: e.target,
    label: e.label || undefined,
    color: {{ color: e.stroke || "{_h_accent}", hover: "{_h_accent}", highlight: "{_h_accent}" }},
    dashes: dash,
    arrows: e.arrow ? {{ to: {{ enabled: true, scaleFactor: 0.8 }} }} : undefined
  }};
  edgesDataset.add(edgeOpt);
}});

const container = document.getElementById('canvas');
const options = {{
  nodes: {{
    font: {{
      color: "{_h_txt_pri}",
      size: 11,
      face: 'Segoe UI'
    }}
  }},
  edges: {{
    font: {{
      color: "{_h_accent2}",
      size: 10,
      face: 'Segoe UI',
      align: 'top'
    }},
    smooth: {{
      type: 'cubicBezier',
      forceDirection: 'none',
      roundness: 0.3
    }}
  }},
  interaction: {{
    hover: true,
    navigationButtons: false,
    tooltipDelay: 200,
    selectConnectedEdges: false
  }},
  physics: {{
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{
      gravitationalConstant: -50,
      centralGravity: 0.01,
      springLength: 100,
      springConstant: 0.08,
      damping: 0.4
    }}
  }}
}};

const directionMap = {{
  "TD": "UD",
  "LR": "LR",
  "RL": "RL",
  "BT": "DU"
}};

if (DATA.direction) {{
  options.layout = {{
    hierarchical: {{
      enabled: true,
      direction: directionMap[DATA.direction] || 'UD',
      sortMethod: 'directed',
      nodeSpacing: 150,
      levelSeparation: 150,
      blockShifting: false,
      edgeMinimization: true,
      parentCentralization: true
    }}
  }};
}}

const network = new vis.Network(container, {{ nodes: nodesDataset, edges: edgesDataset }}, options);

// Listen to selections
network.on("selectNode", function(params) {{
  if (params.nodes.length > 0 && BRIDGE) {{
    BRIDGE.onNodeSelected(String(params.nodes[0]));
  }}
}});

network.on("selectEdge", function(params) {{
  if (params.edges.length > 0 && BRIDGE) {{
    BRIDGE.onEdgeSelected(String(params.edges[0]));
  }}
}});

// Listen to context menu
network.on("oncontext", function(params) {{
  params.event.preventDefault();
  const nodeId = network.getNodeAt(params.pointer.DOM);
  const edgeId = nodeId ? null : network.getEdgeAt(params.pointer.DOM);
  let itemType = "background";
  let itemId = "";
  if (nodeId) {{
    itemType = "node";
    itemId = String(nodeId);
  }} else if (edgeId) {{
    itemType = "edge";
    itemId = String(edgeId);
  }}
  if (BRIDGE) {{
    BRIDGE.onContextMenu(itemType, itemId, Math.round(params.pointer.DOM.x), Math.round(params.pointer.DOM.y));
  }}
}});

// Programmatic selection helpers
window.selectNode = function(nodeId) {{
  network.selectNodes([nodeId]);
}};
window.selectEdge = function(edgeId) {{
  network.selectEdges([edgeId]);
}};

window.addNode = function(n) {{
  if (nodesDataset.get(n.id)) {{
    return;
  }}
  nodesDataset.add({{
    id: n.id,
    label: n.label,
    shape: 'image',
    image: makeSvgDataUrl(n),
    title: makeTooltipHtml(n)
  }});
}};

window.addEdge = function(e) {{
  if (edgesDataset.get(e.id)) {{
    return;
  }}
  let dash = false;
  if (e.dash && e.dash !== 'none') {{
    dash = true;
  }}
  let edgeOpt = {{
    id: e.id,
    from: e.source,
    to: e.target,
    label: e.label || undefined,
    color: {{ color: e.stroke || "{_h_accent}", hover: "{_h_accent}", highlight: "{_h_accent}" }},
    dashes: dash,
    arrows: e.arrow ? {{ to: {{ enabled: true, scaleFactor: 0.8 }} }} : undefined
  }};
  edgesDataset.add(edgeOpt);
}};

// Headless test trigger functions
window.testTriggerNodeSelected = function(nodeId) {{
  if (BRIDGE) {{
    BRIDGE.onNodeSelected(nodeId);
  }}
}};
window.testTriggerEdgeSelected = function(edgeId) {{
  if (BRIDGE) {{
    BRIDGE.onEdgeSelected(edgeId);
  }}
}};
window.testTriggerContextMenu = function(itemType, itemId, x, y) {{
  if (BRIDGE) {{
    BRIDGE.onContextMenu(itemType, itemId, x, y);
  }}
}};

// === M4: Highlight shortest path ===
window.highlightPath = function(nodeIds) {{
  // Always reset first
  nodesDataset.get().forEach(n => {{
    nodesDataset.update({{id: n.id, opacity: 1.0}});
  }});
  edgesDataset.get().forEach(e => {{
    edgesDataset.update({{id: e.id, color: {{color: "{_h_accent}", opacity: 1.0}}, width: 1}});
  }});
  if (!nodeIds || nodeIds.length === 0) return;
  const pathSet = new Set(nodeIds);
  nodesDataset.get().forEach(n => {{
    if (!pathSet.has(n.id)) {{
      nodesDataset.update({{id: n.id, opacity: 0.15}});
    }}
  }});
  edgesDataset.get().forEach(e => {{
    const onPath = pathSet.has(String(e.from)) && pathSet.has(String(e.to));
    if (!onPath) {{
      edgesDataset.update({{id: e.id, color: {{color: "{_h_accent}", opacity: 0.08}}, width: 1}});
    }} else {{
      edgesDataset.update({{id: e.id, color: {{color: "#f472b6", opacity: 1.0}}, width: 4}});
    }}
  }});
}};

// === M4: Apply centrality node sizes ===
window.applyCentralitySizes = function(sizesDict) {{
  const minSize = 20, maxSize = 65, defaultSize = 25;
  if (!sizesDict || Object.keys(sizesDict).length === 0) {{
    nodesDataset.get().forEach(n => {{
      nodesDataset.update({{id: n.id, size: defaultSize}});
    }});
    return;
  }}
  Object.entries(sizesDict).forEach(([nodeId, score]) => {{
    const pct  = Math.min(1.0, Math.max(0.0, score));
    const size = Math.round(minSize + pct * (maxSize - minSize));
    nodesDataset.update({{id: nodeId, size: size}});
  }});
}};

// === M5: Temporal filter by ISO date range ===
window.filterByTimeRange = function(startIso, endIso) {{
  const toMs  = iso => (iso && iso !== '') ? new Date(iso).getTime() : null;
  const startMs = toMs(startIso);
  const endMs   = toMs(endIso);
  const nodeVis = {{}};
  DATA.nodes.forEach(n => {{
    let vis = true;
    if (startMs !== null && n.valid_to   && n.valid_to   !== '') {{
      if (new Date(n.valid_to).getTime()   < startMs) vis = false;
    }}
    if (endMs   !== null && n.valid_from && n.valid_from !== '') {{
      if (new Date(n.valid_from).getTime() > endMs)   vis = false;
    }}
    nodeVis[n.id] = vis;
    if (nodesDataset.get(n.id)) nodesDataset.update({{id: n.id, hidden: !vis}});
  }});
  DATA.edges.forEach(e => {{
    let vis = (nodeVis[e.source] !== false) && (nodeVis[e.target] !== false);
    if (vis && e.valid_from && e.valid_from !== '' && endMs !== null) {{
      if (new Date(e.valid_from).getTime() > endMs) vis = false;
    }}
    if (vis && e.valid_to   && e.valid_to   !== '' && startMs !== null) {{
      if (new Date(e.valid_to).getTime()   < startMs) vis = false;
    }}
    if (edgesDataset.get(e.id)) edgesDataset.update({{id: e.id, hidden: !vis}});
  }});
}};
</script>
</body>
</html>
"""
    return html.replace("/*VIS_JS_PLACEHOLDER*/", vis_js_content)


def format_node_for_js(node: Node, theme: dict = None) -> dict:
    fill = _parse_style_color(
        node.mermaid_style, "fill", _TYPE_COLORS.get(node.node_type, "#94a3b8")
    )
    return {
        "id": node.id,
        "label": node.label,
        "type": node.node_type,
        "desc": node.description,
        "fill": fill,
        "icon": _TYPE_SYMBOLS.get(node.node_type, "●"),
        "meta": node.metadata,
        "shape": SHAPE_ID_TO_D3.get(node.mermaid_shape, "circle"),
    }


def format_edge_for_js(edge: Edge, theme: dict | None = None) -> dict:
    _td = theme or {}
    _h_accent = _td.get("accent_color", "#c084fc")
    stroke = _parse_style_color(edge.mermaid_style, "stroke", _h_accent)
    dash = _EDGE_DASH.get(edge.mermaid_line, "none")
    return {
        "id": edge.id,
        "source": edge.source_id,
        "target": edge.target_id,
        "label": edge.label,
        "type": edge.edge_type,
        "stroke": stroke,
        "dash": dash,
        "arrow": "-->" not in (edge.mermaid_line or "") or True,
    }
