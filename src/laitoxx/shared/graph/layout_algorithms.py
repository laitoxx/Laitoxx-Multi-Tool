"""
algorithms.py - NetworkX-based graph algorithms for the Laitoxx Graph Editor.
Provides shortest path finding and node centrality calculations.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from laitoxx.shared.graph.model import Graph


def calculate_cluster_layout(
    graph: Graph,
    root_id: str | None = None,
    *,
    max_nodes: int = 260,
    max_edges: int = 520,
    communities: list[set[str]] | None = None,
) -> dict[str, tuple[float, float]]:
    """Return a deterministic, community-aware layout for dense OSINT graphs.

    A single force-directed plane becomes unreadable once a target has dozens
    of pivots.  This layout first detects communities, places each community in
    its own visual sector and only then applies a local spring layout.  The
    investigation target remains at the origin.
    """
    network = _network_from_graph(graph, max_nodes=max_nodes, max_edges=max_edges)
    if not network:
        return {}
    if len(network) == 1:
        return {next(iter(network)): (0.0, 0.0)}
    root = (
        root_id
        if root_id in network
        else max(
            network,
            key=lambda identifier: (network.degree(identifier), identifier),
        )
    )
    if communities is None:
        communities = _detect_network_communities(
            network,
            graph,
            root_id=root,
            max_nodes=max_nodes,
        )
    else:
        communities = [set(community) for community in communities]
    root_index = next(
        (index for index, community in enumerate(communities) if root in community),
        0,
    )
    if root_index:
        communities.insert(0, communities.pop(root_index))

    positions: dict[str, list[float]] = {}
    for index, community in enumerate(communities):
        members = sorted(community)
        if index == 0:
            centre = (0.0, 0.0)
        else:
            ring = 0
            preceding = index - 1
            while preceding >= 6 + ring * 4:
                preceding -= 6 + ring * 4
                ring += 1
            capacity = 6 + ring * 4
            angle = -math.pi / 2 + (2 * math.pi * preceding / capacity)
            radius = 520.0 + ring * 430.0
            centre = (math.cos(angle) * radius, math.sin(angle) * radius)

        if len(members) == 1:
            positions[members[0]] = [centre[0], centre[1]]
            continue
        local = network.subgraph(members)
        local_scale = max(105.0, min(270.0, 41.0 * math.sqrt(len(members))))
        raw = nx.spring_layout(
            local,
            seed=42,
            iterations=80 if len(members) <= 40 else 55,
            scale=local_scale,
            weight="weight",
        )
        if index == 0 and root in raw:
            offset_x, offset_y = map(float, raw[root])
        else:
            offset_x = sum(float(point[0]) for point in raw.values()) / len(raw)
            offset_y = sum(float(point[1]) for point in raw.values()) / len(raw)
        for identifier, point in raw.items():
            positions[identifier] = [
                centre[0] + float(point[0]) - offset_x,
                centre[1] + float(point[1]) - offset_y,
            ]
        _relax_community(positions, members, fixed=root if index == 0 else None)

    positions[root] = [0.0, 0.0]
    return {identifier: (point[0], point[1]) for identifier, point in positions.items()}


def _network_from_graph(graph: Graph, *, max_nodes: int, max_edges: int) -> nx.Graph:
    identifiers = sorted(node.id for node in graph.nodes[:max_nodes])
    node_ids = set(identifiers)
    network = nx.Graph()
    network.add_nodes_from(identifiers)
    for edge in graph.edges[:max_edges]:
        if edge.source_id not in node_ids or edge.target_id not in node_ids:
            continue
        if edge.source_id == edge.target_id:
            continue
        if network.has_edge(edge.source_id, edge.target_id):
            network[edge.source_id][edge.target_id]["weight"] += 1.0
        else:
            network.add_edge(edge.source_id, edge.target_id, weight=1.0)
    return network


def detect_graph_communities(
    graph: Graph,
    root_id: str | None = None,
    *,
    max_nodes: int = 260,
    max_edges: int = 520,
) -> list[set[str]]:
    """Detect stable visual communities, including sensible star fallbacks."""
    network = _network_from_graph(graph, max_nodes=max_nodes, max_edges=max_edges)
    return _detect_network_communities(
        network,
        graph,
        root_id=root_id,
        max_nodes=max_nodes,
    )


def _detect_network_communities(
    network: nx.Graph,
    graph: Graph,
    *,
    root_id: str | None,
    max_nodes: int,
) -> list[set[str]]:
    """Detect communities in an already materialised NetworkX graph."""
    if not network:
        return []
    root = root_id if root_id in network else None
    node_types = {node.id: node.node_type for node in graph.nodes[:max_nodes]}
    isolated = set(nx.isolates(network))
    communities: list[set[str]] = []
    for component in sorted(
        (set(value) for value in nx.connected_components(network) if not set(value) <= isolated),
        key=lambda value: (-len(value), min(value)),
    ):
        subgraph = network.subgraph(component)
        if len(component) <= 3:
            found = [component]
        else:
            try:
                found = [
                    set(value)
                    for value in nx.community.louvain_communities(
                        subgraph,
                        weight="weight",
                        resolution=1.18,
                        seed=42,
                    )
                ]
            except (AttributeError, nx.NetworkXException, ZeroDivisionError):
                found = [set(value) for value in nx.community.greedy_modularity_communities(subgraph)]
        # Stars and near-stars have no useful modularity split.  Separate their
        # leaves into bounded visual groups without claiming semantic identity.
        dominant_hub = max(dict(subgraph.degree()).values(), default=0) >= (len(component) - 1) * 0.55
        if len(component) > 20 and (len(found) == 1 or dominant_hub):
            anchor = (
                root
                if root in component
                else max(
                    component,
                    key=lambda identifier: (subgraph.degree(identifier), identifier),
                )
            )
            buckets: dict[str, list[str]] = {}
            for identifier in sorted(component - {anchor}):
                buckets.setdefault(node_types.get(identifier, "Other"), []).append(identifier)
            found = [{anchor}]
            for node_type in sorted(buckets):
                values = buckets[node_type]
                found.extend(set(values[index : index + 18]) for index in range(0, len(values), 18))
        communities.extend(found)

    isolated_buckets: dict[str, list[str]] = {}
    for identifier in sorted(isolated):
        isolated_buckets.setdefault(node_types.get(identifier, "Other"), []).append(identifier)
    for node_type in sorted(isolated_buckets):
        values = isolated_buckets[node_type]
        communities.extend(set(values[index : index + 18]) for index in range(0, len(values), 18))
    communities.sort(key=lambda value: (0 if root in value else 1, -len(value), min(value)))
    return communities


def _relax_community(
    positions: dict[str, list[float]],
    identifiers: list[str],
    *,
    fixed: str | None,
) -> None:
    """Provide enough room for native nodes and their labels."""
    minimum_distance = 68.0
    for _ in range(7):
        moved = False
        for index, left in enumerate(identifiers):
            for right in identifiers[index + 1 :]:
                dx = positions[right][0] - positions[left][0]
                dy = positions[right][1] - positions[left][1]
                distance = math.hypot(dx, dy)
                if distance >= minimum_distance:
                    continue
                if distance < 1e-6:
                    dx, dy, distance = 1.0, 0.0, 1.0
                push = (minimum_distance - distance) / 2
                ux, uy = dx / distance, dy / distance
                if left != fixed:
                    positions[left][0] -= ux * push
                    positions[left][1] -= uy * push
                if right != fixed:
                    positions[right][0] += ux * push
                    positions[right][1] += uy * push
                moved = True
        if not moved:
            return
