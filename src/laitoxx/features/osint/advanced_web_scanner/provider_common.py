"""Shared transport, pacing, caching, and provider result helpers."""

from __future__ import annotations

import re
import threading
import time
from datetime import UTC, datetime
from typing import Any

from requests import HTTPError, RequestException, Timeout

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.osint.intelligence.cache import cache

from .models import ProviderResult
from .quota import QuotaExceeded, ledger

USER_AGENT = "Laitoxx-Advanced-Web-Scanner/1.0"
_DNS_RECORD_TYPE_BY_CODE = {
    1: "A",
    2: "NS",
    5: "CNAME",
    6: "SOA",
    12: "PTR",
    15: "MX",
    16: "TXT",
    28: "AAAA",
    52: "TLSA",
    257: "CAA",
}
_FEED_LOCK = threading.Lock()
_OTX_LOCK = threading.Lock()
_SHODAN_INFO_LOCK = threading.Lock()
_SHODAN_API_LOCK = threading.Lock()
_SHODAN_LAST_REQUEST = 0.0
_LEAKIX_LOCK = threading.Lock()
_LEAKIX_LAST_REQUEST = 0.0
_NAMESPACE_PROVIDER = {
    "dns": "dns",
    "dns_google": "dns",
    "dns_security": "dns",
    "rdap": "rdap",
    "rdap_bootstrap": "rdap",
    "rdap_authoritative": "rdap",
    "ipinfo": "ipinfo",
    "ripestat": "ripestat",
    "ripestat_rpki": "ripestat",
    "ripestat_routing": "ripestat",
    "ripestat_prefixes": "ripestat",
    "internetdb": "internetdb",
    "crtsh": "crtsh",
    "otx": "otx",
    "abuseipdb": "abuseipdb",
    "nvd": "nvd",
    "nvd_match": "nvd",
    "osv": "osv",
    "osv_match": "osv",
    "cisa_kev_feed": "kev",
    "epss": "epss",
    "github_advisories": "github_advisories",
    "github_affects": "github_advisories",
    "vulncheck_nvd": "vulncheck",
    "vulncheck_kev": "vulncheck",
    "vulncheck_cpe_search": "vulncheck",
    "shodan_info": "shodan_account",
    "shodan_count": "shodan_account",
    "shodan_search": "shodan_account",
    "shodan_facets": "shodan_account",
    "shodan_filters": "shodan_account",
    "whoisjson_reverse": "whoisjson",
    "botoi_reverse": "botoi",
    "virustotal": "virustotal",
    "virustotal_resolutions": "virustotal",
    "urlscan": "urlscan",
    "wayback": "wayback",
    "commoncrawl_index": "commoncrawl",
    "greynoise": "greynoise",
    "certspotter": "certspotter",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _entity_id(kind: str, value: str) -> str:
    return f"{kind}:{value.casefold()}"


def _domain_candidate(value: Any) -> str:
    """Normalize a value only when it is a syntactically valid domain name."""
    candidate = str(value or "").strip().lower().rstrip(".")
    if candidate.startswith("*."):
        candidate = candidate[2:]
    try:
        candidate = candidate.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeDecodeError):
        return ""
    domain_pattern = (
        r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z0-9-]{2,63}"
    )
    return candidate if re.fullmatch(domain_pattern, candidate, re.I) else ""


def _status_data(result: tuple[Any, bool]) -> tuple[str, Any]:
    data, cache_hit = result
    return ("cached" if cache_hit else "ok", data)


def _cached_json(
    namespace: str,
    query: str,
    url: str,
    *,
    ttl: int = 3600,
    params: dict | None = None,
    headers: dict | None = None,
    method: str = "get",
    body: dict | None = None,
    track_quota: bool = True,
) -> tuple[Any, bool]:
    def load():
        provider_id = _NAMESPACE_PROVIDER[namespace]
        event_id = ledger.acquire(provider_id) if track_quota else None
        request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
        if method == "post":
            response = get_session().post(url, params=params, json=body, headers=request_headers, timeout=25)
        else:
            response = get_session().get(url, params=params, headers=request_headers, timeout=25)
        if event_id is not None:
            ledger.record_response(event_id, provider_id, response.status_code, response.headers)
        response.raise_for_status()
        return response.json()

    return cache.get_or_set(f"advanced_web_scanner:{namespace}", query, load, ttl)


def _paced_shodan_json(
    namespace: str,
    query: str,
    url: str,
    *,
    params: dict,
    consumes_credit: bool = False,
    ttl: int = 21600,
):
    """Cache and serialize Shodan API calls while separating free facet calls.

    Host-count/facet requests do not consume query credits, so they must not be
    rejected merely because /api-info reports zero query credits. Filtered
    search requests do consume a credit and therefore go through the ledger.
    """
    cache_namespace = f"advanced_web_scanner:{namespace}"
    cached = cache.get(cache_namespace, query)
    if cached is not None:
        return cached, True

    global _SHODAN_LAST_REQUEST
    with _SHODAN_API_LOCK:
        cached = cache.get(cache_namespace, query)
        if cached is not None:
            return cached, True
        delay = 1.05 - (time.monotonic() - _SHODAN_LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        event_id = ledger.acquire("shodan_account") if consumes_credit else None
        _SHODAN_LAST_REQUEST = time.monotonic()
        response = get_session().get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        if event_id is not None:
            ledger.record_response(event_id, "shodan_account", response.status_code, response.headers)
        response.raise_for_status()
        data = response.json()
        return cache.set(cache_namespace, query, data, ttl), False


def _leakix_cached_json(
    namespace: str,
    query: str,
    url: str,
    headers: dict,
    ttl: int = 21600,
    params: dict | None = None,
):
    """Cached LeakIX request with the documented one-request/second pacing."""
    cache_namespace = f"advanced_web_scanner:{namespace}"
    cached = cache.get(cache_namespace, query)
    if cached is not None:
        return cached, True

    global _LEAKIX_LAST_REQUEST
    with _LEAKIX_LOCK:
        cached = cache.get(cache_namespace, query)
        if cached is not None:
            return cached, True
        delay = 1.05 - (time.monotonic() - _LEAKIX_LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        event_id = ledger.acquire("leakix")
        _LEAKIX_LAST_REQUEST = time.monotonic()
        response = get_session().get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT, **headers},
            timeout=30,
        )
        ledger.record_response(event_id, "leakix", response.status_code, response.headers)
        response.raise_for_status()
        data = response.json()
        return cache.set(cache_namespace, query, data, ttl), False


def _run(name: str, loader) -> ProviderResult:
    started = time.perf_counter()
    try:
        result = loader()
        result.name = name
        result.duration_ms = round((time.perf_counter() - started) * 1000)
        return result
    except QuotaExceeded as exc:
        return ProviderResult(
            name=name,
            status="rate_limited",
            error=_safe_error(exc),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
    except HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        status = (
            "auth_error"
            if code == 401
            else "restricted"
            if code in {402, 403}
            else "rate_limited"
            if code == 429
            else "no_data"
            if code == 404
            else "error"
        )
        return ProviderResult(
            name=name,
            status=status,
            error=_http_error_message(exc),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
    except (Timeout, RequestException) as exc:
        return ProviderResult(
            name=name,
            status="unavailable",
            error=_safe_error(exc),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:
        return ProviderResult(
            name=name,
            status="error",
            error=_safe_error(exc),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )


_SECRET_QUERY_RE = re.compile(r"(?i)([?&](?:key|token|api[_-]?key)=)[^&\s]+")


def _safe_error(error) -> str:
    return _SECRET_QUERY_RE.sub(r"\1<redacted>", str(error))


def _http_error_message(error: HTTPError) -> str:
    response = error.response
    code = response.status_code if response is not None else "unknown"
    message = ""
    if response is not None:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = str(payload.get("error") or payload.get("message") or payload.get("description") or "")
        except (ValueError, TypeError):
            pass
    return _safe_error(f"HTTP {code}" + (f": {message}" if message else ""))


def skipped(name: str, reason: str) -> ProviderResult:
    return ProviderResult(name=name, status="skipped", error=reason)
