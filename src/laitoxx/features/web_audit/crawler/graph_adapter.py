"""Graph adapter for structured crawler reports."""

from __future__ import annotations

from urllib.parse import urlsplit

from laitoxx.shared.graph.model import Edge, Graph, Node

from .models import CrawlReport


def build_crawl_graph(report: CrawlReport, max_pages: int = 300) -> Graph:
    """Create a bounded page and external domain relationship graph."""

    graph = Graph(name=f"Web Crawl: {urlsplit(report.seed_url).netloc}", direction="LR")
    root = Node.from_type(report.seed_url, "Website")
    root.description = "Crawl seed"
    graph.add_node(root)
    page_nodes: dict[str, Node] = {report.seed_url: root}
    for page in report.pages[:max_pages]:
        key = page.final_url or page.url
        node = page_nodes.get(key)
        if node is None:
            node = Node.from_type(page.title or key, "Website")
            node.description = key
            node.metadata = {"status": str(page.status or ""), "depth": str(page.depth), "error": page.error}
            page_nodes[key] = node
            graph.add_node(node)
        parent = page_nodes.get(page.parent_url) or root
        if parent.id != node.id:
            graph.add_edge(Edge(parent.id, node.id, label="link", edge_type="LinksTo", mermaid_line="-->"))
    external_nodes: dict[str, Node] = {}
    for page in report.pages[:max_pages]:
        source = page_nodes.get(page.final_url or page.url)
        if source is None:
            continue
        for link in page.external_links:
            domain = (urlsplit(link).hostname or "").casefold()
            if not domain:
                continue
            node = external_nodes.get(domain)
            if node is None:
                node = Node.from_type(domain, "Website")
                node.description = "External domain"
                external_nodes[domain] = node
                graph.add_node(node)
            graph.add_edge(Edge(source.id, node.id, label="external", edge_type="ExternalLink", mermaid_line="-.->"))
    return graph
