"""IP ownership, routing history and RPKI providers."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .. import provider_common as _common
from ..configuration import credential
from ..models import Entity, ProviderResult, Relation, TimelineEvent

_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run
skipped = _common.skipped


def ipinfo(ip: str) -> ProviderResult:
    token = credential("ipinfo")
    if not token:
        return skipped("IPinfo Lite", "IPINFO_TOKEN is not configured")

    def load():
        data, hit = _cached_json(
            "ipinfo", ip, f"https://api.ipinfo.io/lite/{quote(ip)}", params={"token": token}, ttl=21600
        )
        entities, relations = [], []
        root = _entity_id("ip", ip)
        asn = str(data.get("asn", ""))
        if asn:
            entities.append(
                Entity("asn", asn, metadata={"name": data.get("as_name"), "country": data.get("country_code")})
            )
            relations.append(Relation(root, _entity_id("asn", asn), "announced_by", "IPinfo Lite", "high", True))
        return ProviderResult("IPinfo Lite", "cached" if hit else "ok", data, entities, relations)

    return _run("IPinfo Lite", load)


def ripestat(value: str) -> ProviderResult:
    def load():
        resource = value.removeprefix("AS") if value.upper().startswith("AS") else value
        endpoint = "as-overview" if value.upper().startswith("AS") else "network-info"
        data, hit = _cached_json(
            "ripestat",
            f"{endpoint}:{resource}",
            f"https://stat.ripe.net/data/{endpoint}/data.json",
            params={"resource": resource},
            ttl=3600,
        )
        payload = data.get("data", {})
        entities, relations = [], []
        root_kind = "asn" if value.upper().startswith("AS") else "ip"
        root = _entity_id(root_kind, value)
        for asn in payload.get("asns", []) or ([payload.get("holder")] if root_kind == "asn" else []):
            if asn and str(asn).isdigit():
                as_value = f"AS{asn}"
                entities.append(Entity("asn", as_value))
                relations.append(
                    Relation(root, _entity_id("asn", as_value), "routing_origin", "RIPEstat", "high", True)
                )
        prefix = payload.get("prefix")
        if prefix:
            entities.append(Entity("prefix", str(prefix)))
            relations.append(
                Relation(root, _entity_id("prefix", str(prefix)), "inside_prefix", "RIPEstat", "high", True)
            )
        return ProviderResult("RIPEstat", "cached" if hit else "ok", payload, entities, relations)

    return _run("RIPEstat", load)


def ripestat_routing(value: str, prefix: str = "", asn: str = "") -> ProviderResult:
    """Add bounded RPKI and routing-history context to an IP/prefix/ASN."""

    def load():
        root_kind = "asn" if value.upper().startswith("AS") else "prefix" if "/" in value else "ip"
        root = _entity_id(root_kind, value)
        entities: list[Entity] = []
        relations: list[Relation] = []
        timeline: list[TimelineEvent] = []
        payload: dict[str, Any] = {}
        cached = True

        resource = value
        routing, hit = _cached_json(
            "ripestat_routing",
            f"routing:{resource}",
            "https://stat.ripe.net/data/routing-history/data.json",
            params={"resource": resource, "max_rows": 250, "normalise_visibility": "true"},
            ttl=21600,
        )
        cached &= hit
        history = routing.get("data", {}).get("by_origin", []) or []
        compact_history = []
        for origin_group in history[:20]:
            origin = str(origin_group.get("origin") or "")
            for prefix_group in (origin_group.get("prefixes") or [])[:30]:
                routed_prefix = str(prefix_group.get("prefix") or "")
                compact_history.append(
                    {
                        "origin": origin,
                        "prefix": routed_prefix,
                        "timelines": (prefix_group.get("timelines") or [])[-5:],
                    }
                )
                if origin:
                    origin_value = origin if origin.upper().startswith("AS") else f"AS{origin}"
                    entities.append(Entity("asn", origin_value))
                    relations.append(
                        Relation(
                            _entity_id("prefix", routed_prefix) if routed_prefix else root,
                            _entity_id("asn", origin_value),
                            "announced_by",
                            "RIPEstat Routing History",
                            "high",
                            None,
                            "Observed by RIPE RIS route collectors",
                            state="candidate",
                        )
                    )
                for period in (prefix_group.get("timelines") or [])[-5:]:
                    start = str(period.get("starttime") or "")
                    if start:
                        timeline.append(
                            TimelineEvent(
                                start,
                                _now(),
                                "RIPEstat Routing History",
                                "route_announced",
                                routed_prefix or value,
                                origin,
                                "high",
                            )
                        )
        payload["routing_history"] = compact_history

        rpki_prefix = prefix or (value if "/" in value else "")
        rpki_asn = asn or (value if value.upper().startswith("AS") else "")
        if rpki_prefix and rpki_asn:
            validation, hit = _cached_json(
                "ripestat_rpki",
                f"{rpki_asn}:{rpki_prefix}",
                "https://stat.ripe.net/data/rpki-validation/data.json",
                params={"resource": rpki_asn, "prefix": rpki_prefix},
                ttl=3600,
            )
            cached &= hit
            rpki = validation.get("data", {}) or {}
            status = str(rpki.get("status") or "unknown").lower()
            payload["rpki"] = rpki
            rpki_entity = Entity(
                "rpki_status",
                f"{rpki_asn}:{rpki_prefix}",
                label=status.upper(),
                metadata={
                    "status": status,
                    "asn": rpki_asn,
                    "prefix": rpki_prefix,
                    "severity": "high" if status == "invalid" else "info",
                    "explanation": (
                        "The observed BGP origin is RPKI-invalid."
                        if status == "invalid"
                        else "RPKI origin validation result for the observed prefix and ASN."
                    ),
                },
            )
            entities.append(rpki_entity)
            relations.append(
                Relation(
                    _entity_id("prefix", rpki_prefix),
                    rpki_entity.id,
                    "has_rpki_status",
                    "RIPEstat RPKI",
                    "high",
                    True,
                    rpki_entity.metadata["explanation"],
                    checked_at=_now(),
                    state="live",
                )
            )
        return ProviderResult(
            "RIPEstat Routing & RPKI",
            "cached" if cached else "ok",
            payload,
            entities,
            relations,
            timeline,
        )

    return _run("RIPEstat Routing & RPKI", load)
