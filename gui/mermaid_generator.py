"""
mermaid_generator.py
  - generate_mermaid()  → raw Mermaid string (kept for the code-preview panel)
  - generate_html()     → full D3.js v7 force-directed interactive graph
"""
from __future__ import annotations

import json as _json
from gui.graph_model import Graph, Node, SHAPE_ID_TO_TOKENS, SHAPE_ID_TO_D3
from gui.translator import translator as _translator

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
# D3.js colour palette per node type
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


# ---------------------------------------------------------------------------
# D3 HTML generator
# ---------------------------------------------------------------------------

def generate_html(graph: Graph, lang: str = None, theme: dict = None) -> str:
    """
    Returns a self-contained HTML page with a D3.js v7 force-directed graph.
    Features:
      - Force simulation with link / charge / collision / center forces
      - Drag & drop nodes
      - Zoom & pan (mouse wheel + drag on background)
      - Node hover: highlight neighbours, dim others, show tooltip
      - Click node/edge: show info card
      - Animated link arrows
      - Per-type colours + emoji icons
      - Gradient background, glow effects, smooth curves
      - Node size proportional to degree
    """
    # Use provided lang or current translator lang
    if lang:
        _translator.set_language(lang)
    def _t(key):
        return _translator.get(key)

    # Extract theme colors (fall back to defaults if no theme provided)
    _td = theme or {}
    _h_accent   = _td.get("accent_color",          "#c084fc")
    _h_accent2  = _td.get("text_secondary_color",  "#a78bfa")
    _h_bg       = _td.get("window_bg_color",        _td.get("text_area_bg_color", "#0d0b1a"))
    _h_bdr      = _td.get("border_color",           _td.get("button_border_color", "rgba(192,132,252,0.35)"))
    _h_txt_pri  = _td.get("text_area_text_color",   "#f1f0ff")
    _h_txt_sec  = _td.get("text_secondary_color",   "#94a3b8")
    # Derive a darker bg for overlays by using the window_bg_color with higher opacity
    _h_bg_dark  = _h_bg if _h_bg.startswith("rgba") else _h_bg
    # Build body background: use window_bg_color as base
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
            "shape": SHAPE_ID_TO_D3.get(n.mermaid_shape, "circle"),
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

svg {{
  width: 100%; height: 100%;
  cursor: grab;
}}
svg:active {{ cursor: grabbing; }}

/* Links */
.link {{
  fill: none;
  stroke-width: 1.8;
  transition: stroke-width 0.2s, opacity 0.3s;
}}
.link.dimmed {{ opacity: 0.08; }}

.link-label {{
  font-size: 10px;
  fill: {_h_accent2};
  pointer-events: none;
  opacity: 0.85;
}}

/* Nodes */
.node-group {{ cursor: pointer; }}

.node-bg {{
  transition: r 0.2s, filter 0.2s, opacity 0.3s;
}}
.node-bg.dimmed {{ opacity: 0.12; }}

.node-ring {{
  fill: none;
  opacity: 0.4;
  transition: opacity 0.25s, r 0.2s;
}}
.node-group:hover .node-ring {{ opacity: 0.85; }}

.node-icon {{
  font-size: 14px;
  dominant-baseline: central;
  text-anchor: middle;
  pointer-events: none;
  user-select: none;
  transition: opacity 0.3s;
}}
.node-label {{
  font-size: 11px;
  font-weight: 600;
  fill: {_h_txt_pri};
  dominant-baseline: hanging;
  text-anchor: middle;
  pointer-events: none;
  user-select: none;
  paint-order: stroke;
  stroke: {_h_bg};
  stroke-width: 3px;
  stroke-linejoin: round;
  transition: opacity 0.3s;
}}
.node-bg.dimmed ~ .node-icon,
.node-bg.dimmed ~ .node-label {{ opacity: 0.1; }}

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
}}
</style>
</head>
<body>

<svg id="canvas">
  <defs>
    <!-- Arrow markers per colour will be added by JS -->
    <filter id="glow-purple" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow-soft" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g id="root"></g>
</svg>

<div id="tooltip"></div>
<div id="info-panel">
  <kbd>{_t('ge_d3_zoom')}</kbd> {_t('ge_d3_zoom_hint')} &nbsp;·&nbsp; <kbd>{_t('ge_d3_drag')}</kbd> {_t('ge_d3_drag_hint')} &nbsp;·&nbsp; <kbd>{_t('ge_d3_hover')}</kbd> {_t('ge_d3_hover_hint')}
</div>
<div id="stats"></div>

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script>
const DATA = {graph_json};

let BRIDGE = null;
if (window.qt && window.qt.webChannelTransport) {{
  new QWebChannel(qt.webChannelTransport, function(channel) {{
    BRIDGE = channel.objects.bridge || null;
  }});
}}

const W = () => window.innerWidth;
const H = () => window.innerHeight;

// ── build adjacency for neighbour-highlight ──────────────────────────────────
const adjSet = new Set();
DATA.edges.forEach(e => {{
  adjSet.add(e.source + '|' + e.target);
  adjSet.add(e.target + '|' + e.source);
}});
function linked(a, b) {{ return adjSet.has(a + '|' + b); }}

// ── degree map (for node size) ───────────────────────────────────────────────
const degMap = {{}};
DATA.nodes.forEach(n => degMap[n.id] = 0);
DATA.edges.forEach(e => {{
  degMap[e.source] = (degMap[e.source] || 0) + 1;
  degMap[e.target] = (degMap[e.target] || 0) + 1;
}});
function nodeR(d) {{ return 18 + Math.min(degMap[d.id] || 0, 8) * 2.5; }}

// ── SVG + zoom setup ─────────────────────────────────────────────────────────
const svg = d3.select('#canvas');
const root = svg.select('#root');

const zoom = d3.zoom()
  .scaleExtent([0.12, 4])
  .on('zoom', (event) => root.attr('transform', event.transform));
svg.call(zoom);

// ── arrow marker factory ─────────────────────────────────────────────────────
const defs = svg.select('defs');
const markerColors = [...new Set(DATA.edges.map(e => e.stroke))];
markerColors.forEach(color => {{
  const safeId = 'arr-' + color.replace('#','');
  defs.append('marker')
    .attr('id', safeId)
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 28).attr('refY', 0)
    .attr('markerWidth', 7).attr('markerHeight', 7)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', color)
    .attr('opacity', 0.85);
}});
// default marker
defs.append('marker')
  .attr('id', 'arr-default')
  .attr('viewBox', '0 -5 10 10')
  .attr('refX', 28).attr('refY', 0)
  .attr('markerWidth', 7).attr('markerHeight', 7)
  .attr('orient', 'auto')
  .append('path').attr('d', 'M0,-5L10,0L0,5')
  .attr('fill', '#c084fc').attr('opacity', 0.7);

// ── force simulation ─────────────────────────────────────────────────────────
const sim = d3.forceSimulation(DATA.nodes)
  .force('link', d3.forceLink(DATA.edges)
    .id(d => d.id)
    .distance(d => 120 + nodeR(d.source) + nodeR(d.target))
    .strength(0.55))
  .force('charge', d3.forceManyBody().strength(-420).distanceMax(500))
  .force('center', d3.forceCenter(W() / 2, H() / 2).strength(0.06))
  .force('collision', d3.forceCollide().radius(d => nodeR(d) + 14))
  .alphaDecay(0.025);

// ── links ────────────────────────────────────────────────────────────────────
const linkG = root.append('g').attr('class', 'links');
const linkEl = linkG.selectAll('path')
  .data(DATA.edges)
  .join('path')
  .attr('class', 'link')
  .attr('stroke', d => d.stroke || '#c084fc')
  .attr('stroke-dasharray', d => d.dash !== 'none' ? d.dash : null)
  .attr('marker-end', d => {{
    const safeId = 'arr-' + (d.stroke || '#c084fc').replace('#','');
    return `url(#${{safeId}})`;
  }});

// ── edge labels ──────────────────────────────────────────────────────────────
const edgeLabelG = root.append('g').attr('class', 'edge-labels');
const edgeLabelEl = edgeLabelG.selectAll('text')
  .data(DATA.edges.filter(e => e.label))
  .join('text')
  .attr('class', 'link-label')
  .text(d => d.label);

// ── nodes ────────────────────────────────────────────────────────────────────
const nodeG = root.append('g').attr('class', 'nodes');
const nodeEl = nodeG.selectAll('g.node-group')
  .data(DATA.nodes)
  .join('g')
  .attr('class', 'node-group')
  .call(d3.drag()
    .on('start', dragStart)
    .on('drag',  dragged)
    .on('end',   dragEnd))
  .on('mouseover', onNodeHover)
  .on('mousemove', onMouseMove)
  .on('mouseout',  onNodeOut)
  .on('click', onNodeClick)
  .on('contextmenu', onNodeContextMenu);

// ── D3 symbol factory (shape-aware) ─────────────────────────────────────────
const symbolMap = {{
  'circle':  d3.symbolCircle,
  'square':  d3.symbolSquare,
  'diamond': d3.symbolDiamond,
  'triangle':d3.symbolTriangle,
  'wye':     d3.symbolWye,
  'star':    d3.symbolStar,
}};

function makeSymbol(d) {{
  const sym = symbolMap[d.shape] || d3.symbolCircle;
  const r = nodeR(d);
  return d3.symbol().type(sym).size(r * r * 3.8)();
}}

// outer glow ring (always circle for clean look)
nodeEl.append('circle')
  .attr('class', 'node-ring')
  .attr('r', d => nodeR(d) + 7)
  .attr('fill', 'none')
  .attr('stroke', d => d.fill)
  .attr('stroke-width', 2);

// main shape (D3 symbol)
nodeEl.append('path')
  .attr('class', 'node-bg')
  .attr('d', d => makeSymbol(d))
  .attr('fill', d => d.fill)
  .attr('fill-opacity', 0.88)
  .attr('filter', 'url(#glow-soft)')
  .attr('stroke', '#0d0b1a')
  .attr('stroke-width', 2);

// inner highlight (small circle overlay)
nodeEl.append('circle')
  .attr('r', d => nodeR(d) * 0.45)
  .attr('fill', 'rgba(255,255,255,0.09)')
  .attr('pointer-events', 'none');

// icon
nodeEl.append('text')
  .attr('class', 'node-icon')
  .attr('y', -3)
  .text(d => d.icon);

// label
nodeEl.append('text')
  .attr('class', 'node-label')
  .attr('y', d => nodeR(d) + 6)
  .text(d => d.label.length > 18 ? d.label.slice(0, 16) + '…' : d.label);

// ── stats badge ───────────────────────────────────────────────────────────────
d3.select('#stats').text(
  `${{DATA.nodes.length}} {_t('ge_d3_nodes_count')} · ${{DATA.edges.length}} {_t('ge_d3_edges_count')}`
);

// ── simulation tick ──────────────────────────────────────────────────────────
sim.on('tick', () => {{
  linkEl.attr('d', linkArc);
  edgeLabelEl
    .attr('x', d => ((d.source.x || 0) + (d.target.x || 0)) / 2)
    .attr('y', d => ((d.source.y || 0) + (d.target.y || 0)) / 2);
  nodeEl.attr('transform', d => `translate(${{d.x || 0}},${{d.y || 0}})`);
}});

function linkArc(d) {{
  const sx = d.source.x || 0, sy = d.source.y || 0;
  const tx = d.target.x || 0, ty = d.target.y || 0;
  // slight curve
  const mx = (sx + tx) / 2, my = (sy + ty) / 2;
  const dx = tx - sx, dy = ty - sy;
  const len = Math.sqrt(dx*dx + dy*dy) || 1;
  const cx = mx - dy / len * 30;
  const cy = my + dx / len * 30;
  return `M${{sx}},${{sy}} Q${{cx}},${{cy}} ${{tx}},${{ty}}`;
}}

// ── drag handlers ─────────────────────────────────────────────────────────────
function dragStart(event, d) {{
  if (!event.active) sim.alphaTarget(0.25).restart();
  d.fx = d.x; d.fy = d.y;
}}
function dragged(event, d) {{
  d.fx = event.x; d.fy = event.y;
}}
function dragEnd(event, d) {{
  if (!event.active) sim.alphaTarget(0);
  d.fx = null; d.fy = null;
}}

// ── hover / tooltip ───────────────────────────────────────────────────────────
const tooltip = document.getElementById('tooltip');
let hoveredId = null;

function onNodeHover(event, d) {{
  hoveredId = d.id;

  // dim non-neighbours
  nodeEl.selectAll('.node-bg').classed('dimmed',
    n => n.id !== d.id && !linked(d.id, n.id));
  linkEl.classed('dimmed',
    e => e.source.id !== d.id && e.target.id !== d.id);

  // build tooltip
  let html = `<strong>${{d.label}}</strong><br>
    <span class="tt-type">${{d.type}}</span>`;
  if (d.desc) html += `<hr class="tt-sep"><div class="tt-row">${{d.desc}}</div>`;
  const metaEntries = Object.entries(d.meta || {{}});
  if (metaEntries.length) {{
    html += `<hr class="tt-sep">`;
    metaEntries.forEach(([k,v]) => {{
      html += `<div class="tt-row">${{k}}: <span>${{v}}</span></div>`;
    }});
  }}
  html += `<hr class="tt-sep"><div class="tt-row">{_t('ge_d3_connections')}: <span>${{degMap[d.id] || 0}}</span></div>`;
  tooltip.innerHTML = html;
  tooltip.classList.add('visible');
  positionTooltip(event);
}}

function onMouseMove(event) {{
  positionTooltip(event);
}}

function onNodeOut() {{
  hoveredId = null;
  nodeEl.selectAll('.node-bg').classed('dimmed', false);
  linkEl.classed('dimmed', false);
  tooltip.classList.remove('visible');
}}

function positionTooltip(event) {{
  const x = event.clientX, y = event.clientY;
  const tw = tooltip.offsetWidth, th = tooltip.offsetHeight;
  const px = x + 14 + tw > W() ? x - tw - 14 : x + 14;
  const py = y + 10 + th > H() ? y - th - 10 : y + 10;
  tooltip.style.left = px + 'px';
  tooltip.style.top  = py + 'px';
}}

function onNodeClick(event, d) {{
  event.stopPropagation();
  // pulse animation
  d3.select(this).select('.node-ring')
    .attr('r', nodeR(d) + 18)
    .transition().duration(400).ease(d3.easeElasticOut)
    .attr('r', nodeR(d) + 7);
}}

function onNodeContextMenu(event, d) {{
  event.preventDefault();
  event.stopPropagation();
  if (BRIDGE && BRIDGE.onNodeContext) {{
    BRIDGE.onNodeContext(String(d.id), Math.round(event.clientX), Math.round(event.clientY));
  }}
}}

svg.on('contextmenu', (event) => {{
  if (event.defaultPrevented) return;
  event.preventDefault();
  if (BRIDGE && BRIDGE.onBackgroundContext) {{
    BRIDGE.onBackgroundContext(Math.round(event.clientX), Math.round(event.clientY));
  }}
}});

// ── resize ────────────────────────────────────────────────────────────────────
window.addEventListener('resize', () => {{
  sim.force('center', d3.forceCenter(W()/2, H()/2).strength(0.06));
  sim.alpha(0.1).restart();
}});

// ── initial zoom to fit (after sim settles) ───────────────────────────────────
sim.on('end', () => {{
  const bounds = root.node().getBBox();
  if (!bounds.width || !bounds.height) return;
  const pad = 60;
  const scale = Math.min(
    (W() - pad*2) / bounds.width,
    (H() - pad*2) / bounds.height,
    1.2
  );
  const tx = W()/2 - scale*(bounds.x + bounds.width/2);
  const ty = H()/2 - scale*(bounds.y + bounds.height/2);
  svg.transition().duration(900).ease(d3.easeCubicInOut)
    .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}});
</script>
</body>
</html>
"""
