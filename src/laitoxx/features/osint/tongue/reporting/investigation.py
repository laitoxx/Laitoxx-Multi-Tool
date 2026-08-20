"""Human-readable gift investigation reports."""

from __future__ import annotations

import html
import json
import math
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from ..domain.primitives import jsonable, safe_int, short
from .wallet import mermaid_escape


def render_investigation_mermaid(graph: Mapping[str, Any], max_nodes: int = 120) -> str:
    nodes = list(graph.get("nodes") or [])[:max_nodes]
    allowed = {str(n.get("id")) for n in nodes}
    aliases = {str(n.get("id")): f"n{i}" for i, n in enumerate(nodes)}
    lines = ["flowchart LR"]
    for node in nodes:
        node_id = str(node.get("id"))
        label = mermaid_escape(str(node.get("label") or node_id))
        shape = "([{}])" if node.get("type") == "gift" else "[{}]"
        lines.append(f"    {aliases[node_id]}{shape.format(label)}")
    for edge in graph.get("edges") or []:
        source, target = str(edge.get("source")), str(edge.get("target"))
        if source not in allowed or target not in allowed:
            continue
        relation = mermaid_escape(str(edge.get("relation") or edge.get("kind") or "RELATED"))
        confidence = float(edge.get("confidence") or 0)
        lines.append(f'    {aliases[source]} -->|"{relation} · {confidence:.2f}"| {aliases[target]}')
    return "\n".join(lines) + "\n"


def render_investigation_html(report: Mapping[str, Any], max_nodes: int = 180) -> str:
    graph = report.get("graph") or {}
    nodes = list(graph.get("nodes") or [])[:max_nodes]
    allowed = {str(n.get("id")) for n in nodes}
    edges = [e for e in graph.get("edges") or [] if str(e.get("source")) in allowed and str(e.get("target")) in allowed]
    width, height = 1700, 1150
    cx, cy = width / 2, height / 2
    positions: dict[str, tuple[float, float]] = {}
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for node in nodes:
        groups[str(node.get("type") or "other")].append(node)
    ordered = []
    for key in ("gift", "nft", "nft_event", "wallet", "telegram_profile", "other"):
        ordered.extend(groups.pop(key, []))
    for rest in groups.values():
        ordered.extend(rest)
    for idx, node in enumerate(ordered):
        if idx == 0:
            positions[str(node.get("id"))] = (cx, cy)
            continue
        ring = (idx - 1) // 32
        within = (idx - 1) % 32
        count = min(32, max(1, len(ordered) - 1 - ring * 32))
        radius = 230 + ring * 150
        angle = 2 * math.pi * within / count - math.pi / 2
        positions[str(node.get("id"))] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    edge_svg = []
    for edge in edges:
        source, target = str(edge.get("source")), str(edge.get("target"))
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        relation = str(edge.get("relation") or edge.get("kind") or "RELATED")
        confidence = float(edge.get("confidence") or 0)
        title = html.escape(
            f"{relation} | confidence={confidence:.2f} | {', '.join(map(str, edge.get('evidence') or []))}"
        )
        edge_svg.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke-width="{1.2 + confidence * 3:.2f}" marker-end="url(#arrow)"><title>{title}</title></line>'
        )
    colors = {
        "gift": "#f59e0b",
        "nft": "#10b981",
        "nft_event": "#a78bfa",
        "wallet": "#3b82f6",
        "telegram_profile": "#ec4899",
        "other": "#64748b",
    }
    node_svg = []
    for node in nodes:
        nid = str(node.get("id"))
        x, y = positions[nid]
        kind = str(node.get("type") or "other")
        label = str(node.get("label") or short(nid))
        display = label if len(label) <= 26 else label[:23] + "…"
        detail = html.escape(json.dumps(jsonable(node), ensure_ascii=False))
        radius = 23 if kind == "gift" else (18 if kind in {"nft", "wallet"} else 14)
        node_svg.append(
            f'<g class="node" tabindex="0" data-detail="{detail}">'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{colors.get(kind, colors["other"])}">'
            f"<title>{html.escape(label)}</title></circle>"
            f'<text x="{x:.2f}" y="{y + radius + 15:.2f}" text-anchor="middle">{html.escape(display)}</text></g>'
        )
    summary = report.get("summary") or {}
    cards = "".join(
        f'<div class="card"><span>{html.escape(str(k))}</span><strong>{html.escape(str(v))}</strong></div>'
        for k, v in list(summary.items())[:14]
    )
    timeline_rows: list[Mapping[str, Any]] = []
    timeline_rows.extend(report.get("history") or [])
    nested = report.get("nft_report") or {}
    if isinstance(nested, Mapping):
        timeline_rows.extend(nested.get("history") or [])
    for nft_address, rows in (report.get("timelines") or {}).items():
        for row in rows:
            timeline_rows.append({"timeline_nft": nft_address, **row})
    timeline_rows.sort(key=lambda r: (safe_int(r.get("transaction_lt")), str(r.get("transaction_time") or "")))
    timeline_html = (
        "".join(
            "<tr>"
            f"<td>{html.escape(str(r.get('transaction_time') or ''))}</td>"
            f"<td>{html.escape(str(r.get('event_type') or ''))}</td>"
            f"<td title='{html.escape(str(r.get('old_owner') or ''))}'>{html.escape(short(str(r.get('old_owner') or '')))}</td>"
            f"<td title='{html.escape(str(r.get('new_owner') or ''))}'>{html.escape(short(str(r.get('new_owner') or '')))}</td>"
            f"<td>{float(r.get('confidence') or 0):.2f}</td>"
            f"<td title='{html.escape(str(r.get('transaction_hash') or ''))}'>{html.escape(short(str(r.get('transaction_hash') or '')))}</td>"
            "</tr>"
            for r in timeline_rows[:5000]
        )
        or '<tr><td colspan="6">No resolved on-chain NFT history.</td></tr>'
    )
    raw_summary = html.escape(json.dumps(jsonable(summary), ensure_ascii=False, indent=2))
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TON Gift Correlator</title><style>
:root{{color-scheme:dark;--bg:#08111f;--panel:#111c2e;--border:#263752;--text:#eef4ff;--muted:#9fb0ca}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,Segoe UI,Arial,sans-serif}}
header{{padding:24px 28px 10px}}h1{{margin:0 0 7px}}.muted{{color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;padding:12px 28px 20px}}
.card,.panel{{background:var(--panel);border:1px solid var(--border);border-radius:13px}}.card{{padding:13px}}.card span{{display:block;color:var(--muted)}}.card strong{{font-size:18px;word-break:break-word}}
.layout{{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:14px;padding:0 18px 20px}}.panel{{overflow:hidden}}.panel h2{{font-size:16px;margin:0;padding:13px 15px;border-bottom:1px solid var(--border)}}
.graph{{overflow:auto;min-height:670px}}svg{{min-width:1150px;width:100%;height:auto;background:radial-gradient(circle,#142441,#08111f 70%)}}line{{stroke:#91a4c5;opacity:.52}}.node{{cursor:pointer}}.node circle{{stroke:#e4edff;stroke-width:1.5}}.node:hover circle,.node:focus circle{{stroke-width:4}}.node text{{fill:#f6f8ff;font-size:11px;paint-order:stroke;stroke:#08111f;stroke-width:3px}}
#detail{{padding:14px;white-space:pre-wrap;word-break:break-word;max-height:790px;overflow:auto}}section{{margin:0 18px 20px}}table{{width:100%;border-collapse:collapse}}th,td{{border-top:1px solid var(--border);padding:9px 11px;text-align:left}}th{{background:#142238;color:#b8c7dd;position:sticky;top:0}}.table-wrap{{overflow:auto;max-height:650px}}details{{margin:18px}}pre{{background:#0b1525;padding:14px;border-radius:10px;overflow:auto}}@media(max-width:900px){{.layout{{grid-template-columns:1fr}}}}
</style></head><body>
<header><h1>TON Gift / NFT Correlator</h1><div class="muted">Public-only evidence. A profile association is not automatically proof that the same person controls a TON wallet.</div></header>
<div class="cards">{cards}</div>
<div class="layout"><div class="panel graph"><h2>Evidence graph</h2><svg viewBox="0 0 {width} {height}"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#aab8cf"/></marker></defs>{"".join(edge_svg)}{"".join(node_svg)}</svg></div><aside class="panel"><h2>Selected entity</h2><div id="detail">Click a node to inspect evidence.</div></aside></div>
<section class="panel"><h2>NFT chronology</h2><div class="table-wrap"><table><thead><tr><th>Time</th><th>Event</th><th>From</th><th>To</th><th>Confidence</th><th>Tx</th></tr></thead><tbody>{timeline_html}</tbody></table></div></section>
<details><summary>Summary JSON</summary><pre>{raw_summary}</pre></details>
<script>for(const n of document.querySelectorAll('.node')){{const show=()=>{{try{{document.getElementById('detail').textContent=JSON.stringify(JSON.parse(n.dataset.detail),null,2)}}catch(e){{document.getElementById('detail').textContent=n.dataset.detail}}}};n.addEventListener('click',show);n.addEventListener('keydown',e=>{{if(e.key==='Enter'||e.key===' ')show()}})}}</script>
</body></html>"""
