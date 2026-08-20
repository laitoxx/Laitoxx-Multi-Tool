"""Generate Mermaid source for graph previews and exports."""

from __future__ import annotations

from laitoxx.shared.graph.model import SHAPE_ID_TO_TOKENS, Graph, Node

_SAFE_LABEL_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.")


def _safe_label(text: str) -> str:
    text = text.replace('"', "'")
    needs_quote = any(character not in _SAFE_LABEL_CHARS for character in text)
    return f'"{text}"' if needs_quote or not text else text


def _node_line(node: Node) -> str:
    open_token, close_token = SHAPE_ID_TO_TOKENS.get(node.mermaid_shape, ("[", "]"))
    return f"    {node.id}{open_token}{_safe_label(node.label)}{close_token}"


def generate_mermaid(graph: Graph) -> str:
    lines: list[str] = [f"graph {graph.direction}"]
    for node in graph.nodes:
        lines.append(_node_line(node))
    for node in graph.nodes:
        if node.mermaid_style:
            lines.append(f"    style {node.id} {node.mermaid_style}")
    link_styles: list[str] = []
    for index, edge in enumerate(graph.edges):
        line_type = edge.mermaid_line or "-->"
        connector = f"{line_type}|{edge.label.replace('|', '/')}|" if edge.label else line_type
        lines.append(f"    {edge.source_id} {connector} {edge.target_id}")
        if edge.mermaid_style:
            link_styles.append(f"    linkStyle {index} {edge.mermaid_style}")
    lines.extend(link_styles)
    return "\n".join(lines)
