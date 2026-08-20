"""Graph adapter for Domain Intelligence subdomain reports."""

from __future__ import annotations

from laitoxx.shared.graph.model import Edge, Graph, Node

from .subdomain_discovery import SubdomainDiscoveryReport


def build_subdomain_graph(report: SubdomainDiscoveryReport) -> Graph:
    """Convert a subdomain discovery report into graph entities."""

    graph = Graph(name=f"Domain Intelligence: {report.domain}", direction="LR")
    root = Node.from_type(report.domain, "Website")
    root.description = "Domain Intelligence target"
    graph.add_node(root)
    nodes: dict[tuple[str, str], Node] = {}
    for record in report.records:
        subdomain = Node.from_type(record.hostname, "Website")
        subdomain.description = ", ".join(record.sources)
        subdomain.metadata = {
            "resolves": str(record.resolves),
            "http_status": str(record.http_status or ""),
            "http_url": record.http_url,
        }
        graph.add_node(subdomain)
        graph.add_edge(Edge(root.id, subdomain.id, label="subdomain", edge_type="SubdomainOf", mermaid_line="-->"))
        for address in [*record.ipv4, *record.ipv6]:
            key = ("IP", address)
            node = nodes.get(key)
            if node is None:
                node = Node.from_type(address, "IP")
                nodes[key] = node
                graph.add_node(node)
            graph.add_edge(Edge(subdomain.id, node.id, label="resolves", edge_type="ResolvesTo", mermaid_line="-->"))
        for cname in record.cname:
            key = ("Website", cname)
            node = nodes.get(key)
            if node is None:
                node = Node.from_type(cname, "Website")
                nodes[key] = node
                graph.add_node(node)
            graph.add_edge(Edge(subdomain.id, node.id, label="CNAME", edge_type="CnameTo", mermaid_line="-.->"))
    return graph
