"""Threat-intelligence providers."""

from __future__ import annotations

from urllib.parse import quote

from .. import provider_common as _common
from ..configuration import credential
from ..models import Entity, ProviderResult, Relation, TimelineEvent

_OTX_LOCK = _common._OTX_LOCK
_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run
skipped = _common.skipped


def otx(kind: str, value: str) -> ProviderResult:
    if kind not in {"ip", "domain"}:
        return skipped("AlienVault OTX", "Not applicable")

    def load():
        indicator_type = "IPv4" if kind == "ip" else "domain"
        headers = {}
        key = credential("otx")
        if key:
            headers["X-OTX-API-KEY"] = key
        with _OTX_LOCK:
            data, hit = _cached_json(
                "otx",
                f"{kind}:{value}",
                f"https://otx.alienvault.com/api/v1/indicators/{indicator_type}/{quote(value)}/passive_dns",
                headers=headers,
                ttl=10800,
            )
        entities, relations, events = [], [], []
        root = _entity_id(kind, value)
        for record in data.get("passive_dns", []):
            address = str(record.get("address", "")).rstrip(".")
            hostname = str(record.get("hostname", "")).lower().rstrip(".")
            peer = address if kind == "domain" else hostname
            peer_kind = "ip" if kind == "domain" else "domain"
            if not peer:
                continue
            entities.append(Entity(peer_kind, peer))
            relation_source = root if kind == "domain" else _entity_id(peer_kind, peer)
            relation_target = _entity_id(peer_kind, peer) if kind == "domain" else root
            relations.append(
                Relation(relation_source, relation_target, "historical_resolves_to", "AlienVault OTX", "medium", False)
            )
            event_time = str(record.get("last") or record.get("first") or "")
            if event_time:
                events.append(
                    TimelineEvent(event_time, _now(), "AlienVault OTX", "historical_resolves_to", value, peer, "medium")
                )
        return ProviderResult("AlienVault OTX", "cached" if hit else "ok", data, entities, relations, events)

    return _run("AlienVault OTX", load)


def abuseipdb(ip: str) -> ProviderResult:
    key = credential("abuseipdb")
    if not key:
        return skipped("AbuseIPDB", "ABUSEIPDB_API_KEY is not configured")

    def load():
        data, hit = _cached_json(
            "abuseipdb",
            ip,
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""},
            headers={"Key": key, "Accept": "application/json"},
            ttl=10800,
        )
        return ProviderResult("AbuseIPDB", "cached" if hit else "ok", data.get("data", data))

    return _run("AbuseIPDB", load)
