"""Collect quota-aware Shodan account, facet, count, and search data."""

from __future__ import annotations

from requests import HTTPError, RequestException

from ..models import ProviderResult
from ..provider_common import _SHODAN_INFO_LOCK, _cached_json, _paced_shodan_json, _safe_error
from ..quota import QuotaExceeded, ledger
from ..shodan_filters import RESTRICTED_FILTERS

_SHODAN_CORE_FACETS = ("port", "product", "version", "org", "asn", "country", "os", "tag")
_SHODAN_PIVOT_FACETS = ("ip", "domain", "hostname", "vuln", "cpe")
_SHODAN_DETAIL_FACETS = (
    "device",
    "shodan.module",
    "cloud.provider",
    "cloud.region",
    "cloud.service",
    "http.component",
    "http.component_category",
    "http.status",
    "http.waf",
    "ssl.version",
    "ssl.cert.issuer.cn",
    "ssl.cert.subject.cn",
    "ssl.jarm",
    "ssh.hassh",
)


def collect_shodan_data(*, name, key, key_id, kind, value, query, purpose, required_filters, allow_search_results):
    with _SHODAN_INFO_LOCK:
        account, account_hit = _cached_json(
            "shodan_info",
            key_id,
            "https://api.shodan.io/api-info",
            params={"key": key},
            ttl=900,
            track_quota=False,
        )

    filters_hit = False
    filters_error = ""
    available_filters: set[str] = set(required_filters)
    try:
        raw_filters, filters_hit = _paced_shodan_json(
            "shodan_filters",
            key_id,
            "https://api.shodan.io/shodan/host/search/filters",
            params={"key": key},
            ttl=86400,
        )
        if isinstance(raw_filters, list):
            available_filters = {str(item) for item in raw_filters}
    except (QuotaExceeded, RequestException, ValueError) as exc:
        filters_error = _safe_error(exc)
    missing_filters = sorted(set(required_filters) - available_filters)
    if not bool(account.get("unlocked")):
        missing_filters = sorted(set(missing_filters) | (set(required_filters) & RESTRICTED_FILTERS))
    if missing_filters:
        return ProviderResult(
            name,
            "no_data",
            data={
                "target": {"kind": kind, "value": value},
                "query": query,
                "purpose": purpose,
                "required_filters": list(required_filters),
                "available_filter_count": len(available_filters),
                "unsupported_filters": missing_filters,
            },
            error=f"Shodan key does not expose filters: {', '.join(missing_filters)}",
        )

    available_facets: set[str] = set(_SHODAN_CORE_FACETS)
    facets_hit = False
    facets_error = ""
    try:
        raw_facets, facets_hit = _paced_shodan_json(
            "shodan_facets",
            key_id,
            "https://api.shodan.io/shodan/host/search/facets",
            params={"key": key},
            ttl=86400,
        )
        if isinstance(raw_facets, list):
            available_facets.update(str(item) for item in raw_facets)
    except (QuotaExceeded, RequestException, ValueError) as exc:
        facets_error = _safe_error(exc)

    requested_facets = [
        facet
        for facet in (
            *_SHODAN_CORE_FACETS,
            *_SHODAN_PIVOT_FACETS,
            *_SHODAN_DETAIL_FACETS,
        )
        if facet in available_facets
    ]
    facets_parameter = ",".join(f"{facet}:25" for facet in requested_facets)
    count_facets_error = ""
    try:
        count_data, count_hit = _paced_shodan_json(
            "shodan_count",
            f"{key_id}:{query}:{facets_parameter}",
            "https://api.shodan.io/shodan/host/count",
            params={"key": key, "query": query, "facets": facets_parameter},
            ttl=21600,
        )
    except HTTPError as exc:
        # Some plans expose a smaller facet catalogue than the discovery
        # endpoint. Preserve free enrichment with the conservative set.
        if exc.response is None or exc.response.status_code not in {400, 403}:
            raise
        count_facets_error = _safe_error(exc)
        safe_facets = ("port", "product", "org", "asn", "country", "os")
        facets_parameter = ",".join(f"{facet}:25" for facet in safe_facets)
        count_data, count_hit = _paced_shodan_json(
            "shodan_count",
            f"{key_id}:{query}:{facets_parameter}",
            "https://api.shodan.io/shodan/host/count",
            params={"key": key, "query": query, "facets": facets_parameter},
            ttl=21600,
        )
    if not isinstance(count_data, dict):
        count_data = {}

    search_data: dict = {}
    search_hit = False
    search_error = ""
    try:
        published_credits = max(0, int(account.get("query_credits") or 0))
    except (TypeError, ValueError):
        published_credits = 0
    quota_status = ledger.status("shodan_account")
    available_credits = quota_status.remaining if quota_status.remaining is not None else published_credits
    if allow_search_results and published_credits > 0 and available_credits > 0:
        try:
            search_data, search_hit = _paced_shodan_json(
                "shodan_search",
                f"{key_id}:{query}:1",
                "https://api.shodan.io/shodan/host/search",
                params={"key": key, "query": query, "page": 1, "minify": "true"},
                consumes_credit=True,
                ttl=21600,
            )
            current_remaining = ledger.status("shodan_account").remaining
            debit_base = current_remaining if current_remaining is not None else published_credits
            ledger.update_remote(
                "shodan_account",
                remaining=max(0, debit_base - 1),
                source=f"Shodan plan: {account.get('plan', 'unknown')}; local debit",
            )
        except (QuotaExceeded, RequestException, ValueError) as exc:
            search_error = _safe_error(exc)

    matches = [
        item
        for item in ((search_data.get("matches") if isinstance(search_data, dict) else []) or [])
        if isinstance(item, dict)
    ][:100]
    return locals()
