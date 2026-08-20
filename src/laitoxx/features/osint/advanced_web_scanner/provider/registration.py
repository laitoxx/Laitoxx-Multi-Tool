"""Registration Data Access Protocol provider."""

from __future__ import annotations

import ipaddress
from urllib.parse import quote, urlparse

from requests import HTTPError, RequestException, Timeout

from .. import provider_common as _common
from ..models import Entity, ProviderResult, Relation, Target, TimelineEvent

_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run
skipped = _common.skipped


def _authoritative_rdap_base(kind: str, query: str) -> str:
    registry = "asn" if kind == "asn" else "dns" if kind == "domain" else "ipv6" if ":" in query else "ipv4"
    data, _hit = _cached_json(
        "rdap_bootstrap",
        registry,
        f"https://data.iana.org/rdap/{registry}.json",
        ttl=7 * 86400,
    )
    for resources, urls in data.get("services", []) or []:
        matched = False
        if registry == "dns":
            matched = query.casefold().rsplit(".", 1)[-1] in {str(item).casefold() for item in resources}
        elif registry == "asn":
            number = int(query.removeprefix("AS"))
            for resource in resources:
                start, _separator, end = str(resource).partition("-")
                if int(start) <= number <= int(end or start):
                    matched = True
                    break
        else:
            address = ipaddress.ip_address(query)
            for resource in resources:
                try:
                    if address in ipaddress.ip_network(str(resource), strict=False):
                        matched = True
                        break
                except ValueError:
                    continue
        if matched and urls:
            return str(urls[0]).rstrip("/")
    raise LookupError(f"IANA RDAP bootstrap has no authoritative service for {query}")


def rdap(target: Target) -> ProviderResult:
    if target.kind not in {"ip", "domain", "url", "asn"}:
        return skipped("RDAP", "Not applicable")

    def load():
        value = urlparse(target.value).hostname if target.kind == "url" else target.value
        kind = "domain" if target.kind == "url" else target.kind
        path_kind = "autnum" if kind == "asn" else kind
        query = value.removeprefix("AS") if kind == "asn" else value
        endpoint = f"https://rdap.org/{path_kind}/{quote(query, safe=':')}"
        source_name = "RDAP.org"
        try:
            data, hit = _cached_json("rdap", f"{kind}:{query}", endpoint, ttl=21600)
        except (HTTPError, RequestException, Timeout):
            base = _authoritative_rdap_base(kind, query)
            endpoint = f"{base}/{path_kind}/{quote(query, safe=':')}"
            data, hit = _cached_json(
                "rdap_authoritative",
                f"{kind}:{query}:{base}",
                endpoint,
                ttl=21600,
            )
            source_name = "Authoritative RDAP"
        entities, relations, events = [], [], []
        root_kind = "domain" if target.kind == "url" else target.kind
        root_value = value if target.kind == "url" else target.value
        root = _entity_id(root_kind, root_value)
        handle = str(data.get("handle", ""))
        name = str(data.get("name", ""))
        if kind == "domain" and not name:
            for rdap_entity in data.get("entities", []):
                if "registrant" not in rdap_entity.get("roles", []):
                    continue
                vcard = rdap_entity.get("vcardArray", [None, []])
                for field in vcard[1] if len(vcard) > 1 else []:
                    if field and field[0] == "fn" and len(field) > 3:
                        name = str(field[3]).strip()
                        break
        if name:
            entities.append(
                Entity("organization", name, metadata={"handle": handle, "role": "registrant", "source": source_name})
            )
            relations.append(
                Relation(
                    root,
                    _entity_id("organization", name),
                    "registered_to",
                    source_name,
                    "medium",
                    None,
                    "RDAP registration record; privacy/proxy data may be present",
                    checked_at=_now(),
                    state="candidate",
                )
            )
        for nameserver in data.get("nameservers", []):
            host = str(nameserver.get("ldhName", "")).lower().rstrip(".")
            if host:
                entities.append(Entity("domain", host))
                relations.append(
                    Relation(
                        root,
                        _entity_id("domain", host),
                        "uses_nameserver",
                        source_name,
                        "high",
                        True,
                        checked_at=_now(),
                        state="live",
                    )
                )
        for event in data.get("events", []):
            date = str(event.get("eventDate", ""))
            action = str(event.get("eventAction", "rdap_event"))
            if date:
                events.append(TimelineEvent(date, _now(), source_name, action, target.value, confidence="high"))
        payload = dict(data)
        payload["_lookup_endpoint"] = endpoint
        payload["_lookup_source"] = source_name
        return ProviderResult("RDAP", "cached" if hit else "ok", payload, entities, relations, events)

    return _run("RDAP", load)
