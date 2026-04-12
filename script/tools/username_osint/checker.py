from __future__ import annotations

import asyncio
import difflib
import logging
import random
import re
import string
import time
from typing import Any, Callable
from urllib.parse import urlparse

import aiohttp

from ._patterns import (
    DEFAULT_UA,
    FALSE_POSITIVE_PHRASES,
    HARD_TITLE_404,
    JS_REDIRECT_PATTERNS,
    LOGIN_WALL_MARKERS,
    MIN_PROFILE_BODY_SIZE,
    SOFT_TITLE_BAD,
    WAF_MARKERS,
)
from .models import CheckResult, SiteEntry

try:
    from settings.network_manager import make_aiohttp_connector, aiohttp_proxy_url
    _HAS_NM = True
except ImportError:
    _HAS_NM = False

    def make_aiohttp_connector() -> aiohttp.TCPConnector:
        return aiohttp.TCPConnector()

    def aiohttp_proxy_url() -> None:
        return None


log = logging.getLogger(__name__)

# Type aliases
_Verdict = tuple[str, str]   # (status, reason)
_Baseline = dict[str, Any]
_Facts = dict[str, Any]


class UsernameChecker:
    def __init__(
        self,
        sites: list[SiteEntry],
        max_workers: int = 50,
        proxy: dict | None = None,
        progress_callback: Callable[[int, int, CheckResult], None] | None = None,
        max_retries: int = 3,
    ) -> None:
        self.sites = [s for s in sites if not s.disabled]
        self.max_workers = max_workers
        self.proxy = proxy  # kept for API compat; NM controls actual proxy
        self.progress_callback = progress_callback
        self.max_retries = max_retries

        self._control_cache: dict[str, _Baseline] = {}
        self._control_lock: asyncio.Lock | None = None  # created lazily inside event loop
        self._cancelled = False

        # Уникальный «контрольный бред» на каждую сессию
        self._junk_username = self._make_junk_username()

        # Компилируем паттерны «не найден» в regex для быстрого поиска
        self._compiled_negative_regex = self._compile_negative_patterns(FALSE_POSITIVE_PHRASES)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def cancel(self) -> None:
        self._cancelled = True

    def check_username(self, username: str) -> list[CheckResult]:
        """Synchronous entry point — runs the async engine in a new event loop."""
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
                    result = await self._check_single(session, site, username)
                counter["n"] += 1
                if self.progress_callback:
                    try:
                        self.progress_callback(counter["n"], total, result)
                    except Exception:
                        pass
                return result

            tasks = [_run_one(site) for site in self.sites]
            for coro in asyncio.as_completed(tasks):
                if self._cancelled:
                    break
                result = await coro
                results.append(result)

        return results

    async def _check_single(
        self, session: aiohttp.ClientSession, site: SiteEntry, username: str
    ) -> CheckResult:
        if self._cancelled:
            return CheckResult(
                site_name=site.name,
                url=site.url_template.replace("{username}", username),
                status="error",
                error_message="Cancelled",
            )

        baseline = await self._get_control_baseline(session, site)
        result = CheckResult(
            site_name=site.name,
            url=site.url_template.replace("{username}", username),
            category=site.category,
            engine=site.engine,
        )

        if not self._validate_username(site, username):
            result.status, result.error_message = "not_found", "Invalid format"
            return result

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
                result.waf_detected = (verdict == "waf_blocked")
                if verdict == "found":
                    result.confidence = self._compute_confidence(resp.status, body, username)

                return result

            except Exception as e:
                if attempt == self.max_retries - 1:
                    result.status, result.error_message = "error", str(e)
                await asyncio.sleep(0.5 * (attempt + 1))

        return result

    # -------------------------------------------------------------------------
    # Baseline
    # -------------------------------------------------------------------------

    async def _get_control_baseline(
        self, session: aiohttp.ClientSession, site: SiteEntry
    ) -> _Baseline | None:
        async with self._control_lock:
            if site.name in self._control_cache:
                return self._control_cache[site.name]

        url = (site.url_probe or site.url_template).replace("{username}", self._junk_username)
        proxy = aiohttp_proxy_url()

        try:
            async with session.get(
                url,
                headers=site.headers or {},
                allow_redirects=True,
                proxy=proxy,
            ) as resp:
                text = await resp.text(errors="replace")
                baseline: _Baseline = {
                    "status": resp.status,
                    "length": len(text),
                    "url_normalized": self._normalize_url(str(resp.url)),
                    "body_lower": text[:15000].lower(),
                }
                async with self._control_lock:
                    self._control_cache[site.name] = baseline
                return baseline
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Logical inference — entry point + per-step helpers
    # -------------------------------------------------------------------------

    def _logical_inference(self, facts: _Facts) -> _Verdict:
        """
        Возвращает (verdict, reason).
        verdict: "found" | "not_found" | "waf_blocked" | "login_required"

        Порядок проверок:
          1. WAF/Captcha
          2. HTTP статус
          3. Серверные редиректы
          4. Login Wall
          5. JS/Meta редиректы
          6. Title анализ
          7. Per-site absence_strs / invalid_indicators
          8. Глобальные паттерны «не найдено»
          9. Baseline сравнение
         10. Позитивное подтверждение
        """
        body = facts["body"]
        body_lower = body.lower()
        username: str = facts["username"].lower()
        site: SiteEntry = facts["site"]
        baseline: _Baseline | None = facts["baseline"]

        verdict = self._check_waf(body_lower)
        if verdict:
            return verdict

        verdict = self._check_http_status(facts["status_code"], site)
        if verdict:
            return verdict

        final_norm, verdict = self._check_server_redirects(facts, username)
        if verdict:
            return verdict

        verdict = self._check_login_wall(body_lower)
        if verdict:
            return verdict

        verdict = self._check_js_redirects(body)
        if verdict:
            return verdict

        title_text, verdict = self._check_title(body, username)
        if verdict:
            return verdict

        verdict = self._check_per_site_patterns(site, body_lower)
        if verdict:
            return verdict

        verdict = self._check_global_patterns(body)
        if verdict:
            return verdict

        verdict = self._check_baseline(facts, final_norm, body_lower, baseline)
        if verdict:
            return verdict

        return self._check_positive_confirmation(body, body_lower, title_text, username)

    def _check_waf(self, body_lower: str) -> _Verdict | None:
        for marker in WAF_MARKERS:
            if marker in body_lower:
                return "waf_blocked", f"WAF/bot-protection detected: '{marker}'"
        return None

    def _check_http_status(self, status: int, site: SiteEntry) -> _Verdict | None:
        if status not in site.valid_status:
            return "not_found", f"Invalid status code: {status}"
        return None

    def _check_server_redirects(
        self, facts: _Facts, username: str
    ) -> tuple[str, _Verdict | None]:
        """Returns (final_norm, verdict_or_None)."""
        initial_url: str = facts["initial_url"]
        final_url: str = facts["final_url"]
        initial_norm = self._normalize_url(initial_url)
        final_norm = self._normalize_url(final_url)

        if facts["history"] or initial_norm != final_norm:
            if self._is_benign_redirect(initial_url, final_url, username):
                final_norm = self._normalize_url(final_url)
            else:
                return final_norm, (
                    "not_found", f"Redirected away from profile URL: {final_url}"
                )
        return final_norm, None

    def _check_login_wall(self, body_lower: str) -> _Verdict | None:
        for marker in LOGIN_WALL_MARKERS:
            if marker in body_lower:
                return "login_required", f"Login wall detected: '{marker}'"
        return None

    def _check_js_redirects(self, body: str) -> _Verdict | None:
        body_head = body[:8000]
        for pattern in JS_REDIRECT_PATTERNS:
            if pattern.search(body_head):
                return "not_found", "Hidden JS/Meta redirect detected"
        return None

    def _check_title(self, body: str, username: str) -> tuple[str, _Verdict | None]:
        """Returns (title_text, verdict_or_None)."""
        title_match = re.search(r'<title>(.*?)</title>', body, re.IGNORECASE | re.DOTALL)
        if not title_match:
            return "", None

        title_text = title_match.group(1).lower().strip()

        if any(p in title_text for p in HARD_TITLE_404):
            return title_text, ("not_found", f"404 in page title: '{title_text}'")

        if any(p in title_text for p in SOFT_TITLE_BAD) and username not in title_text:
            return title_text, ("not_found", f"Suspicious title: '{title_text}'")

        return title_text, None

    def _check_per_site_patterns(
        self, site: SiteEntry, body_lower: str
    ) -> _Verdict | None:
        for s in site.absence_strs:
            if s.lower() in body_lower:
                return "not_found", f"Absence indicator found: '{s}'"
        for s in site.invalid_indicators:
            if s.lower() in body_lower:
                return "not_found", f"Invalid indicator found: '{s}'"
        return None

    def _check_global_patterns(self, body: str) -> _Verdict | None:
        for regex in self._compiled_negative_regex:
            if regex.search(body):
                return "not_found", f"Negative pattern match: '{regex.pattern}'"
        return None

    def _check_baseline(
        self,
        facts: _Facts,
        final_norm: str,
        body_lower: str,
        baseline: _Baseline | None,
    ) -> _Verdict | None:
        if not baseline:
            return None

        username: str = facts["username"].lower()

        # 9a. Финальный URL совпадает с URL baseline-заглушки
        if final_norm == baseline["url_normalized"] and username not in final_norm:
            return "not_found", "Landing URL matches non-existent user baseline"

        # 9b. Контент идентичен baseline
        len_diff = abs(facts["content_length"] - baseline["length"])
        if len_diff < 50:
            ratio = difflib.SequenceMatcher(
                None, body_lower[:2000], baseline["body_lower"][:2000]
            ).ratio()
            if ratio > 0.97:
                return "not_found", f"Content identical to baseline ({ratio:.2f})"

        # 9c. Страница не тяжелее baseline — скорее всего заглушка
        if facts["content_length"] < MIN_PROFILE_BODY_SIZE:
            if facts["content_length"] <= baseline["length"] + 200:
                return (
                    "not_found",
                    f"Page too small ({facts['content_length']} bytes), likely a stub",
                )

        return None

    def _check_positive_confirmation(
        self,
        body: str,
        body_lower: str,
        title_text: str,
        username: str,
    ) -> _Verdict:
        """
        Проверяет наличие никнейма по приоритетным местам:
          a) JSON username-поле
          b) <title>
          c) <h1>
          d) og:title / og:url
          e) href/src атрибут
          f) тело страницы (fallback)
        """
        uname_escaped = re.escape(username)

        # a) JSON username-поле
        json_re = re.compile(
            r'"(?:username|user|login|handle|screen_name|name)"\s*:\s*"'
            + uname_escaped + r'"',
            re.IGNORECASE,
        )
        if json_re.search(body):
            return "found", ""

        # b) <title>
        if title_text:
            title_token_re = re.compile(
                r'(?:^|[\s/\'"@:·\-|])' + uname_escaped + r'(?:$|[\s/\'"@:·\-|])'
            )
            if title_token_re.search(title_text):
                return "found", ""

        # c) <h1>
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.IGNORECASE | re.DOTALL)
        if h1_match:
            h1_text = h1_match.group(1).lower()
            h1_token_re = re.compile(
                r'(?:^|[\s/\'"@:·\-|])' + uname_escaped + r'(?:$|[\s/\'"@:·\-|])'
            )
            if h1_token_re.search(h1_text):
                return "found", ""

        # d) og:title / og:url
        og_match = re.search(
            r'<meta[^>]+(?:og:title|og:url)[^>]+content=["\']([^"\']+)["\']',
            body, re.IGNORECASE,
        )
        if og_match and username in og_match.group(1).lower():
            return "found", ""

        # e) href/src атрибут
        url_attr_re = re.compile(
            r'(?:href|src)=["\'][^"\']*/' + uname_escaped + r'(?:[/"\'?]|$)',
            re.IGNORECASE,
        )
        if url_attr_re.search(body):
            return "found", ""

        # f) Тело страницы (fallback)
        body_token_re = re.compile(
            r'(?:^|[\s/\\"\'@:,<>()\[\]{}|])' + uname_escaped
            + r'(?:$|[\s/\\"\'@:,<>()\[\]{}|])',
            re.MULTILINE,
        )
        if body_token_re.search(body_lower):
            return "found", ""

        return "not_found", f"Username '{username}' not found as a distinct token on the page"

    # -------------------------------------------------------------------------
    # Static helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _make_junk_username() -> str:
        """Генерирует случайный бессмысленный никнейм — гарантированно несуществующий."""
        chars = string.ascii_lowercase + string.digits
        prefix = "".join(random.choices(string.ascii_lowercase, k=4))
        suffix = "".join(random.choices(chars, k=10))
        return f"{prefix}{suffix}"

    @staticmethod
    def _compile_negative_patterns(phrases: list[str]) -> list[re.Pattern]:
        """Компилирует список строк в простые regex-паттерны."""
        return [
            re.compile(re.escape(p), re.IGNORECASE)
            for p in phrases
            if p.strip()
        ]

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Нормализует URL для сравнения редиректов.
        Игнорирует: протокол, www-префикс, trailing slash, регистр.
        Оставляет: хост + путь (без query/fragment).
        """
        parsed = urlparse(url.lower())
        netloc = parsed.netloc.replace("www.", "")
        path = parsed.path.rstrip("/")
        return f"{netloc}{path}"

    @staticmethod
    def _is_benign_redirect(initial_url: str, final_url: str, username: str) -> bool:
        """
        Возвращает True если редирект безопасен:
          1. http → https (или обратно) на том же хосте и пути
          2. Нормализация trailing slash / регистра
          3. Языковой субдомен: site.com → xx.site.com
          4. Языковой префикс в пути: /alex → /en/alex
        """
        i = urlparse(initial_url.lower())
        f = urlparse(final_url.lower())

        i_host = i.netloc.replace("www.", "")
        f_host = f.netloc.replace("www.", "")
        i_path = i.path.rstrip("/")
        f_path = f.path.rstrip("/")

        # 1 & 2. Хост тот же, путь совпадает (протокол/регистр/slash уже нормализованы)
        if i_host == f_host and i_path == f_path:
            return True

        # 3. Языковой субдомен
        if f_host.endswith("." + i_host):
            prefix = f_host[: -(len(i_host) + 1)]
            if re.match(r"^[a-z]{2,5}$", prefix) and i_path == f_path:
                return True

        # 4. Языковой префикс в пути
        if i_host == f_host:
            lang_prefix_re = re.compile(
                r"^/[a-z]{2}(?:-[a-z]{2})?" + re.escape(i_path) + r"$"
            )
            if lang_prefix_re.match(f_path):
                return True

        return False

    @staticmethod
    def _validate_username(site: SiteEntry, username: str) -> bool:
        if not site.regex_check:
            return True
        try:
            return bool(re.match(site.regex_check, username))
        except re.error:
            return True

    @staticmethod
    def _compute_confidence(status_code: int, body: str, username: str) -> float:
        score = 0.4
        body_lower = body.lower()
        if status_code == 200:
            score += 0.2
        if username.lower() in body_lower:
            score += 0.3
        if f"<title>{username}" in body_lower:
            score += 0.1
        return min(score, 1.0)
