from __future__ import annotations

import asyncio
import html
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin, urlsplit

import aiohttp

from laitoxx.core.settings.network_manager import aiohttp_proxy_url, make_aiohttp_connector

from ._patterns import (
    DEFAULT_UA,
    FALSE_POSITIVE_PHRASES,
)
from .health import ProviderHealthStore
from .models import CheckResult, SiteEntry

# Type aliases
_Verdict = tuple[str, str]  # (status, reason)
_Baseline = dict[str, Any]
_Facts = dict[str, Any]


def _extract_avatar_url(body: str, page_url: str) -> str | None:
    """Best-effort avatar discovery without treating arbitrary page art as identity evidence."""
    patterns = (
        r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']',
        r'<img[^>]+(?:class|id)=["\'][^"\']*(?:avatar|profile[-_ ]?(?:image|photo)|userpic)[^"\']*["\'][^>]+src=["\']([^"\']+)',
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]+(?:class|id)=["\'][^"\']*(?:avatar|profile[-_ ]?(?:image|photo)|userpic)',
    )
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            candidate = html.unescape(match.group(1).strip())
            if candidate and not candidate.startswith("data:"):
                return urljoin(page_url, candidate)
    return None


from .checker_baseline import BaselineCheckMixin
from .checker_inference import InferenceMixin
from .checker_utilities import CheckerUtilitiesMixin


class UsernameChecker(BaselineCheckMixin, InferenceMixin, CheckerUtilitiesMixin):
    def __init__(
        self,
        sites: list[SiteEntry],
        max_workers: int = 50,
        progress_callback: Callable[[int, int, CheckResult], None] | None = None,
        max_retries: int = 3,
        per_host_limit: int = 2,
    ) -> None:
        self.sites = [s for s in sites if not s.disabled]
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.max_retries = max_retries
        self.per_host_limit = max(1, per_host_limit)

        self._control_cache: dict[str, _Baseline] = {}
        self._control_lock: asyncio.Lock | None = None  # created lazily inside event loop
        self._cancelled = False
        self._host_semaphores: dict[str, asyncio.Semaphore] = {}
        self._health = ProviderHealthStore()

        # Use a unique control username for each search session.
        self._junk_username = self._make_junk_username()

        # Compile absence patterns once for the complete search.
        self._compiled_negative_regex = self._compile_negative_patterns(FALSE_POSITIVE_PHRASES)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def cancel(self) -> None:
        self._cancelled = True

    def check_username(self, username: str) -> list[CheckResult]:
        """Synchronous entry point - runs the async engine in a new event loop."""
        return asyncio.run(self._check_username_async(username))

    # -------------------------------------------------------------------------
    # Async core
    # -------------------------------------------------------------------------

    async def _check_username_async(self, username: str) -> list[CheckResult]:
        if self._control_lock is None:
            self._control_lock = asyncio.Lock()

        results: list[CheckResult] = []
        total = len(self.sites)
        semaphore = asyncio.Semaphore(self.max_workers)
        counter = {"n": 0}

        connector = make_aiohttp_connector()
        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(
            connector=connector,
            headers={"User-Agent": DEFAULT_UA},
            timeout=timeout,
        ) as session:

            async def _run_one(site: SiteEntry) -> CheckResult:
                async with semaphore:
                    host = (urlsplit(site.url_probe or site.url_template).hostname or site.name).casefold()
                    host_semaphore = self._host_semaphores.setdefault(host, asyncio.Semaphore(self.per_host_limit))
                    async with host_semaphore:
                        result = await self._check_single(session, site, username)
                counter["n"] += 1
                if self.progress_callback:
                    try:
                        self.progress_callback(counter["n"], total, result)
                    except Exception:
                        pass
                self._health.record(result)
                return result

            tasks = [asyncio.create_task(_run_one(site)) for site in self.sites]
            try:
                pending = set(tasks)
                while pending and not self._cancelled:
                    done, pending = await asyncio.wait(pending, timeout=0.1, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        results.append(task.result())
            finally:
                if self._cancelled:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)

        self._health.flush()

        return results

    async def _check_single(self, session: aiohttp.ClientSession, site: SiteEntry, username: str) -> CheckResult:
        if self._cancelled:
            return CheckResult(
                site_name=site.name,
                url=site.url_template.replace("{username}", username),
                status="error",
                error_message="Cancelled",
            )
        result = CheckResult(
            site_name=site.name,
            url=site.url_template.replace("{username}", username),
            category=site.category,
            engine=site.engine,
            tags=list(site.tags),
        )

        if site.request_method.upper() != "GET":
            result.status = "unsupported"
            result.error_message = f"Unsupported request method: {site.request_method}"
            return result

        if not self._validate_username(site, username):
            result.status, result.error_message = "not_found", "Invalid format"
            return result
        baseline = await self._get_control_baseline(session, site)

        probe_url = (site.url_probe or site.url_template).replace("{username}", username)
        proxy = aiohttp_proxy_url()
        req_timeout = aiohttp.ClientTimeout(total=site.timeout)

        for attempt in range(self.max_retries):
            if self._cancelled:
                return result
            try:
                t0 = time.perf_counter()
                async with session.get(
                    probe_url,
                    headers=site.headers or {},
                    allow_redirects=True,
                    proxy=proxy,
                    timeout=req_timeout,
                ) as resp:
                    body = await resp.text(errors="replace")
                    history = resp.history

                if resp.status == 429:
                    result.retry_count = attempt
                    if attempt < self.max_retries - 1:
                        retry_after = resp.headers.get("Retry-After", "")
                        delay = float(retry_after) if retry_after.isdigit() else 0.5 * (attempt + 1)
                        await asyncio.sleep(min(delay, 5.0))
                        continue
                    result.status = "rate_limited"
                    result.error_message = "Provider rate limit reached"
                    return result
                if 500 <= resp.status <= 599 and attempt < self.max_retries - 1:
                    result.retry_count = attempt + 1
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue

                facts: _Facts = {
                    "status_code": resp.status,
                    "content_length": len(body),
                    "initial_url": probe_url,
                    "final_url": str(resp.url),
                    "history": history,
                    "body": body,
                    "username": username,
                    "site": site,
                    "baseline": baseline,
                }

                verdict, reason = self._logical_inference(facts)

                result.http_code = resp.status
                result.response_time_ms = (time.perf_counter() - t0) * 1000
                result.status = verdict
                result.error_message = reason if verdict != "found" else ""
                result.waf_detected = verdict == "waf_blocked"
                if verdict == "found":
                    result.confidence = self._compute_confidence(resp.status, body, username)
                    threshold = max(0.0, min(1.0, site.confidence_threshold))
                    if result.confidence < threshold:
                        result.status = "not_found"
                        result.error_message = (
                            f"Confidence {result.confidence:.0%} is below the provider threshold {threshold:.0%}"
                        )
                        return result
                    result.status = "confirmed" if result.confidence >= 0.75 else "probable"
                    if reason:
                        result.evidence.append(reason)
                    result.profile_url = str(resp.url)
                    if site.avatar_url:
                        result.avatar_url = site.avatar_url.replace("{username}", username)
                    else:
                        result.avatar_url = _extract_avatar_url(body, str(resp.url))

                return result

            except TimeoutError:
                result.retry_count = attempt
                if attempt == self.max_retries - 1:
                    result.status, result.error_message = "timeout", "Request timed out"
                else:
                    await asyncio.sleep(0.5 * (attempt + 1))
            except aiohttp.ClientError as error:
                result.retry_count = attempt
                if attempt == self.max_retries - 1:
                    result.status, result.error_message = "network_error", str(error)
                else:
                    await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as e:
                if attempt == self.max_retries - 1:
                    result.status, result.error_message = "network_error", str(e)
                else:
                    await asyncio.sleep(0.5 * (attempt + 1))

        return result

    # -------------------------------------------------------------------------
    # Baseline
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Logical inference - entry point + per-step helpers
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Static helpers
    # -------------------------------------------------------------------------
