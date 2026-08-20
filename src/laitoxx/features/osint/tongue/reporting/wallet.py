"""Human-readable wallet scan reports."""

from __future__ import annotations

import html
import json
import math
from collections.abc import Mapping
from typing import Any

from ..domain.primitives import jsonable, short


def mermaid_escape(text: str) -> str:
    return text.replace('"', "'").replace("\n", " ")


def render_mermaid(graph: Mapping[str, Any], max_nodes: int = 60) -> str:
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    nodes.sort(key=lambda x: float(x.get("weight") or 0), reverse=True)
    selected = {str(x.get("id")) for x in nodes[:max_nodes]}
    node_ids = {node_id: f"N{i}" for i, node_id in enumerate(selected)}
    lines = ["flowchart LR"]
    for node in nodes:
        node_id = str(node.get("id"))
        if node_id not in selected:
            continue
        label = mermaid_escape(str(node.get("label") or short(node_id)))
        shape_l, shape_r = ("((", "))") if node.get("type") == "seed" else ("[", "]")
        lines.append(f'    {node_ids[node_id]}{shape_l}"{label}"{shape_r}')
    for edge in edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        if source not in selected or target not in selected:
            continue
        label = mermaid_escape(str(edge.get("label") or edge.get("kind") or "link"))
        if edge.get("kind") == "TON_TRANSFER":
            total = float(edge.get("total_ton") or 0)
            label += f" {total:.4g} TON / {edge.get('count', 1)}x"
        lines.append(f'    {node_ids[source]} -->|"{label}"| {node_ids[target]}')
    return "\n".join(lines) + "\n"


def render_html_report(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    graph = report.get("graph") or {}
    nodes = sorted(graph.get("nodes") or [], key=lambda x: float(x.get("weight") or 0), reverse=True)
    # Keep the HTML graph readable; all data remains in JSON/CSV.
    max_nodes = 90
    selected_nodes = nodes[:max_nodes]
    selected_ids = {str(n.get("id")) for n in selected_nodes}
    edges = [
        e
        for e in graph.get("edges") or []
        if str(e.get("source")) in selected_ids and str(e.get("target")) in selected_ids
    ]

    width, height = 1600, 1100
    cx, cy = width / 2, height / 2
    seed_nodes = [n for n in selected_nodes if n.get("type") == "seed"]
    others = [n for n in selected_nodes if n.get("type") != "seed"]
    positions: dict[str, tuple[float, float]] = {}
    for seed in seed_nodes:
        positions[str(seed["id"])] = (cx, cy)
    for idx, node in enumerate(others):
        ring = idx // 30
        within = idx % 30
        count_on_ring = min(30, len(others) - ring * 30)
        radius = 220 + ring * 150
        angle = (2 * math.pi * within / max(count_on_ring, 1)) - math.pi / 2
        positions[str(node["id"])] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    edge_svg = []
    for edge in edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        weight = max(1.0, min(8.0, 1.0 + math.log1p(float(edge.get("weight") or 0))))
        kind = str(edge.get("kind") or "")
        css_class = {
            "TON_TRANSFER": "edge-ton",
            "JETTON_TRANSFER": "edge-jetton",
            "NFT_TRANSFER": "edge-nft",
            "OWNS_NFT": "edge-own",
        }.get(kind, "edge-other")
        title = html.escape(
            f"{edge.get('label')} | count={edge.get('count')} | TON={float(edge.get('total_ton') or 0):.9g}"
        )
        edge_svg.append(
            f'<line class="edge {css_class}" x1="{x1:.2f}" y1="{y1:.2f}" '
            f'x2="{x2:.2f}" y2="{y2:.2f}" stroke-width="{weight:.2f}" marker-end="url(#arrow)">'
            f"<title>{title}</title></line>"
        )

    type_class = {
        "seed": "node-seed",
        "account": "node-account",
        "nft": "node-nft",
        "possible_gift": "node-gift",
    }
    node_svg = []
    for node in selected_nodes:
        node_id = str(node.get("id"))
        x, y = positions[node_id]
        radius = 13 if node.get("type") != "seed" else 25
        radius += min(11, math.log1p(float(node.get("weight") or 1)) * 2)
        css_class = type_class.get(str(node.get("type")), "node-other")
        label = str(node.get("label") or short(node_id))
        display = label if len(label) <= 25 else label[:22] + "…"
        detail_json = html.escape(json.dumps(jsonable(node), ensure_ascii=False))
        node_svg.append(
            f'<g class="node {css_class}" data-detail="{detail_json}" tabindex="0">'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}"><title>{html.escape(label)}</title></circle>'
            f'<text x="{x:.2f}" y="{y + radius + 15:.2f}" text-anchor="middle">{html.escape(display)}</text>'
            f"</g>"
        )

    cards = [
        ("Balance", f"{float(summary.get('balance_ton') or 0):,.6f} TON"),
        ("Transactions", str(summary.get("transactions_loaded", 0))),
        ("Counterparties", str(summary.get("counterparties", 0))),
        ("NFT", str(summary.get("nft_items", 0))),
        ("Gift candidates", str(summary.get("possible_telegram_collectibles", 0))),
        ("Jetton transfers", str(summary.get("jetton_transfers", 0))),
    ]
    cards_html = "".join(
        f'<div class="card"><span>{html.escape(title)}</span><strong>{html.escape(value)}</strong></div>'
        for title, value in cards
    )

    cp_rows = report.get("counterparties") or []
    cp_html = "".join(
        "<tr>"
        f"<td title='{html.escape(str(row.get('address')))}'>{html.escape(str(row.get('label')))}</td>"
        f"<td>{int(row.get('incoming_count') or 0)}</td>"
        f"<td>{float(row.get('incoming_ton') or 0):.6g}</td>"
        f"<td>{int(row.get('outgoing_count') or 0)}</td>"
        f"<td>{float(row.get('outgoing_ton') or 0):.6g}</td>"
        f"<td>{html.escape(str(row.get('classification')))}</td>"
        f"<td>{float(row.get('classification_confidence') or 0):.2f}</td>"
        "</tr>"
        for row in cp_rows[:100]
    )

    gifts = report.get("gift_candidates") or []
    gifts_html = (
        "".join(
            "<tr>"
            f"<td>{html.escape(str((row.get('token_info') or {}).get('name') or short(str(row.get('address')))))}</td>"
            f"<td title='{html.escape(str(row.get('address')))}'>{html.escape(short(str(row.get('address'))))}</td>"
            f"<td>{float(row.get('gift_confidence') or 0):.2f}</td>"
            f"<td>{html.escape(', '.join(map(str, row.get('gift_evidence') or [])))}</td>"
            "</tr>"
            for row in gifts[:100]
        )
        or '<tr><td colspan="4">No heuristic Telegram collectible candidates in the current NFT inventory.</td></tr>'
    )

    summary_json = html.escape(json.dumps(jsonable(summary), ensure_ascii=False, indent=2))
    generated = html.escape(str(summary.get("generated_at")))
    seed = html.escape(str(summary.get("seed_raw")))

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TON public scan - {seed}</title>
<style>
:root {{ color-scheme: dark; --bg:#0b1020; --panel:#131a2d; --muted:#9ba7c0; --text:#eef2ff; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:14px/1.45 Inter,Segoe UI,Arial,sans-serif; }}
header {{ padding:24px 30px 12px; }}
h1 {{ margin:0 0 8px; font-size:24px; }}
code {{ color:#b9c7ff; word-break:break-all; }}
small,.muted {{ color:var(--muted); }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; padding:12px 30px 20px; }}
.card {{ background:var(--panel); border:1px solid #26324d; border-radius:12px; padding:14px; }}
.card span {{ color:var(--muted); display:block; }} .card strong {{ font-size:19px; }}
.layout {{ display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:14px; padding:0 20px 20px; }}
.panel {{ background:var(--panel); border:1px solid #26324d; border-radius:14px; overflow:hidden; }}
.panel h2 {{ margin:0; padding:14px 16px; border-bottom:1px solid #26324d; font-size:16px; }}
.graph-wrap {{ overflow:auto; min-height:650px; }}
svg {{ min-width:1100px; width:100%; height:auto; background:radial-gradient(circle at 50% 50%,#16203a,#0d1324 70%); }}
.edge {{ opacity:.52; }} .edge-ton {{ stroke:#71b7ff; }} .edge-jetton {{ stroke:#b48cff; }} .edge-nft {{ stroke:#ffbf69; }} .edge-own {{ stroke:#7de2a7; stroke-dasharray:5 4; }} .edge-other {{ stroke:#75809a; }}
.node {{ cursor:pointer; }} .node circle {{ stroke-width:2; transition:.15s; }} .node:hover circle,.node:focus circle {{ stroke:#fff; stroke-width:4; }}
.node text {{ fill:#e9edff; font-size:11px; paint-order:stroke; stroke:#0b1020; stroke-width:3px; stroke-linejoin:round; }}
.node-seed circle {{ fill:#ff5d73; stroke:#ffb1bd; }} .node-account circle {{ fill:#377dff; stroke:#9fc2ff; }} .node-nft circle {{ fill:#0fa77a; stroke:#79e4c2; }} .node-gift circle {{ fill:#e78a17; stroke:#ffd194; }} .node-other circle {{ fill:#6f7890; stroke:#b8bfd1; }}
#detail {{ padding:14px; white-space:pre-wrap; word-break:break-word; max-height:760px; overflow:auto; color:#d8def0; }}
section.table-panel {{ margin:0 20px 20px; background:var(--panel); border:1px solid #26324d; border-radius:14px; overflow:auto; }}
section.table-panel h2 {{ padding:14px 16px; margin:0; }}
table {{ width:100%; border-collapse:collapse; }} th,td {{ text-align:left; border-top:1px solid #26324d; padding:9px 12px; vertical-align:top; }} th {{ color:#b9c5dc; position:sticky; top:0; background:#161e33; }}
details {{ margin:0 20px 30px; }} pre {{ background:#10172a; padding:14px; border-radius:10px; overflow:auto; }}
.legend {{ padding:0 30px 14px; color:var(--muted); }}
@media(max-width:900px) {{ .layout {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>TON Public Correlator</h1>
  <div><code>{seed}</code></div>
  <small>Generated: {generated}. Graph contains the {max_nodes} highest-weight nodes; raw JSON/CSV keeps all loaded data.</small>
</header>
<div class="cards">{cards_html}</div>
<div class="legend">TON - blue · Jetton - purple · NFT transfer - orange · current NFT ownership - dashed green. Gift detection is heuristic, not identity proof.</div>
<div class="layout">
  <div class="panel graph-wrap">
    <h2>Evidence graph</h2>
    <svg viewBox="0 0 {width} {height}" role="img">
      <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L8,3 z" fill="#aeb8cf"/></marker></defs>
      {"".join(edge_svg)}
      {"".join(node_svg)}
    </svg>
  </div>
  <aside class="panel"><h2>Selected node</h2><div id="detail">Click a node to inspect evidence.</div></aside>
</div>
<section class="table-panel"><h2>Top counterparties</h2><table><thead><tr><th>Label</th><th>In #</th><th>In TON</th><th>Out #</th><th>Out TON</th><th>Classification</th><th>Confidence</th></tr></thead><tbody>{cp_html}</tbody></table></section>
<section class="table-panel"><h2>Possible Telegram collectibles</h2><table><thead><tr><th>Name</th><th>NFT</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody>{gifts_html}</tbody></table></section>
<details><summary>Scan summary JSON</summary><pre>{summary_json}</pre></details>
<script>
for (const node of document.querySelectorAll('.node')) {{
  const show = () => {{
    try {{ document.getElementById('detail').textContent = JSON.stringify(JSON.parse(node.dataset.detail), null, 2); }}
    catch (e) {{ document.getElementById('detail').textContent = node.dataset.detail; }}
  }};
  node.addEventListener('click', show);
  node.addEventListener('keydown', e => {{ if (e.key === 'Enter' || e.key === ' ') show(); }});
}}
</script>
</body>
</html>"""
