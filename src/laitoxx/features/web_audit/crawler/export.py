"""Export adapters for crawler reports."""

from __future__ import annotations

import html
from pathlib import Path

from laitoxx.shared.report_export import write_csv_rows, write_json_report

from .models import CrawlReport


def export_crawl_report(report: CrawlReport, path: str | Path) -> Path:
    """Export a crawler report based on the destination extension."""

    destination = Path(path)
    suffix = destination.suffix.casefold()
    if suffix == ".csv":
        fields = [
            "url",
            "final_url",
            "status",
            "depth",
            "title",
            "content_type",
            "content_length",
            "response_ms",
            "parent_url",
            "canonical_url",
            "error",
        ]
        return write_csv_rows(destination, fields, (page.to_dict() for page in report.pages))
    if suffix == ".html":
        rows = []
        for page in report.pages:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(page.status or ''))}</td>"
                f"<td>{page.depth}</td>"
                f'<td><a href="{html.escape(page.final_url or page.url, quote=True)}">{html.escape(page.url)}</a></td>'
                f"<td>{html.escape(page.title)}</td>"
                f"<td>{html.escape(page.error)}</td>"
                "</tr>"
            )
        document = (
            '<!doctype html><meta charset="utf-8"><title>Crawl Report</title>'
            "<style>body{font-family:sans-serif;background:#111;color:#ddd}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #444;padding:6px;text-align:left}a{color:#7cc7ff}</style>"
            f"<h1>Crawl Report</h1><p>{html.escape(report.seed_url)}</p>"
            "<table><thead><tr><th>Status</th><th>Depth</th><th>URL</th><th>Title</th><th>Error</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        return destination
    return write_json_report(destination, report.to_dict())
