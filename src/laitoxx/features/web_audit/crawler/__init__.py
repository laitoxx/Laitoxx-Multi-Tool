"""Structured website crawler feature."""

from __future__ import annotations

import json

from .models import CrawlConfig, CrawlPage, CrawlReport
from .service import WebCrawlerService, crawl_website


def web_crawler(value: str | dict | None = None) -> dict:
    """Run a bounded crawl and print its structured report."""

    config = (
        CrawlConfig(**value)
        if isinstance(value, dict)
        else CrawlConfig(
            seed_url=str(value or input()).strip(),
        )
    )
    data = crawl_website(config).to_dict()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


__all__ = [
    "CrawlConfig",
    "CrawlPage",
    "CrawlReport",
    "WebCrawlerService",
    "crawl_website",
    "web_crawler",
]
