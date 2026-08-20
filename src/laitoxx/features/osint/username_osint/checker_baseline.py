from __future__ import annotations

import threading
import time
from typing import Any

import aiohttp

from laitoxx.core.settings.network_manager import aiohttp_proxy_url

from .models import SiteEntry

_BASELINE_TTL_SECONDS = 21600
_SHARED_BASELINES: dict[str, tuple[float, _Baseline]] = {}
_SHARED_BASELINES_LOCK = threading.Lock()

# Type aliases
_Verdict = tuple[str, str]  # (status, reason)
_Baseline = dict[str, Any]
_Facts = dict[str, Any]


class BaselineCheckMixin:
    async def _get_control_baseline(self, session: aiohttp.ClientSession, site: SiteEntry) -> _Baseline | None:
        cache_key = site.url_probe or site.url_template
        with _SHARED_BASELINES_LOCK:
            cached = _SHARED_BASELINES.get(cache_key)
            if cached and time.monotonic() - cached[0] <= _BASELINE_TTL_SECONDS:
                return cached[1]
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
                with _SHARED_BASELINES_LOCK:
                    _SHARED_BASELINES[cache_key] = (time.monotonic(), baseline)
                return baseline
        except Exception:
            return None

    def _logical_inference(self, facts: _Facts) -> _Verdict:
        """Return a verdict and reason from ordered negative and positive evidence checks."""
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
