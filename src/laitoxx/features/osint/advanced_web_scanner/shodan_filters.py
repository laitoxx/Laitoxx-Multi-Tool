"""Shodan filter catalogue and conservative automatic pivot planning."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Any

from .models import ScanReport, Target

# Mirrors the public Shodan filter reference. Runtime capability discovery is
# still authoritative because plans and newly introduced filters can differ.
OFFICIAL_FILTER_GROUPS: dict[str, frozenset[str]] = {
    "general": frozenset(
        {
            "all",
            "asn",
            "asset",
            "city",
            "country",
            "cpe",
            "device",
            "domain",
            "geo",
            "google_ads",
            "google_analytics",
            "google_tag_manager",
            "has_ipv6",
            "has_screenshot",
            "has_ssl",
            "has_vuln",
            "hash",
            "hostname",
            "ip",
            "isp",
            "link",
            "meta_pixel",
            "net",
            "org",
            "os",
            "port",
            "postal",
            "product",
            "region",
            "scan",
            "shodan.module",
            "state",
            "tiktok_pixel",
            "version",
            "x_pixel",
        }
    ),
    "screenshot": frozenset({"screenshot.hash", "screenshot.label"}),
    "cloud": frozenset({"cloud.provider", "cloud.region", "cloud.service"}),
    "http": frozenset(
        {
            "http.component",
            "http.component_category",
            "http.dom_hash",
            "http.favicon.hash",
            "http.headers_hash",
            "http.html",
            "http.html_hash",
            "http.robots_hash",
            "http.securitytxt",
            "http.server_hash",
            "http.status",
            "http.title",
            "http.title_hash",
            "http.waf",
        }
    ),
    "bitcoin": frozenset({"bitcoin.ip", "bitcoin.ip_count", "bitcoin.port", "bitcoin.version"}),
    "restricted": frozenset({"tag", "vuln"}),
    "snmp": frozenset({"snmp.contact", "snmp.location", "snmp.name"}),
    "ssl": frozenset(
        {
            "ssl",
            "ssl.alpn",
            "ssl.cert.alg",
            "ssl.cert.expired",
            "ssl.cert.extension",
            "ssl.cert.fingerprint",
            "ssl.cert.issuer.cn",
            "ssl.cert.pubkey.bits",
            "ssl.cert.pubkey.type",
            "ssl.cert.serial",
            "ssl.cert.subject.cn",
            "ssl.chain_count",
            "ssl.cipher.bits",
            "ssl.cipher.name",
            "ssl.cipher.version",
            "ssl.ja3s",
            "ssl.jarm",
            "ssl.version",
        }
    ),
    "ntp": frozenset({"ntp.ip", "ntp.ip_count", "ntp.more", "ntp.port"}),
    "telnet": frozenset({"telnet.do", "telnet.dont", "telnet.option", "telnet.will", "telnet.wont"}),
    "ssh": frozenset({"ssh.hassh", "ssh.type"}),
}

ALL_KNOWN_FILTERS = frozenset().union(*OFFICIAL_FILTER_GROUPS.values())
RESTRICTED_FILTERS = OFFICIAL_FILTER_GROUPS["restricted"]


@dataclass(frozen=True)
class ShodanPivotPlan:
    anchor_kind: str
    anchor_value: str
    query: str
    required_filters: tuple[str, ...]
    purpose: str
    relation: str = "matches_shodan_filter"
    confidence: str = "medium"
    allow_search_results: bool = False
    priority: int = 100
    collision_prone: bool = False


_UNQUOTED_RE = re.compile(r"^(?:-?\d+(?:\.\d+)?|true|false|AS\d+|[0-9a-f:.]+/\d+)$", re.I)


def filter_term(name: str, value: Any) -> str:
    """Build one filter term without allowing user-controlled query syntax."""
    if name not in ALL_KNOWN_FILTERS:
        raise ValueError(f"Unknown Shodan filter: {name}")
    text = str(value).strip()
    if not text:
        raise ValueError(f"Shodan filter {name} requires a value")
    if _UNQUOTED_RE.fullmatch(text):
        return f"{name}:{text}"
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'{name}:"{escaped}"'


def exact_scope(kind: str, value: str) -> tuple[str, tuple[str, ...]]:
    if kind == "ip":
        address = ipaddress.ip_address(value)
        suffix = 32 if address.version == 4 else 128
        return filter_term("net", f"{address}/{suffix}"), ("net",)
    if kind == "domain":
        return filter_term("hostname", value), ("hostname",)
    if kind == "asn":
        normalized = value.upper()
        return filter_term("asn", normalized), ("asn",)
    if kind == "cve":
        return filter_term("vuln", value.upper()), ("vuln",)
    raise ValueError(f"No Shodan scope filter for {kind}")


def _metadata_scalars(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _metadata_scalars(child, path.casefold())
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _metadata_scalars(child, prefix)
    elif value not in {None, ""}:
        yield prefix, value


def contextual_pivots(report: ScanReport, target: Target, limit: int = 8) -> list[ShodanPivotPlan]:
    """Create evidence-driven pivots, ordered by attribution strength."""
    plans: list[ShodanPivotPlan] = []
    seen: set[tuple[str, str, str]] = set()

    def add(plan: ShodanPivotPlan) -> None:
        identity = (plan.anchor_kind, plan.anchor_value.casefold(), plan.query.casefold())
        if identity not in seen:
            seen.add(identity)
            plans.append(plan)

    if target.kind == "domain":
        domain_term = filter_term("domain", target.value)
        add(
            ShodanPivotPlan(
                "domain",
                target.value,
                domain_term,
                ("domain",),
                "Domain-index pivot including subdomain observations",
                priority=10,
            )
        )
        cert_term = filter_term("ssl.cert.subject.cn", target.value)
        add(
            ShodanPivotPlan(
                "domain",
                target.value,
                cert_term,
                ("ssl.cert.subject.cn",),
                "TLS subject pivot for infrastructure using the target identity",
                relation="certificate_subject_match",
                confidence="medium",
                allow_search_results=True,
                priority=12,
            )
        )
        hostname_term, hostname_filters = exact_scope("domain", target.value)
        add(
            ShodanPivotPlan(
                "domain",
                target.value,
                f"{hostname_term} {filter_term('has_vuln', 'true')}",
                (*hostname_filters, "has_vuln"),
                "Vulnerability-bearing Shodan records scoped to the target hostname",
                relation="has_vulnerability_signal",
                allow_search_results=True,
                priority=14,
            )
        )
    elif target.kind == "ip":
        net_term, net_filters = exact_scope("ip", target.value)
        add(
            ShodanPivotPlan(
                "ip",
                target.value,
                f"{net_term} {filter_term('has_vuln', 'true')}",
                (*net_filters, "has_vuln"),
                "Vulnerability-bearing Shodan records scoped to the exact IP",
                relation="has_vulnerability_signal",
                allow_search_results=True,
                priority=10,
            )
        )
    elif target.kind in {"asn", "cve"}:
        query, filters = exact_scope(target.kind, target.value)
        add(
            ShodanPivotPlan(
                target.kind,
                target.value,
                query,
                filters,
                "Direct Shodan index pivot for the normalized target",
                allow_search_results=True,
                priority=5,
            )
        )

    metadata_filter_map = {
        "google_analytics": "google_analytics",
        "google_tag_manager": "google_tag_manager",
        "meta_pixel": "meta_pixel",
        "tiktok_pixel": "tiktok_pixel",
        "x_pixel": "x_pixel",
        "favicon_hash": "http.favicon.hash",
        "favicon_mmh3": "http.favicon.hash",
        "html_hash": "http.html_hash",
        "headers_hash": "http.headers_hash",
        "title_hash": "http.title_hash",
        "screenshot_hash": "screenshot.hash",
        "hassh": "ssh.hassh",
        "ja3s": "ssl.ja3s",
        "jarm": "ssl.jarm",
    }

    for entity in report.entities:
        if entity.kind == "certificate":
            fingerprints = {
                str(entity.metadata.get(key) or "").strip().casefold()
                for key in ("fingerprint_sha256", "sha256", "fingerprint")
            }
            fingerprints.add(str(entity.value).strip().casefold())
            for fingerprint in fingerprints:
                if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", fingerprint):
                    add(
                        ShodanPivotPlan(
                            "certificate",
                            entity.value,
                            filter_term("ssl.cert.fingerprint", fingerprint),
                            ("ssl.cert.fingerprint",),
                            "Exact certificate fingerprint pivot",
                            relation="shares_certificate",
                            confidence="high",
                            allow_search_results=True,
                            priority=20,
                        )
                    )
                    break
            certificate_fields = {
                "serial": "ssl.cert.serial",
                "serial_number": "ssl.cert.serial",
                "subject_cn": "ssl.cert.subject.cn",
                "issuer_cn": "ssl.cert.issuer.cn",
            }
            for metadata_key, filter_name in certificate_fields.items():
                field_value = str(entity.metadata.get(metadata_key) or "").strip()
                if field_value:
                    add(
                        ShodanPivotPlan(
                            "certificate",
                            entity.value,
                            filter_term(filter_name, field_value),
                            (filter_name,),
                            f"Certificate {metadata_key} pivot",
                            relation="shares_certificate_attribute",
                            confidence="medium",
                            allow_search_results=True,
                            priority=24,
                        )
                    )
        elif entity.kind == "web_fingerprint":
            fingerprint_type = str(entity.metadata.get("fingerprint_type") or "").casefold()
            fingerprint = str(entity.metadata.get("fingerprint") or "").strip()
            filter_name = {
                "favicon": "http.favicon.hash",
                "http_html": "http.html_hash",
                "http_headers": "http.headers_hash",
                "http_title": "http.title_hash",
                "jarm": "ssl.jarm",
                "ja3s": "ssl.ja3s",
            }.get(fingerprint_type)
            if filter_name and fingerprint:
                collision_prone = True
                add(
                    ShodanPivotPlan(
                        "web_fingerprint",
                        entity.value,
                        filter_term(filter_name, fingerprint),
                        (filter_name,),
                        f"{fingerprint_type.upper()} correlation pivot",
                        relation="shares_web_fingerprint",
                        confidence="low" if collision_prone else "medium",
                        allow_search_results=fingerprint_type in {"jarm", "ja3s"},
                        priority=35 if fingerprint_type == "favicon" else 28,
                        collision_prone=collision_prone,
                    )
                )
        elif entity.kind == "cpe" and entity.value.startswith("cpe:"):
            add(
                ShodanPivotPlan(
                    "cpe",
                    entity.value,
                    filter_term("cpe", entity.value),
                    ("cpe",),
                    "Exposure landscape for an observed CPE",
                    relation="shares_cpe",
                    confidence="low",
                    priority=60,
                    collision_prone=True,
                )
            )
        elif entity.kind == "service":
            title = str(entity.metadata.get("title") or "").strip()
            category = str(entity.metadata.get("category") or "")
            if title and len(title) >= 8 and category in {"admin_panel", "database", "devops", "monitoring"}:
                add(
                    ShodanPivotPlan(
                        "service",
                        entity.value,
                        filter_term("http.title", title),
                        ("http.title",),
                        "Exact title correlation for a high-interest exposed service",
                        relation="shares_service_title",
                        confidence="low",
                        priority=55,
                        collision_prone=True,
                    )
                )

        metadata_path_filter_map = {
            "cloud.provider": "cloud.provider",
            "cloud.region": "cloud.region",
            "cloud.service": "cloud.service",
            "http.component": "http.component",
            "http.dom_hash": "http.dom_hash",
            "http.favicon.hash": "http.favicon.hash",
            "http.headers_hash": "http.headers_hash",
            "http.html_hash": "http.html_hash",
            "http.robots_hash": "http.robots_hash",
            "http.server_hash": "http.server_hash",
            "http.title_hash": "http.title_hash",
            "screenshot.hash": "screenshot.hash",
            "ssh.hassh": "ssh.hassh",
            "ssl.ja3s": "ssl.ja3s",
            "ssl.jarm": "ssl.jarm",
            "ssl.cert.fingerprint": "ssl.cert.fingerprint",
            "ssl.cert.serial": "ssl.cert.serial",
            "snmp.contact": "snmp.contact",
            "snmp.location": "snmp.location",
            "snmp.name": "snmp.name",
        }
        for path, scalar in _metadata_scalars(entity.metadata):
            leaf = path.rsplit(".", 1)[-1]
            filter_name = next(
                (
                    candidate
                    for suffix, candidate in metadata_path_filter_map.items()
                    if path == suffix or path.endswith("." + suffix)
                ),
                metadata_filter_map.get(leaf),
            )
            if not filter_name:
                continue
            text = str(scalar).strip()
            if not text or len(text) > 256:
                continue
            collision_prone = filter_name.startswith("http.") or filter_name.startswith("screenshot.")
            add(
                ShodanPivotPlan(
                    entity.kind,
                    entity.value,
                    filter_term(filter_name, text),
                    (filter_name,),
                    f"Evidence-driven {filter_name} pivot",
                    relation="matches_shodan_filter",
                    confidence="low" if collision_prone else "medium",
                    allow_search_results=not collision_prone,
                    priority=42 if collision_prone else 30,
                    collision_prone=collision_prone,
                )
            )

    plans.sort(key=lambda plan: (plan.priority, plan.query))
    return plans[: max(0, limit)]
