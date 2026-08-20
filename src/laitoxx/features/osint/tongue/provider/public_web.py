"""Bounded client and parser for public collectible web pages."""

from __future__ import annotations

import html
import os
import random
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import requests

from laitoxx.core.settings.network_manager import get_session

from ..domain.primitives import stable_id, utc_now_iso
from .toncenter import OperationCancelled


class PublicPageParser(HTMLParser):
    """Small dependency-free HTML extractor for public collectible pages."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.text_parts: list[str] = []
        self.scripts: list[str] = []
        self._in_script = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "meta":
            key = (data.get("property") or data.get("name") or "").lower()
            value = data.get("content", "").strip()
            if key and value:
                self.meta[key] = value
        elif tag == "a" and data.get("href"):
            self.links.append(data["href"].strip())
        elif tag == "link" and data.get("href"):
            rel = data.get("rel", "").lower()
            if "canonical" in rel:
                self.meta["canonical"] = data["href"].strip()
            self.links.append(data["href"].strip())
        elif tag == "script":
            self._in_script = True
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_script:
            self._in_script = False
            text = "".join(self._script_parts).strip()
            if text and len(text) <= 2_000_000:
                self.scripts.append(text)
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data or "").strip()
        if not text:
            return
        if self._in_script:
            self._script_parts.append(data)
        elif len(text) <= 2000:
            self.text_parts.append(text)


class PublicWebError(RuntimeError):
    pass


class PublicWebClient:
    def __init__(
        self,
        timeout: float = 30.0,
        raw_dir: Path | None = None,
        min_interval: float = 0.55,
        max_retries: int = 4,
        max_bytes: int = 5_000_000,
        cancel_check=None,
    ) -> None:
        self.timeout = timeout
        self.raw_dir = raw_dir
        self.min_interval = max(0.0, min_interval)
        self.max_retries = max(1, max_retries)
        self.max_bytes = max_bytes
        self.cancel_check = cancel_check
        self._last_request_at = 0.0
        self.session = get_session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; TON-Public-Correlator/0.5)",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,*/*;q=0.5",
        }

    def close(self) -> None:
        return None

    def _throttle(self) -> None:
        if self.cancel_check and self.cancel_check():
            raise OperationCancelled("TONgue investigation cancelled")
        delay = self.min_interval - (time.monotonic() - self._last_request_at)
        if delay > 0:
            time.sleep(delay)

    def get_text(self, url: str) -> tuple[str, str, int]:
        last_error: Exception | None = None
        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=True,
                )
                self._last_request_at = time.monotonic()
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt == self.max_retries:
                        raise PublicWebError(f"HTTP {response.status_code} for {url}")
                    time.sleep(backoff + random.random() * 0.2)
                    backoff = min(backoff * 2, 12)
                    continue
                if response.status_code >= 400:
                    raise PublicWebError(f"HTTP {response.status_code} for {url}")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise PublicWebError(f"Page exceeds {self.max_bytes} bytes: {url}")
                    chunks.append(chunk)
                body = b"".join(chunks)
                encoding = response.encoding or response.apparent_encoding or "utf-8"
                text = body.decode(encoding, errors="replace")
                final_url = str(response.url)
                self._save_raw(final_url, response.status_code, text)
                return text, final_url, response.status_code
            except requests.exceptions.SSLError as exc:
                # Some Windows Python installations cannot see enterprise or
                # local root CAs while Schannel can. Keep verification enabled
                # and use the operating-system trust store through curl.
                try:
                    return self._get_text_with_system_curl(url)
                except PublicWebError as fallback_error:
                    last_error = PublicWebError(f"{exc}; system TLS fallback failed: {fallback_error}")
                    break
            except (requests.RequestException, PublicWebError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(backoff + random.random() * 0.2)
                backoff = min(backoff * 2, 12)
        raise PublicWebError(str(last_error or f"Failed to fetch {url}"))

    def _get_text_with_system_curl(self, url: str) -> tuple[str, str, int]:
        executable = shutil.which("curl.exe" if os.name == "nt" else "curl")
        if not executable:
            raise PublicWebError("System curl is unavailable")
        marker = b"\nLAITOXX_CURL_META:"
        command = [
            executable,
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            str(max(1, round(self.timeout))),
            "--max-filesize",
            str(self.max_bytes),
            "--user-agent",
            self.headers["User-Agent"],
            "--write-out",
            "\nLAITOXX_CURL_META:%{http_code}:%{url_effective}",
        ]
        if os.name == "nt":
            command.append("--ssl-revoke-best-effort")
        command.append(url)
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=self.timeout + 5,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise PublicWebError(str(error)) from error
        body, separator, metadata = result.stdout.rpartition(marker)
        if not separator:
            raise PublicWebError("System curl returned no response metadata")
        status_text, separator, final_url = metadata.partition(b":")
        if not separator:
            raise PublicWebError("System curl returned malformed response metadata")
        try:
            status = int(status_text)
        except ValueError as error:
            raise PublicWebError("System curl returned an invalid HTTP status") from error
        if len(body) > self.max_bytes:
            raise PublicWebError(f"Page exceeds {self.max_bytes} bytes: {url}")
        text = body.decode("utf-8", errors="replace")
        resolved_url = final_url.decode("utf-8", errors="replace")
        self._save_raw(resolved_url, status, text)
        return text, resolved_url, status

    def _save_raw(self, url: str, status: int, text: str) -> None:
        if not self.raw_dir:
            return
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        digest = stable_id(url)[:12]
        path = self.raw_dir / f"{stamp}_public_{digest}.html"
        header = f"<!-- fetched_at={utc_now_iso()} status={status} url={html.escape(url)} -->\n"
        path.write_text(header + text, encoding="utf-8")
