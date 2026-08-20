"""Node, edge, and graph domain models."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from . import schema as _schema

EDGE_LINE_TYPES = _schema.EDGE_LINE_TYPES
EDGE_TYPES = _schema.EDGE_TYPES
NODE_SHAPES = _schema.NODE_SHAPES
NODE_TYPE_DEFAULTS = _schema.NODE_TYPE_DEFAULTS
NODE_TYPES = _schema.NODE_TYPES
SHAPE_ID_TO_TOKENS = _schema.SHAPE_ID_TO_TOKENS


@dataclass
class Node:
    label: str
    node_type: str = "Custom"
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    # Mermaid display
    mermaid_shape: str = "[]"  # e.g. "[]", "()", "(())", "{}"
    mermaid_style: str = ""  # CSS style string
    # Internal
    id: str = field(default_factory=lambda: f"N{uuid.uuid4().hex[:6].upper()}")
    # Temporal fields
    valid_from: str | None = None
    valid_to: str | None = None

    @classmethod
    def from_type(cls, label: str, node_type: str = "Custom") -> Node:
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
    def from_dict(cls, d: dict) -> Node:
        n = cls(
            label=d.get("label", ""),
            node_type=d.get("node_type", "Custom"),
            description=d.get("description", ""),
            metadata=d.get("metadata", {}),
            mermaid_shape=d.get("mermaid_shape", "[]"),
            mermaid_style=d.get("mermaid_style", ""),
            valid_from=d.get("valid_from"),
            valid_to=d.get("valid_to"),
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
    mermaid_line: str = "-->"  # e.g. "-->", "==>", "-.->", "---"
    mermaid_style: str = ""  # linkStyle CSS string
    # Internal
    id: str = field(default_factory=lambda: f"E{uuid.uuid4().hex[:6].upper()}")
    # Temporal fields
    valid_from: str | None = None
    valid_to: str | None = None

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
    def from_dict(cls, d: dict) -> Edge:
        e = cls(
            source_id=d.get("source_id", ""),
            target_id=d.get("target_id", ""),
            label=d.get("label", ""),
            edge_type=d.get("edge_type", "Connected"),
            metadata=d.get("metadata", {}),
            mermaid_line=d.get("mermaid_line", "-->"),
            mermaid_style=d.get("mermaid_style", ""),
            valid_from=d.get("valid_from"),
            valid_to=d.get("valid_to"),
        )
        e.id = d.get("id", e.id)
        return e


class Graph:
    def __init__(self, name: str = "Untitled Graph", direction: str = "TD"):
        self.name = name
        self.direction = direction  # TD / LR / RL / BT
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
        self.edges = [e for e in self.edges if e.source_id != node_id and e.target_id != node_id]

    def get_node(self, node_id: str) -> Node | None:
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

    def get_edge(self, edge_id: str) -> Edge | None:
        return next((e for e in self.edges if e.id == edge_id), None)

    def merge_nodes(self, primary_id: str, duplicate_ids: list[str]) -> None:
        """
        Merge duplicate nodes into the primary node.
        Combines descriptions, merges metadata, aggregates temporal ranges,
        re-routes edges, and removes duplicates.
        """
        primary_node = self.get_node(primary_id)
        if not primary_node:
            raise ValueError(f"Primary node with ID '{primary_id}' not found.")

        # 1. Filter out duplicate IDs that don't exist or are the primary itself
        valid_dup_ids = [d_id for d_id in duplicate_ids if d_id != primary_id and self.get_node(d_id) is not None]

        # 2. Gather descriptions, metadata, and dates
        descriptions = [primary_node.description] if primary_node.description else []

        def merge_dates(d1: str | None, d2: str | None, op_type: str) -> str | None:
            if not d1:
                return d2
            if not d2:
                return d1
            if op_type == "min":
                return min(d1, d2)
            else:
                return max(d1, d2)

        for d_id in valid_dup_ids:
            dup_node = self.get_node(d_id)
            if not dup_node:
                continue

            # Merge description
            if dup_node.description and dup_node.description not in descriptions:
                descriptions.append(dup_node.description)

            # Merge metadata
            for k, v in dup_node.metadata.items():
                if k not in primary_node.metadata:
                    primary_node.metadata[k] = v
                else:
                    curr_val = primary_node.metadata[k]
                    if curr_val != v:
                        curr_list = [x.strip() for x in curr_val.split(",") if x.strip()]
                        new_list = [x.strip() for x in v.split(",") if x.strip()]
                        for item in new_list:
                            if item not in curr_list:
                                curr_list.append(item)
                        primary_node.metadata[k] = ", ".join(curr_list)

            # Merge temporal bounds
            primary_node.valid_from = merge_dates(primary_node.valid_from, dup_node.valid_from, "min")
            primary_node.valid_to = merge_dates(primary_node.valid_to, dup_node.valid_to, "max")

        primary_node.description = " | ".join(descriptions)

        # 3. Re-route edges and prepare for deduplication
        merged_node_ids = {primary_id} | set(valid_dup_ids)
        connected_edges: list[Edge] = []
        unrelated_edges: list[Edge] = []

        for edge in self.edges:
            if edge.source_id in merged_node_ids or edge.target_id in merged_node_ids:
                connected_edges.append(edge)
            else:
                unrelated_edges.append(edge)

        for edge in connected_edges:
            # Re-route source
            if edge.source_id in valid_dup_ids:
                edge.source_id = primary_id
            # Re-route target
            if edge.target_id in valid_dup_ids:
                edge.target_id = primary_id

        # Avoid self-loops for connected edges only
        connected_edges = [edge for edge in connected_edges if edge.source_id != edge.target_id]

        edge_groups: dict[tuple[str, str, str, str], list[Edge]] = {}
        for edge in connected_edges:
            key = (edge.source_id, edge.target_id, edge.edge_type, edge.label)
            if key not in edge_groups:
                edge_groups[key] = []
            edge_groups[key].append(edge)

        # Re-build the edges list by merging duplicate groups
        processed_connected_edges: list[Edge] = []
        for _key, group in edge_groups.items():
            representative = group[0]
            # Merge duplicate edges metadata and dates
            for other in group[1:]:
                for k, v in other.metadata.items():
                    if k not in representative.metadata:
                        representative.metadata[k] = v
                    else:
                        curr_val = representative.metadata[k]
                        if curr_val != v:
                            curr_list = [x.strip() for x in curr_val.split(",") if x.strip()]
                            new_list = [x.strip() for x in v.split(",") if x.strip()]
                            for item in new_list:
                                if item not in curr_list:
                                    curr_list.append(item)
                            representative.metadata[k] = ", ".join(curr_list)

                representative.valid_from = merge_dates(representative.valid_from, other.valid_from, "min")
                representative.valid_to = merge_dates(representative.valid_to, other.valid_to, "max")

            processed_connected_edges.append(representative)

        self.edges = unrelated_edges + processed_connected_edges

        # 4. Remove duplicate nodes
        self.nodes = [n for n in self.nodes if n.id not in valid_dup_ids]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "direction": self.direction,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Graph:
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
    def load_json(cls, filepath: str) -> Graph:
        with open(filepath, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
