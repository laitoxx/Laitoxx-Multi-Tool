"""VirusTotal and urlscan.io providers."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import quote

from .. import provider_common as _common
from ..configuration import credential
from ..models import Entity, ProviderResult, Relation, TimelineEvent

_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run
skipped = _common.skipped


def virustotal(kind: str, value: str) -> ProviderResult:
    key = credential("virustotal")
    if not key:
        return skipped("VirusTotal", "VIRUSTOTAL_API_KEY is not configured")
    vt_kind = "ip_addresses" if kind == "ip" else "domains"

    def load():
        headers = {"x-apikey": key}
        base, hit1 = _cached_json(
            "virustotal",
            f"{kind}:{value}",
            f"https://www.virustotal.com/api/v3/{vt_kind}/{quote(value)}",
            headers=headers,
            ttl=10800,
        )
        resolutions, hit2 = _cached_json(
            "virustotal_resolutions",
            f"{kind}:{value}",
            f"https://www.virustotal.com/api/v3/{vt_kind}/{quote(value)}/resolutions",
            headers=headers,
            params={"limit": 40},
            ttl=10800,
        )
        entities, relations, events = [], [], []
        root = _entity_id(kind, value)
        for record in resolutions.get("data", []):
            attrs = record.get("attributes", {})
            peer = attrs.get("ip_address") if kind == "domain" else attrs.get("host_name")
            peer_kind = "ip" if kind == "domain" else "domain"
            if not peer:
                continue
            peer = str(peer).lower().rstrip(".")
            entities.append(Entity(peer_kind, peer))
            relation_source = root if kind == "domain" else _entity_id(peer_kind, peer)
            relation_target = _entity_id(peer_kind, peer) if kind == "domain" else root
            relations.append(
                Relation(relation_source, relation_target, "historical_resolves_to", "VirusTotal", "medium", False)
            )
            timestamp = attrs.get("date")
            if timestamp:
                event_time = datetime.fromtimestamp(int(timestamp), UTC).isoformat()
                events.append(
                    TimelineEvent(event_time, _now(), "VirusTotal", "historical_resolves_to", value, peer, "medium")
                )
        return ProviderResult(
            "VirusTotal",
            "cached" if hit1 and hit2 else "ok",
            {"object": base, "resolutions": resolutions},
            entities,
            relations,
            events,
        )

    return _run("VirusTotal", load)


def urlscan(kind: str, value: str) -> ProviderResult:
    query_field = "ip" if kind == "ip" else "domain"
    key = credential("urlscan")
    headers = {"api-key": key} if key else {}

    def load():
        escaped_value = re.sub(r'([+\-=!(){}\[\]^"~*?:\\/]|&&|\|\||[<>])', r"\\\1", value)
        data, hit = _cached_json(
            "urlscan",
            f"{kind}:{value}",
            "https://urlscan.io/api/v1/search/",
            params={"q": f"{query_field}:{escaped_value}", "size": 100},
            headers=headers,
            ttl=10800,
        )
        events, entities, relations = [], [], []
        root = _entity_id(kind, value)
        for item in data.get("results", []):
            task, page = item.get("task", {}), item.get("page", {})
            timestamp = str(task.get("time", ""))
            observed_ip = str(page.get("ip", ""))
            observed_domain = str(page.get("domain", "")).lower().rstrip(".")
            observed = observed_ip or observed_domain
            if timestamp:
                events.append(TimelineEvent(timestamp, _now(), "urlscan.io", "scanned_on", value, observed, "medium"))
            for peer_kind, peer in (("ip", observed_ip), ("domain", observed_domain)):
                if peer and not (peer_kind == kind and peer == value):
                    entities.append(Entity(peer_kind, peer))
                    relations.append(
                        Relation(root, _entity_id(peer_kind, peer), "scanned_on", "urlscan.io", "medium", False)
                    )
        return ProviderResult(
            "urlscan.io",
            "cached" if hit else "ok",
            {"results": data.get("results", [])[:100]},
            entities,
            relations,
            events,
        )

    return _run("urlscan.io", load)
