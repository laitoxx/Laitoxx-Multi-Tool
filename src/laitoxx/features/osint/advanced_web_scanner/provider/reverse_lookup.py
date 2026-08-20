"""Reverse domain discovery providers and domain normalization."""

from __future__ import annotations

import ipaddress
from typing import Any

from .. import provider_common as _common
from ..configuration import auth_mode, credential
from ..models import Entity, ProviderResult, Relation

_cached_json = _common._cached_json
_domain_candidate = _common._domain_candidate
_entity_id = _common._entity_id
_run = _common._run
skipped = _common.skipped


def domain_candidate(value: Any) -> str:
    return _domain_candidate(value)


def domains_from_payload(payload: Any) -> list[str]:
    """Extract domain-shaped fields without treating arbitrary text as evidence."""
    found: set[str] = set()

    def add(value: Any):
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)
            return
        candidate = domain_candidate(value)
        if candidate:
            found.add(candidate)

    def walk(value: Any):
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key in ("domain", "hostname", "host", "subdomain", "name", "idnName"):
                if key in value:
                    add(value[key])
            for key in ("domains", "hostnames", "ptr_records", "results", "records", "data"):
                if key in value:
                    walk(value[key])
        else:
            add(value)

    walk(payload)
    return sorted(found)


def whoisjson_reverse_whois(ip: str) -> ProviderResult:
    """Discover IP-associated domains from WhoisJSON's private database."""
    ip = str(ipaddress.ip_address(ip))
    key = credential("whoisjson")
    if not key:
        return skipped("WhoisJSON Reverse WHOIS", "WHOISJSON_API_KEY is not configured")

    def load():
        data, hit = _cached_json(
            "whoisjson_reverse",
            ip,
            "https://whoisjson.com/api/v1/reverseWhois",
            params={"ip": ip},
            headers={"Authorization": f"TOKEN={key}"},
            ttl=21600,
        )
        discovered = domains_from_payload(data)
        domains = discovered[:50]
        root = _entity_id("ip", ip)
        entities = [
            Entity(
                "domain",
                domain,
                metadata={
                    "discovery": "reverse_whois",
                    "evidence_kind": "private_database_association",
                    "ownership_proven": False,
                },
            )
            for domain in domains
        ]
        relations = [
            Relation(
                root,
                _entity_id("domain", domain),
                "reverse_whois_association",
                "WhoisJSON Reverse WHOIS",
                "medium",
                None,
                "Private-database IP association; this is not proof of common ownership or a current DNS record.",
            )
            for domain in domains
        ]
        status = "cached" if hit else "ok"
        if not domains:
            status = "no_data"
        return ProviderResult(
            "WhoisJSON Reverse WHOIS",
            status,
            {
                "ip": ip,
                "domains": domains,
                "total_domains": len(discovered),
                "truncated": len(discovered) > len(domains),
                "response": data,
            },
            entities,
            relations,
        )

    return _run("WhoisJSON Reverse WHOIS", load)


def botoi_reverse_dns(ip: str) -> ProviderResult:
    """Resolve authoritative PTR records through Botoi (not reverse WHOIS)."""
    ip = str(ipaddress.ip_address(ip))
    key = credential("botoi") if auth_mode("botoi") == "key" else ""
    headers = {"Authorization": f"Bearer {key}"} if key else {}

    def load():
        data, hit = _cached_json(
            "botoi_reverse",
            ip,
            "https://api.botoi.com/v1/ip/reverse",
            method="post",
            body={"ip": ip},
            headers=headers,
            ttl=21600,
        )
        domains = domains_from_payload(data.get("data", data) if isinstance(data, dict) else data)
        root = _entity_id("ip", ip)
        entities = [
            Entity(
                "domain",
                domain,
                metadata={
                    "discovery": "ptr",
                    "evidence_kind": "dns_ptr",
                    "ownership_proven": False,
                },
            )
            for domain in domains
        ]
        relations = [
            Relation(
                root,
                _entity_id("domain", domain),
                "ptr_record",
                "Botoi Reverse DNS",
                "high",
                True,
                "Current PTR record assigned by the IP block operator; it does not prove domain ownership.",
            )
            for domain in domains
        ]
        status = "cached" if hit else "ok"
        if not domains:
            status = "no_data"
        return ProviderResult(
            "Botoi Reverse DNS",
            status,
            {"ip": ip, "ptr_records": domains, "response": data},
            entities,
            relations,
        )

    return _run("Botoi Reverse DNS", load)
