"""Data models for the structured website crawler."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from laitoxx.shared.execution import OperationIssue


@dataclass(frozen=True)
class CrawlConfig:
    """Resource and scope limits for one crawl."""

    seed_url: str
    max_pages: int = 200
    max_depth: int = 4
    concurrency: int = 8
    request_delay: float = 0.05
    timeout: float = 10.0
    scope: str = "host"
    query_policy: str = "sort"
    respect_robots: bool = True
    use_sitemap: bool = True
    max_response_bytes: int = 2_000_000
    max_redirects: int = 5
    allowed_content_types: tuple[str, ...] = ("text/html", "application/xhtml+xml")

    def validated(self) -> CrawlConfig:
        if self.scope not in {"host", "subdomains"}:
            raise ValueError("Scope must be host or subdomains")
        if self.query_policy not in {"drop", "sort", "keep"}:
            raise ValueError("Query policy must be drop, sort or keep")
        if not 1 <= self.max_pages <= 10000:
            raise ValueError("Maximum pages must be between 1 and 10000")
        if not 0 <= self.max_depth <= 50:
            raise ValueError("Maximum depth must be between 0 and 50")
        if not 1 <= self.concurrency <= 50:
            raise ValueError("Concurrency must be between 1 and 50")
        if not 1 <= self.timeout <= 120:
            raise ValueError("Timeout must be between 1 and 120 seconds")
        if not self.allowed_content_types:
            raise ValueError("At least one content type must be allowed")
        return self


@dataclass
class CrawlForm:
    """One HTML form discovered on a page."""

    action: str
    method: str
    fields: list[dict[str, str]] = field(default_factory=list)


@dataclass
class CrawlPage:
    """Observed state for one requested page."""

    url: str
    depth: int
    parent_url: str = ""
    final_url: str = ""
    status: int | None = None
    title: str = ""
    description: str = ""
    content_type: str = ""
    content_length: int = 0
    response_ms: float = 0.0
    canonical_url: str = ""
    redirect_chain: list[str] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    forms: list[CrawlForm] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    security_headers: dict[str, str] = field(default_factory=dict)
    missing_security_headers: list[str] = field(default_factory=list)
    blocked_by_robots: bool = False
    truncated: bool = False
    error: str = ""

    @property
    def broken(self) -> bool:
        return self.status is not None and self.status >= 400

    def to_dict(self) -> dict:
        data = asdict(self)
        data["broken"] = self.broken
        return data


@dataclass
class CrawlReport:
    """Complete structured crawl report."""

    seed_url: str
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str = ""
    pages: list[CrawlPage] = field(default_factory=list)
    issues: list[OperationIssue] = field(default_factory=list)
    cancelled: bool = False
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        external_domains = sorted(
            {
                link.split("/", 3)[2].casefold()
                for page in self.pages
                for link in page.external_links
                if link.startswith(("http://", "https://"))
            }
        )
        return {
            "seed_url": self.seed_url,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cancelled": self.cancelled,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "summary": {
                "pages": len(self.pages),
                "successful": sum(
                    page.status is not None and page.status < 400 and not page.error for page in self.pages
                ),
                "broken": sum(page.broken for page in self.pages),
                "errors": sum(bool(page.error) for page in self.pages),
                "forms": sum(len(page.forms) for page in self.pages),
                "external_domains": len(external_domains),
            },
            "external_domains": external_domains,
            "pages": [page.to_dict() for page in self.pages],
            "issues": [issue.to_dict() for issue in self.issues],
        }
