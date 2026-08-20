"""Run controlled local regressions for web and username OSINT services."""

from __future__ import annotations

import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from laitoxx.features.osint.username_osint.checker import UsernameChecker
from laitoxx.features.osint.username_osint.models import SiteEntry
from laitoxx.features.web_audit import subdomain_discovery as subdomains
from laitoxx.features.web_audit.crawler import CrawlConfig, crawl_website
from laitoxx.shared.execution import JobControl


class _FixtureHandler(BaseHTTPRequestHandler):
    requests_seen: list[str] = []

    def do_GET(self) -> None:
        self.requests_seen.append(self.path)
        if self.path == "/robots.txt":
            return self._send(200, b"User-agent: *\nDisallow: /blocked\n", "text/plain")
        if self.path == "/sitemap.xml":
            location = f"http://127.0.0.1:{self.server.server_port}/from-sitemap"
            return self._send(200, f"<urlset><url><loc>{location}</loc></url></urlset>".encode(), "application/xml")
        if self.path.startswith("/rate/"):
            return self._send(429, b"rate limited")
        if self.path.startswith("/profile/"):
            username = self.path.rsplit("/", 1)[-1]
            if username == "alice":
                return self._send(200, b"<title>alice profile</title><h1>alice</h1>")
            return self._send(404, b"<title>User not found</title>")
        if self.path == "/blocked":
            return self._send(200, b"This endpoint must not be requested")
        if self.path == "/external-redirect":
            self.send_response(302)
            self.send_header("Location", "https://outside.invalid/path")
            self.end_headers()
            return
        if self.path == "/broken":
            return self._send(404, b"<title>Missing</title>")
        if self.path == "/":
            body = b"""<title>Home</title><a href='/page?utm_source=x&amp;id=2'>Page</a>
            <a href='/blocked'>Blocked</a><a href='/broken'>Broken</a>
            <a href='/external-redirect'>Redirect</a><form action='/submit' method='post'>
            <input name='email' type='email'></form>test@example.com"""
            return self._send(200, body)
        return self._send(200, f"<title>{self.path}</title>".encode())

    def _send(self, status: int, body: bytes, content_type: str = "text/html") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


def _run() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        report = crawl_website(
            CrawlConfig(
                seed_url=origin,
                max_pages=20,
                max_depth=2,
                concurrency=3,
                request_delay=0,
                timeout=2,
            )
        )
        root = next(page for page in report.pages if page.url == origin + "/")
        assert any("/page?id=2" in link for link in root.internal_links)
        assert root.forms and root.emails == ["test@example.com"]
        assert "/blocked" not in _FixtureHandler.requests_seen
        assert any(page.broken for page in report.pages)
        redirect = next(page for page in report.pages if page.url.endswith("/external-redirect"))
        assert redirect.error == "Redirect left the selected crawl scope"

        control = JobControl()
        control.cancel()
        cancelled = crawl_website(CrawlConfig(seed_url=origin), control=control)
        assert cancelled.cancelled and not cancelled.pages

        sites = [
            SiteEntry(name="Profile", url_template=origin + "/profile/{username}", category="social", timeout=2),
            SiteEntry(name="Limited", url_template=origin + "/rate/{username}", category="social", timeout=2),
        ]
        results = UsernameChecker(sites, max_workers=2, max_retries=2).check_username("alice")
        by_name = {result.site_name: result for result in results}
        assert by_name["Profile"].status == "confirmed" and by_name["Profile"].evidence
        assert by_name["Limited"].status == "rate_limited"

        unsupported = SiteEntry(
            name="PostOnly",
            url_template="http://127.0.0.1:1/{username}",
            category="other",
            request_method="POST",
        )
        unsupported_result = UsernameChecker([unsupported], max_workers=1).check_username("alice")[0]
        assert unsupported_result.status == "unsupported" and unsupported_result.http_code is None

        rows = [{"common_name": "*.api.example.com", "name_value": "www.example.com\noutside.test"}]
        records = subdomains._records_from_rows(rows, "example.com", 20)
        assert [record.hostname for record in records] == ["api.example.com", "www.example.com"]
        assert records[0].wildcard_observed

        control = JobControl()
        dns_calls: list[tuple[str, str]] = []

        def slow_dns(host: str, record_type: str, _timeout: float) -> list[str]:
            dns_calls.append((host, record_type))
            time.sleep(0.08)
            return []

        def cancel_discovery() -> None:
            time.sleep(0.02)
            control.cancel()

        many_rows = [{"name_value": "\n".join(f"host{i}.example.com" for i in range(12))}]
        threading.Thread(target=cancel_discovery, daemon=True).start()
        with (
            patch.object(subdomains, "_load_cache", return_value=many_rows),
            patch.object(subdomains, "query_dns", side_effect=slow_dns),
        ):
            discovery = subdomains.discover_subdomains(
                "example.com",
                subdomains.SubdomainDiscoveryConfig(max_workers=1, probe_http=False),
                control=control,
            )
        assert discovery.cancelled and len(dns_calls) == 1
    finally:
        server.shutdown()
        server.server_close()
    print("Controlled web and username runtime audit passed")


if __name__ == "__main__":
    _run()
