"""Shodan account capability and scoped search enrichment."""

from __future__ import annotations

import hashlib
import ipaddress

from ..configuration import credential
from ..models import ProviderResult
from ..provider_common import (
    _SHODAN_INFO_LOCK,
    _cached_json,
    _domain_candidate,
    _run,
    skipped,
)
from ..quota import ledger
from ..shodan_filters import exact_scope
from .shodan_collect import collect_shodan_data
from .shodan_facets import project_shodan_facets
from .shodan_matches import project_shodan_matches


def shodan_account_info() -> ProviderResult:
    """Return account capabilities without attempting a membership-only host lookup."""
    key = credential("shodan_account")
    if not key:
        return skipped("Shodan Account", "SHODAN_API_KEY is not configured")

    def load():
        key_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        with _SHODAN_INFO_LOCK:
            data, hit = _cached_json(
                "shodan_info",
                key_id,
                "https://api.shodan.io/api-info",
                params={"key": key},
                ttl=900,
                track_quota=False,
            )
        credits = data.get("query_credits")
        ledger.update_remote(
            "shodan_account",
            remaining=int(credits) if credits is not None else None,
            source=f"Shodan plan: {data.get('plan', 'unknown')}",
        )
        compact = {
            key: data.get(key)
            for key in (
                "plan",
                "unlocked",
                "query_credits",
                "scan_credits",
                "monitored_ips",
                "usage_limits",
            )
            if key in data
        }
        return ProviderResult("Shodan Account", "cached" if hit else "ok", compact)

    return _run("Shodan Account", load)


def _shodan_scope_query(kind: str, value: str) -> tuple[str, str]:
    if kind == "ip":
        address = ipaddress.ip_address(value)
        normalized = str(address)
        query, _filters = exact_scope("ip", normalized)
        return normalized, query
    if kind == "domain":
        normalized = _domain_candidate(value)
        if normalized:
            query, _filters = exact_scope("domain", normalized)
            return normalized, query
    raise ValueError("Shodan search enrichment requires a valid IP or domain")


def _shodan_compact_match(match: dict) -> dict:
    """Retain enrichment fields and explicitly discard raw service banners."""
    http_data = match.get("http") or {}
    ssl_data = match.get("ssl") or {}
    certificate = ssl_data.get("cert") or {}
    return {
        key: match.get(key)
        for key in (
            "ip_str",
            "port",
            "transport",
            "product",
            "version",
            "hostnames",
            "domains",
            "org",
            "isp",
            "asn",
            "timestamp",
            "cpe",
            "vulns",
            "tags",
        )
    } | {
        "http": {
            "title": http_data.get("title"),
            "server": http_data.get("server"),
            "favicon_hash": (http_data.get("favicon") or {}).get("hash")
            if isinstance(http_data.get("favicon"), dict)
            else http_data.get("favicon_hash"),
            "html_hash": http_data.get("html_hash"),
            "headers_hash": http_data.get("headers_hash"),
            "title_hash": http_data.get("title_hash"),
        },
        "ssl": {
            "version": ssl_data.get("version"),
            "jarm": ssl_data.get("jarm"),
            "ja3s": ssl_data.get("ja3s"),
            "subject": certificate.get("subject") or {},
            "issuer": certificate.get("issuer") or {},
            "alt_names": certificate.get("alt_names") or [],
            "fingerprint": certificate.get("fingerprint") or {},
        },
    }


def shodan_search_enrichment(
    kind: str,
    value: str,
    *,
    query_override: str = "",
    required_filters: tuple[str, ...] = (),
    purpose: str = "Exact target filter",
    relation: str = "matches_shodan_filter",
    confidence: str = "medium",
    allow_search_results: bool = True,
    collision_prone: bool = False,
) -> ProviderResult:
    """Use free filtered facets and, when credits exist, compact search results.

    `/shodan/host/count` is the important free-account path: it accepts search
    filters and facets without consuming query credits. The membership-only
    `/shodan/host/{ip}` endpoint is deliberately never called here.
    """
    name = "Shodan Search Enrichment"
    key = credential("shodan_account")
    if not key:
        return skipped(name, "SHODAN_API_KEY is not configured")
    if query_override:
        value = str(value).strip()
        query = query_override.strip()
        if not value or not query:
            return ProviderResult(name, "no_data", error="Shodan pivot requires an anchor and query")
    else:
        try:
            value, query = _shodan_scope_query(kind, value)
        except ValueError as exc:
            return ProviderResult(name, "no_data", error=str(exc))
        required_filters = ("net",) if kind == "ip" else ("hostname",)
    key_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def load():
        collected = collect_shodan_data(
            name=name,
            key=key,
            key_id=key_id,
            kind=kind,
            value=value,
            query=query,
            purpose=purpose,
            required_filters=required_filters,
            allow_search_results=allow_search_results,
        )
        account = collected["account"]
        count_data = collected["count_data"]
        matches = collected["matches"]
        available_filters = collected["available_filters"]
        filters_error = collected["filters_error"]
        facets_error = collected["facets_error"]
        count_facets_error = collected["count_facets_error"]
        search_error = collected["search_error"]
        account_hit = collected["account_hit"]
        filters_hit = collected["filters_hit"]
        facets_hit = collected["facets_hit"]
        count_hit = collected["count_hit"]
        search_hit = collected["search_hit"]
        entities, relations, timeline, root, facets = project_shodan_facets(
            name=name,
            kind=kind,
            value=value,
            query=query,
            purpose=purpose,
            required_filters=required_filters,
            count_data=count_data,
            relation=relation,
            confidence=confidence,
            collision_prone=collision_prone,
        )
        entities, relations, timeline = project_shodan_matches(
            name=name,
            kind=kind,
            value=value,
            purpose=purpose,
            matches=matches,
            relation=relation,
            confidence=confidence,
            entities=entities,
            relations=relations,
            timeline=timeline,
            root=root,
        )

        compact_account = {
            field: account.get(field)
            for field in ("plan", "unlocked", "query_credits", "scan_credits", "usage_limits")
            if field in account
        }
        compact = {
            "target": {"kind": kind, "value": value},
            "query": query,
            "purpose": purpose,
            "required_filters": list(required_filters),
            "available_filter_count": len(available_filters),
            "collision_prone": collision_prone,
            "account": compact_account,
            "mode": "facets_and_results" if matches else "facets_only",
            "total": int(count_data.get("total") or 0),
            "facets": facets,
            "matches": [_shodan_compact_match(match) for match in matches],
            "search_error": search_error,
            "filters_discovery_error": filters_error,
            "facets_discovery_error": facets_error,
            "count_facets_error": count_facets_error,
        }
        cached = account_hit and filters_hit and facets_hit and count_hit and (not matches or search_hit)
        status = "cached" if cached else "ok"
        if not compact["total"] and not matches:
            status = "no_data"
        return ProviderResult(name, status, compact, entities, relations, timeline)

    return _run(name, load)
