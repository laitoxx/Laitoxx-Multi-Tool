"""
Lua Plugin Engine for Laitoxx.

Uses `lupa` (LuaJIT/Lua runtime for Python) to execute Lua plugins
inside a sandboxed environment with a rich host API.
"""

import os
import uuid

from laitoxx.core.settings.paths import GRAPHS_DIR
from laitoxx.shared.graph.model import NODE_TYPE_DEFAULTS, Edge, Graph, Node

from .lua_values import _lua_str, _lua_table_to_dict, _python_to_lua


class GraphHostMixin:
    def graph_create(self, name=None, direction=None):
        """Create a new graph. Returns graph id (string)."""
        gid = f"G{uuid.uuid4().hex[:8]}"
        g = Graph(
            name=_lua_str(name) if name else f"Graph_{self._meta.id}",
            direction=_lua_str(direction) if direction else "TD",
        )
        if not hasattr(self, "_graphs"):
            self._graphs: dict[str, Graph] = {}
        self._graphs[gid] = g
        self._output(f"[Graph] Created graph '{g.name}' (id={gid})")
        return gid

    def graph_add_node(
        self,
        graph_id,
        label,
        node_type=None,
        shape=None,
        style=None,
        description=None,
        metadata_table=None,
    ):
        """Add a node to a graph. Returns node id."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        ntype = _lua_str(node_type) if node_type else "Custom"
        node = Node.from_type(_lua_str(label), ntype)

        if shape:
            node.mermaid_shape = _lua_str(shape)
        if style:
            node.mermaid_style = _lua_str(style)
        if description:
            node.description = _lua_str(description)
        if metadata_table:
            node.metadata = _lua_table_to_dict(metadata_table)

        g.add_node(node)
        return node.id

    def graph_add_edge(
        self,
        graph_id,
        source_id,
        target_id,
        label=None,
        edge_type=None,
        line_type=None,
        style=None,
        metadata_table=None,
    ):
        """Add an edge between two nodes. Returns edge id."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        edge = Edge(
            source_id=_lua_str(source_id),
            target_id=_lua_str(target_id),
            label=_lua_str(label) if label else "",
            edge_type=_lua_str(edge_type) if edge_type else "Connected",
            mermaid_line=_lua_str(line_type) if line_type else "-->",
            mermaid_style=_lua_str(style) if style else "",
        )
        if metadata_table:
            edge.metadata = _lua_table_to_dict(metadata_table)

        if not g.add_edge(edge):
            return None, "Source or target node not found"
        return edge.id

    def graph_find_node(self, graph_id, label):
        """Find a node by its label. Returns node id or nil."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        for n in g.nodes:
            if n.label == _lua_str(label):
                return n.id
        return None

    def graph_get_nodes(self, graph_id):
        """Return all node ids and labels as a Lua table."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        result = {}
        for i, n in enumerate(g.nodes, 1):
            result[i] = {"id": n.id, "label": n.label, "type": n.node_type}
        return _python_to_lua(self._lua, result)

    def graph_save(self, graph_id, filename=None):
        """Save the graph to the application graph directory. Returns filepath."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        if not filename:
            safe_name = g.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            filename = f"{safe_name}.graph.json"

        filename = os.path.basename(_lua_str(filename))
        plugin_dir = os.path.join(GRAPHS_DIR, "plugins", self._meta.id)
        filepath = os.path.join(plugin_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        g.save_json(filepath)
        self._output(f"[Graph] Saved → {filepath}")

        # Store path for the host to pick up
        if not hasattr(self, "_saved_graph_paths"):
            self._saved_graph_paths: list[str] = []
        self._saved_graph_paths.append(filepath)

        return filepath

    def graph_set_direction(self, graph_id, direction):
        """Set graph direction: TD, LR, RL, BT."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"
        g.direction = _lua_str(direction)
        return True

    def graph_node_set_style(self, graph_id, node_id, style):
        """Override the CSS style of a node."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        node = g.get_node(_lua_str(node_id))
        if node is None:
            return None
        node.mermaid_style = _lua_str(style)
        return True

    def graph_node_set_shape(self, graph_id, node_id, shape):
        """Override the shape of a node (rect, round, circle, diamond, hexagon)."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        node = g.get_node(_lua_str(node_id))
        if node is None:
            return None
        node.mermaid_shape = _lua_str(shape)
        return True

    def graph_get_node_types(self):
        """Return available node types and their default styles as a Lua table."""
        return _python_to_lua(self._lua, NODE_TYPE_DEFAULTS)

    def _get_graph(self, graph_id) -> Graph | None:
        if not hasattr(self, "_graphs"):
            return None
        return self._graphs.get(_lua_str(graph_id))
