"""
graph_model.py — Internal data model for the Graph Editor.
Node, Edge, Graph classes with full Mermaid style support.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Default styles per node type
# ---------------------------------------------------------------------------
NODE_TYPE_DEFAULTS: dict[str, dict] = {
    "Person":   {"shape": "round",   "style": "fill:#FFD700,stroke:#8B4513,stroke-width:2px,color:#000"},
    "Email":    {"shape": "rect",    "style": "fill:#ADD8E6,stroke:#1E90FF,stroke-width:2px,color:#000"},
    "Phone":    {"shape": "rect",    "style": "fill:#98FB98,stroke:#228B22,stroke-width:2px,color:#000"},
    "Website":  {"shape": "rect",    "style": "fill:#DDA0DD,stroke:#8B008B,stroke-width:2px,color:#000"},
    "Company":  {"shape": "diamond", "style": "fill:#90EE90,stroke:#2E8B57,stroke-width:2px,color:#000"},
    "IP":       {"shape": "rect",    "style": "fill:#F08080,stroke:#8B0000,stroke-width:2px,color:#000"},
    "Address":  {"shape": "rect",    "style": "fill:#FFDAB9,stroke:#D2691E,stroke-width:2px,color:#000"},
    "Document": {"shape": "rect",    "style": "fill:#E6E6FA,stroke:#483D8B,stroke-width:2px,color:#000"},
    "Custom":   {"shape": "rect",    "style": "fill:#CCCCCC,stroke:#555555,stroke-width:1px,color:#000"},
    # Username OSINT node types
    "Username":       {"shape": "round",   "style": "fill:#FF6B6B,stroke:#C0392B,stroke-width:3px,color:#000"},
    "SocialAccount":  {"shape": "rect",    "style": "fill:#74B9FF,stroke:#0984E3,stroke-width:2px,color:#000"},
    "AltAccount":     {"shape": "round",   "style": "fill:#FDCB6E,stroke:#F39C12,stroke-width:2px,color:#000"},
    "Category":       {"shape": "hexagon", "style": "fill:#A29BFE,stroke:#6C5CE7,stroke-width:2px,color:#000"},
}

NODE_TYPES = list(NODE_TYPE_DEFAULTS.keys())

# NODE_SHAPES: display_name -> (shape_id, open_token, close_token)
# shape_id is what gets stored in Node.mermaid_shape
NODE_SHAPES: dict[str, tuple[str, str, str]] = {
    "Прямоугольник":   ("rect",     "[",   "]"),
    "Скруглённый":     ("round",    "(",   ")"),
    "Круг":            ("circle",   "((", "))"),
    "Ромб":            ("diamond",  "{",   "}"),
    "Шестиугольник":   ("hexagon",  "{{", "}}"),
    "Флаг":            ("flag",     ">",   "]"),
    "Трапеция":        ("trapez",   "[/",  "/]"),
}

# shape_id -> (open, close) for Mermaid generation
SHAPE_ID_TO_TOKENS: dict[str, tuple[str, str]] = {
    v[0]: (v[1], v[2]) for v in NODE_SHAPES.values()
}

# shape_id -> D3 symbol hint (for visual differentiation in D3 viewer)
SHAPE_ID_TO_D3: dict[str, str] = {
    "rect":    "square",
    "round":   "circle",
    "circle":  "circle",
    "diamond": "diamond",
    "hexagon": "wye",
    "flag":    "triangle",
    "trapez":  "square",
}

# EDGE_TYPES = [
#     "Connected", "WorksFor", "Owns", "RelatedTo",
#     "Communicates", "LocatedAt", "MemberOf", "Custom",
#     # Username OSINT edge types
#     "RegisteredOn", "SamePersonAs", "AltAccountOf", "BelongsToCategory",
# ]

EDGE_LINE_TYPES: dict[str, str] = {
    "Arrow -->":          "-->",
    "Thick Arrow ==>":    "==>",
    "Dotted -..->":       "-.->",
    "Open ---":           "---",
    "Open Dotted -...-":  "-...-",
    "Double Arrow <-->":  "<-->",
}


@dataclass
class Node:
    label: str
    node_type: str = "Custom"
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    # Mermaid display
    mermaid_shape: str = "[]"          # e.g. "[]", "()", "(())", "{}"
    mermaid_style: str = ""            # CSS style string
    # Temporal fields
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    # Internal
    id: str = field(default_factory=lambda: f"N{uuid.uuid4().hex[:6].upper()}")

    @classmethod
    def from_type(cls, label: str, node_type: str = "Custom") -> "Node":
        defaults = NODE_TYPE_DEFAULTS.get(node_type, NODE_TYPE_DEFAULTS["Custom"])
        return cls(
            label=label,
            node_type=node_type,
            mermaid_shape=defaults["shape"],
            mermaid_style=defaults["style"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "node_type": self.node_type,
            "description": self.description,
            "metadata": self.metadata,
            "mermaid_shape": self.mermaid_shape,
            "mermaid_style": self.mermaid_style,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        n = cls(
            label=d.get("label", ""),
            node_type=d.get("node_type", "Custom"),
            description=d.get("description", ""),
            metadata=d.get("metadata", {}),
            mermaid_shape=d.get("mermaid_shape", "[]"),
            mermaid_style=d.get("mermaid_style", ""),
            valid_from=d.get("valid_from", None),
            valid_to=d.get("valid_to", None),
        )
        n.id = d.get("id", n.id)
        return n


@dataclass
class Edge:
    source_id: str
    target_id: str
    label: str = ""
    edge_type: str = "Connected"
    metadata: dict[str, str] = field(default_factory=dict)
    # Mermaid display
    mermaid_line: str = "-->"          # e.g. "-->", "==>", "-.->", "---"
    mermaid_style: str = ""            # linkStyle CSS string
    # Temporal fields
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    # Internal
    id: str = field(default_factory=lambda: f"E{uuid.uuid4().hex[:6].upper()}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
            "edge_type": self.edge_type,
            "metadata": self.metadata,
            "mermaid_line": self.mermaid_line,
            "mermaid_style": self.mermaid_style,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        e = cls(
            source_id=d.get("source_id", ""),
            target_id=d.get("target_id", ""),
            label=d.get("label", ""),
            edge_type=d.get("edge_type", "Connected"),
            metadata=d.get("metadata", {}),
            mermaid_line=d.get("mermaid_line", "-->"),
            mermaid_style=d.get("mermaid_style", ""),
            valid_from=d.get("valid_from", None),
            valid_to=d.get("valid_to", None),
        )
        e.id = d.get("id", e.id)
        return e


class Graph:
    def __init__(self, name: str = "Untitled Graph", direction: str = "TD"):
        self.name = name
        self.direction = direction       # TD / LR / RL / BT
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> None:
        if not self.get_node(node.id):
            self.nodes.append(node)

    def remove_node(self, node_id: str) -> None:
        self.nodes = [n for n in self.nodes if n.id != node_id]
        # Remove dangling edges
        self.edges = [e for e in self.edges
                      if e.source_id != node_id and e.target_id != node_id]

    def get_node(self, node_id: str) -> Optional[Node]:
        return next((n for n in self.nodes if n.id == node_id), None)

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def add_edge(self, edge: Edge) -> bool:
        """Returns False if source or target node doesn't exist."""
        if not self.get_node(edge.source_id) or not self.get_node(edge.target_id):
            return False
        self.edges.append(edge)
        return True

    def remove_edge(self, edge_id: str) -> None:
        self.edges = [e for e in self.edges if e.id != edge_id]

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        return next((e for e in self.edges if e.id == edge_id), None)

    def merge_nodes(self, primary_id: str, duplicate_ids: list[str]) -> None:
        """
        Merge duplicate nodes into a primary node, combining descriptions,
        metadata, and temporal bounds, and re-routing edges.
        Deduplicates re-routed edges and combines their properties.
        """
        primary_node = self.get_node(primary_id)
        if not primary_node:
            raise ValueError(f"Primary node with ID '{primary_id}' not found in graph.")

        cleaned_duplicate_ids = []
        for d_id in duplicate_ids:
            if d_id == primary_id:
                continue
            dup_node = self.get_node(d_id)
            if dup_node:
                cleaned_duplicate_ids.append(d_id)

        if not cleaned_duplicate_ids:
            return

        # 1. Merge Node descriptions, metadata, and temporal bounds
        descriptions = [primary_node.description] if primary_node.description else []
        for d_id in cleaned_duplicate_ids:
            dup_node = self.get_node(d_id)
            if dup_node:
                if dup_node.description and dup_node.description not in descriptions:
                    descriptions.append(dup_node.description)

                for k, v in dup_node.metadata.items():
                    if k not in primary_node.metadata:
                        primary_node.metadata[k] = v

                # Merge temporal bounds (valid_from/valid_to)
                froms = [v for v in [primary_node.valid_from, dup_node.valid_from] if v is not None]
                if froms:
                    primary_node.valid_from = min(froms)
                tos = [v for v in [primary_node.valid_to, dup_node.valid_to] if v is not None]
                if tos:
                    primary_node.valid_to = max(tos)

        if descriptions:
            primary_node.description = "\n".join(descriptions)

        # 2. Re-route edges pointing to duplicate nodes to point to the primary node
        for edge in self.edges:
            if edge.source_id in cleaned_duplicate_ids:
                edge.source_id = primary_id
            if edge.target_id in cleaned_duplicate_ids:
                edge.target_id = primary_id

        # 3. Deduplicate re-routed edges
        unique_edges = {}
        edges_to_remove = []

        for edge in self.edges:
            # Key for edge uniqueness: (source, target, label, edge_type)
            key = (edge.source_id, edge.target_id, edge.label, edge.edge_type)
            
            if key not in unique_edges:
                unique_edges[key] = edge
            else:
                primary_edge = unique_edges[key]
                # Merge metadata
                for k, v in edge.metadata.items():
                    if k not in primary_edge.metadata:
                        primary_edge.metadata[k] = v
                
                # Merge temporal bounds
                froms = [v for v in [primary_edge.valid_from, edge.valid_from] if v is not None]
                if froms:
                    primary_edge.valid_from = min(froms)
                tos = [v for v in [primary_edge.valid_to, edge.valid_to] if v is not None]
                if tos:
                    primary_edge.valid_to = max(tos)

                edges_to_remove.append(edge)

        # Remove duplicate edges and the merged duplicate nodes
        self.edges = [e for e in self.edges if e not in edges_to_remove]
        self.nodes = [n for n in self.nodes if n.id not in cleaned_duplicate_ids]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "direction": self.direction,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Graph":
        g = cls(name=d.get("name", "Untitled"), direction=d.get("direction", "TD"))
        for nd in d.get("nodes", []):
            g.nodes.append(Node.from_dict(nd))
        for ed in d.get("edges", []):
            g.edges.append(Edge.from_dict(ed))
        return g

    def save_json(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)

    @classmethod
    def load_json(cls, filepath: str) -> "Graph":
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
