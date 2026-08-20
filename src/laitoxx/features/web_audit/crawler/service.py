"""Concurrent, scope aware website crawler service."""

from __future__ import annotations

import threading
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from urllib.parse import urlsplit

import requests

from laitoxx.shared.execution import (
    JobControl,
    OperationCancelled,
    OperationIssue,
    ProgressCallback,
    ProgressEvent,
    emit_progress,
)

from .models import CrawlConfig, CrawlPage, CrawlReport
from .parser import parse_html
from .url_policy import CrawlScope, normalize_url

_USER_AGENT = "Laitoxx-Web-Crawler/2.0"
_HTML_TYPES = ("text/html", "application/xhtml+xml")


class WebCrawlerService:
    """Execute one bounded crawl and return a structured report."""

    def __init__(
        self,
        config: CrawlConfig,
        progress: ProgressCallback | None = None,
        control: JobControl | None = None,
        page_callback: Callable[[CrawlPage], None] | None = None,
    ) -> None:
        self.config = config.validated()
        self.progress = progress
        self.control = control or JobControl()
        self.page_callback = page_callback
        seed = normalize_url(config.seed_url, query_policy=config.query_policy)
        if not seed:
            raise ValueError("Enter a valid HTTP or HTTPS URL")
        self.seed_url = seed
        self.scope = CrawlScope(seed, config.scope)
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._robots_lock = threading.Lock()

    def _new_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml,*/*;q=0.5"})
        return session

    def _read_bounded(self, response: requests.Response) -> tuple[bytes, bool]:
        chunks: list[bytes] = []
        total = 0
        truncated = False
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            remaining = self.config.max_response_bytes - total
            if remaining <= 0:
                truncated = True
                break
            chunks.append(chunk[:remaining])
            total += min(len(chunk), remaining)
            if len(chunk) > remaining:
                truncated = True
                break
        return b"".join(chunks), truncated

    def _robots_parser(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        with self._robots_lock:
            if origin in self._robots:
                return self._robots[origin]
        parser = urllib.robotparser.RobotFileParser()
        try:
            with self._new_session() as session:
                response = session.get(f"{origin}/robots.txt", timeout=self.config.timeout)
                if response.status_code >= 400:
                    result = None
                else:
                    parser.set_url(response.url)
                    parser.parse(response.text.splitlines())
                    result = parser
        except requests.RequestException:
            result = None
        with self._robots_lock:
            self._robots[origin] = result
        return result

    def _allowed_by_robots(self, url: str) -> bool:
        if not self.config.respect_robots:
            return True
        parser = self._robots_parser(url)
        return True if parser is None else parser.can_fetch(_USER_AGENT, url)

    def _sitemap_urls(self) -> list[str]:
        if not self.config.use_sitemap:
            return []
        parsed = urlsplit(self.seed_url)
        candidates = [f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"]
        robots = self._robots_parser(self.seed_url)
        if robots is not None and robots.site_maps():
            candidates.extend(robots.site_maps() or [])
        found: list[str] = []
        visited_sitemaps: set[str] = set()

        def read_sitemap(sitemap_url: str, depth: int = 0) -> None:
            normalized_sitemap = normalize_url(sitemap_url, self.seed_url, self.config.query_policy)
            if (
                not normalized_sitemap
                or normalized_sitemap in visited_sitemaps
                or len(visited_sitemaps) >= 50
                or not self.scope.contains(normalized_sitemap)
                or depth > 2
                or len(found) >= self.config.max_pages
            ):
                return
            visited_sitemaps.add(normalized_sitemap)
            try:
                with self._new_session() as session:
                    response = session.get(normalized_sitemap, timeout=self.config.timeout, stream=True)
                    response.raise_for_status()
                    content, _ = self._read_bounded(response)
                root = ET.fromstring(content)
            except (requests.RequestException, ET.ParseError, ValueError):
                return
            root_kind = root.tag.rsplit("}", 1)[-1].casefold()
            locations = [
                element.text.strip()
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1].casefold() == "loc" and element.text
            ]
            if root_kind == "sitemapindex":
                for location in locations[:50]:
                    read_sitemap(location, depth + 1)
                return
            for location in locations:
                normalized = normalize_url(location, self.seed_url, self.config.query_policy)
                if normalized and self.scope.contains(normalized) and normalized not in found:
                    found.append(normalized)
                if len(found) >= self.config.max_pages:
                    break

        for candidate in dict.fromkeys(candidates):
            read_sitemap(candidate)
        return found

    def _fetch_page(self, url: str, depth: int, parent_url: str) -> CrawlPage:
        self.control.checkpoint()
        page = CrawlPage(url=url, depth=depth, parent_url=parent_url)
        if not self._allowed_by_robots(url):
            page.blocked_by_robots = True
            page.error = "Blocked by robots.txt"
            return page
        if self.config.request_delay:
            time.sleep(self.config.request_delay)
        started = time.perf_counter()
        current = url
        try:
            with self._new_session() as session:
                for _ in range(self.config.max_redirects + 1):
                    self.control.checkpoint()
                    response = session.get(
                        current,
                        timeout=self.config.timeout,
                        allow_redirects=False,
                        stream=True,
                    )
                    if 300 <= response.status_code < 400 and response.headers.get("Location"):
                        target = normalize_url(
                            response.headers["Location"],
                            current,
                            self.config.query_policy,
                        )
                        response.close()
                        if not target:
                            page.error = "Redirect target is not a valid HTTP URL"
                            break
                        page.redirect_chain.append(target)
                        if not self.scope.contains(target):
                            page.status = response.status_code
                            page.final_url = target
                            page.error = "Redirect left the selected crawl scope"
                            break
                        current = target
                        continue
                    page.status = response.status_code
                    page.final_url = normalize_url(response.url, query_policy=self.config.query_policy) or current
                    page.content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
                    if page.content_type and not any(
                        page.content_type.startswith(allowed) for allowed in self.config.allowed_content_types
                    ):
                        advertised = response.headers.get("Content-Length", "")
                        page.content_length = int(advertised) if advertised.isdigit() else 0
                        response.close()
                        break
                    content, page.truncated = self._read_bounded(response)
                    page.content_length = len(content)
                    encoding = response.encoding or "utf-8"
                    headers = dict(response.headers)
                    response.close()
                    if page.content_type.startswith(_HTML_TYPES):
                        extracted = parse_html(content.decode(encoding, errors="replace"), page.final_url, headers)
                        for key, value in extracted.items():
                            if key != "raw_links":
                                setattr(page, key, value)
                        internal: set[str] = set()
                        external: set[str] = set()
                        for raw_link in extracted["raw_links"]:
                            normalized = normalize_url(raw_link, page.final_url, self.config.query_policy)
                            if not normalized:
                                continue
                            (internal if self.scope.contains(normalized) else external).add(normalized)
                        page.internal_links = sorted(internal)
                        page.external_links = sorted(external)
                    break
                else:
                    page.error = "Redirect limit exceeded"
        except OperationCancelled:
            raise
        except requests.Timeout:
            page.error = "Request timed out"
        except requests.RequestException as error:
            page.error = str(error)
        except Exception as error:
            page.error = f"Parser error: {error}"
        page.response_ms = (time.perf_counter() - started) * 1000
        return page

    def run(self) -> CrawlReport:
        """Run the crawl until the queue, limit or cancellation ends it."""

        started = time.monotonic()
        report = CrawlReport(seed_url=self.seed_url)
        queue: deque[tuple[str, int, str]] = deque([(self.seed_url, 0, "")])
        queued = {self.seed_url}
        completed_urls: set[str] = set()
        try:
            self.control.checkpoint()
            for sitemap_url in self._sitemap_urls():
                if sitemap_url not in queued and len(queued) < self.config.max_pages:
                    queue.append((sitemap_url, 0, self.seed_url))
                    queued.add(sitemap_url)
            emit_progress(self.progress, ProgressEvent("crawl", 0, self.config.max_pages, "Crawl started"))
            with ThreadPoolExecutor(max_workers=self.config.concurrency, thread_name_prefix="web-crawler") as executor:
                while queue and len(report.pages) < self.config.max_pages:
                    self.control.checkpoint()
                    remaining = self.config.max_pages - len(report.pages)
                    batch_size = min(self.config.concurrency, remaining, len(queue))
                    batch = []
                    while queue and len(batch) < batch_size:
                        candidate = queue.popleft()
                        if candidate[0] not in completed_urls:
                            batch.append(candidate)
                    if not batch:
                        continue
                    futures = {
                        executor.submit(self._fetch_page, url, depth, parent): (url, depth, parent)
                        for url, depth, parent in batch
                    }
                    for future in as_completed(futures):
                        self.control.checkpoint()
                        try:
                            page = future.result()
                        except OperationCancelled:
                            raise
                        except Exception as error:
                            url, depth, parent = futures[future]
                            page = CrawlPage(url=url, depth=depth, parent_url=parent, error=str(error))
                        report.pages.append(page)
                        completed_urls.add(page.url)
                        if page.final_url:
                            completed_urls.add(page.final_url)
                        canonical = normalize_url(
                            page.canonical_url,
                            page.final_url or page.url,
                            self.config.query_policy,
                        )
                        if canonical and self.scope.contains(canonical):
                            completed_urls.add(canonical)
                        if self.page_callback is not None:
                            try:
                                self.page_callback(page)
                            except Exception:
                                pass
                        if page.depth < self.config.max_depth and not page.error:
                            for link in page.internal_links:
                                if link not in queued and len(queued) < self.config.max_pages * 4:
                                    queue.append((link, page.depth + 1, page.final_url or page.url))
                                    queued.add(link)
                        emit_progress(
                            self.progress,
                            ProgressEvent(
                                "crawl",
                                len(report.pages),
                                self.config.max_pages,
                                f"Queue: {len(queue)}",
                                page.url,
                            ),
                        )
        except OperationCancelled:
            report.cancelled = True
        except Exception as error:
            report.issues.append(OperationIssue("crawler", str(error), "crawl_error", False))
        report.pages.sort(key=lambda page: (page.depth, page.url))
        report.elapsed_seconds = time.monotonic() - started
        report.finished_at = datetime.now(UTC).isoformat()
        emit_progress(
            self.progress,
            ProgressEvent("complete", len(report.pages), len(report.pages), "Crawl complete"),
        )
        return report


def crawl_website(
    config: CrawlConfig,
    progress: ProgressCallback | None = None,
    control: JobControl | None = None,
    page_callback: Callable[[CrawlPage], None] | None = None,
) -> CrawlReport:
    """Convenience entry point for a single structured crawl."""

    return WebCrawlerService(
        config,
        progress=progress,
        control=control,
        page_callback=page_callback,
    ).run()
