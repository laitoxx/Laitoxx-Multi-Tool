"""LeakIX service and leak-event enrichment."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re

from requests import RequestException

from .. import provider_common as _common
from ..configuration import credential
from ..domain.exposure import classify_service
from ..domain.leakix import compact_event as _compact_leakix_event
from ..domain.leakix import redact_text as _redact_leakix_text
from ..models import Entity, ProviderResult, Relation, TimelineEvent
from ..quota import QuotaExceeded
from .reverse_lookup import domain_candidate as _domain_candidate

_entity_id = _common._entity_id
_leakix_cached_json = _common._leakix_cached_json
_now = _common._now
_run = _common._run
_safe_error = _common._safe_error
skipped = _common.skipped


def leakix(kind: str, value: str) -> ProviderResult:
    """Retrieve both LeakIX search scopes for an exact IP/domain pivot."""
    name = "LeakIX"
    key = credential("leakix")
    if not key:
        return skipped(name, "LEAKIX_API_KEY is not configured")
    if kind == "ip":
        value = str(ipaddress.ip_address(value))
        query = f"+ip:{value}"
    elif kind == "domain":
        value = _domain_candidate(value)
        if not value:
            return ProviderResult(name, "no_data", error="LeakIX requires a valid IP or domain")
        # The LeakIX DNS field matches the domain and its subdomains.
        query = f"+host:{value}"
    else:
        return skipped(name, f"LeakIX does not support target type: {kind}")

    def load():
        scoped_events: dict[str, list[dict]] = {"service": [], "leak": []}
        scope_hits: dict[str, bool] = {}
        scope_errors: dict[str, str] = {}
        failures: list[Exception] = []
        for scope_name in ("service", "leak"):
            try:
                data, hit = _leakix_cached_json(
                    f"leakix_search_{scope_name}",
                    f"{kind}:{value}:page:0",
                    "https://leakix.net/search",
                    {"accept": "application/json", "api-key": key},
                    params={"q": query, "scope": scope_name, "page": 0},
                )
                events = data if isinstance(data, list) else []
                scoped_events[scope_name] = [event for event in events if isinstance(event, dict)][:100]
                scope_hits[scope_name] = hit
            except (QuotaExceeded, RequestException, ValueError) as exc:
                failures.append(exc)
                scope_errors[scope_name] = _safe_error(exc)
                scope_hits[scope_name] = False
        if len(failures) == 2:
            raise failures[0]

        def deduplicate_events(events: list[dict]) -> list[dict]:
            unique: dict[str, dict] = {}
            for event in events:
                fingerprint = str(event.get("event_fingerprint") or "").strip()
                if not fingerprint:
                    identity = {
                        "type": event.get("event_type"),
                        "source": event.get("event_source"),
                        "ip": event.get("ip"),
                        "host": event.get("host"),
                        "port": event.get("port"),
                        "time": event.get("time"),
                    }
                    fingerprint = hashlib.sha256(
                        json.dumps(identity, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest()
                unique.setdefault(fingerprint, event)
            return list(unique.values())

        services = deduplicate_events(scoped_events["service"])
        leaks = deduplicate_events(scoped_events["leak"])
        entities: list[Entity] = []
        relations: list[Relation] = []
        timeline: list[TimelineEvent] = []
        root = _entity_id(kind, value)

        for is_leak, event in [(False, item) for item in services] + [(True, item) for item in leaks]:
            event_source = str(event.get("event_source") or "LeakIX")
            summary = _redact_leakix_text(event.get("summary")).strip()
            event_ip = ""
            try:
                event_ip = str(ipaddress.ip_address(str(event.get("ip") or "")))
            except ValueError:
                pass
            host = _domain_candidate(event.get("host")) or _domain_candidate(event.get("reverse"))
            if event_ip:
                entities.append(Entity("ip", event_ip, metadata={"source": name, "leakix_observed": True}))
                if _entity_id("ip", event_ip) != root:
                    relations.append(
                        Relation(
                            root,
                            _entity_id("ip", event_ip),
                            "leakix_observed_on",
                            name,
                            "medium",
                            None,
                            "Indexed host association; verify current DNS before attribution.",
                        )
                    )
            if host:
                entities.append(Entity("domain", host, metadata={"source": name, "discovery": "leakix"}))
                if _entity_id("domain", host) != root:
                    relations.append(
                        Relation(
                            root,
                            _entity_id("domain", host),
                            "leakix_observed_host",
                            name,
                            "medium",
                            None,
                        )
                    )

            try:
                port = int(event.get("port"))
            except (TypeError, ValueError):
                port = 0
            service_data = event.get("service") or {}
            software = service_data.get("software") or {}
            product = str(software.get("name") or "")
            version = str(software.get("version") or "")
            event_time = str(event.get("time") or event.get("update_date") or event.get("creation_date") or "")
            http_data = event.get("http") or {}
            title = str(http_data.get("title") or "")
            anchor = _entity_id("ip", event_ip) if event_ip else _entity_id("domain", host) if host else root
            service_id = ""
            if port:
                endpoint_host = host or event_ip or value
                display_host = f"[{endpoint_host}]" if ":" in endpoint_host else endpoint_host
                service_value = f"{display_host}:{port}"
                classification = classify_service(port, product, event_source, title)
                service_metadata = {
                    "port": port,
                    "host": host or event_ip,
                    "ip": event_ip,
                    "protocol": str(event.get("protocol") or ""),
                    "transport": event.get("transport") or [],
                    "product": product,
                    "version": version,
                    "title": title,
                    "source": name,
                    "leakix_event_source": event_source,
                    "leakix_summary": summary[:1000],
                    "observed_at": event_time,
                    "evidence_state": "historical",
                    **classification,
                }
                entities.append(Entity("service", service_value, metadata=service_metadata))
                service_id = _entity_id("service", service_value)
                relations.append(
                    Relation(
                        anchor,
                        service_id,
                        "indexed_service",
                        name,
                        "high",
                        False,
                        f"{classification['category_label']}: {classification['service_name']}; indexed observation, revalidate current reachability",
                        observed_at=event_time,
                        state="historical",
                    )
                )
                if product:
                    technology_value = f"{product} {version}".strip()
                    entities.append(
                        Entity(
                            "technology",
                            technology_value,
                            metadata={
                                "product": product,
                                "version": version,
                                "source": name,
                            },
                        )
                    )
                    relations.append(
                        Relation(
                            service_id,
                            _entity_id("technology", technology_value),
                            "fingerprinted_as",
                            name,
                            "high",
                            None,
                        )
                    )

            finding_id = ""
            if is_leak:
                leak_data = event.get("leak") or {}
                severity = str(leak_data.get("severity") or "unknown").lower()
                leak_type = str(leak_data.get("type") or event_source).strip()
                fingerprint = str(
                    event.get("event_fingerprint")
                    or hashlib.sha256(json.dumps(event, sort_keys=True, default=str).encode("utf-8")).hexdigest()
                )
                finding_value = f"leakix:{fingerprint[:24]}"
                finding_id = _entity_id("finding", finding_value)
                entities.append(
                    Entity(
                        "finding",
                        finding_value,
                        label=f"LeakIX · {leak_type}",
                        metadata={
                            "source": name,
                            "finding_type": leak_type,
                            "severity": severity,
                            "stage": leak_data.get("stage"),
                            "dataset": leak_data.get("dataset") or {},
                            "credentials": {
                                "noauth": bool((service_data.get("credentials") or {}).get("noauth")),
                                "username_present": bool((service_data.get("credentials") or {}).get("username")),
                                "password_present": bool((service_data.get("credentials") or {}).get("password")),
                                "key_present": bool((service_data.get("credentials") or {}).get("key")),
                                "raw_present": bool((service_data.get("credentials") or {}).get("raw")),
                            },
                            "plugin": event_source,
                            "summary": summary[:2000],
                            "observed_at": event_time,
                            "confidence_state": "reported_by_source",
                            "evidence_state": "historical",
                        },
                    )
                )
                relations.append(
                    Relation(
                        service_id or anchor,
                        finding_id,
                        "detected_exposure",
                        name,
                        "high",
                        False,
                        summary[:500] or f"LeakIX {leak_type} finding",
                        observed_at=event_time,
                        state="historical",
                    )
                )

            cves = sorted(set(re.findall(r"CVE-\d{4}-\d{4,}", json.dumps(event), re.I)))
            for cve in cves[:20]:
                cve = cve.upper()
                entities.append(
                    Entity(
                        "cve",
                        cve,
                        metadata={
                            "sources": [name],
                            "validation_sources": [name] if is_leak else [],
                            "leakix_plugin": event_source,
                        },
                    )
                )
                relations.append(
                    Relation(
                        finding_id or service_id or anchor,
                        _entity_id("cve", cve),
                        "validated_vulnerability" if is_leak else "possible_vulnerability",
                        name,
                        "high" if is_leak else "medium",
                        False if is_leak else None,
                        f"{event_source}: {summary[:400]}".rstrip(": "),
                        observed_at=event_time,
                        state="historical" if is_leak else "candidate",
                    )
                )
            if event_time and not event_time.startswith("0001-"):
                timeline.append(
                    TimelineEvent(
                        event_time,
                        _now(),
                        name,
                        "leak_detected" if is_leak else "service_observed",
                        host or event_ip or value,
                        event_source,
                        "high" if is_leak else "medium",
                    )
                )

        successful_scopes = [scope_name for scope_name in ("service", "leak") if scope_name not in scope_errors]
        status = "cached" if successful_scopes and all(scope_hits[name] for name in successful_scopes) else "ok"
        if not services and not leaks:
            status = "no_data"
        compact = {
            "target": {"kind": kind, "value": value},
            "query": query,
            "scopes": {
                scope_name: {
                    "status": (
                        "error" if scope_name in scope_errors else "cached" if scope_hits.get(scope_name) else "ok"
                    ),
                    "count": len(services if scope_name == "service" else leaks),
                    "error": scope_errors.get(scope_name, ""),
                }
                for scope_name in ("service", "leak")
            },
            "service_count": len(services),
            "leak_count": len(leaks),
            "services": [_compact_leakix_event(event) for event in services],
            "leaks": [_compact_leakix_event(event) for event in leaks],
        }
        error = "; ".join(f"{scope_name}: {message}" for scope_name, message in scope_errors.items())
        return ProviderResult(name, status, compact, entities, relations, timeline, error=error)

    return _run(name, load)
