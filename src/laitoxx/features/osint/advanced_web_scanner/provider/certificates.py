"""Certificate transparency and issuance providers."""

from __future__ import annotations

import hashlib
import json

from .. import provider_common as _common
from ..configuration import credential
from ..models import DOMAIN_RE, Entity, ProviderResult, Relation, TimelineEvent

_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run


def crtsh(domain: str) -> ProviderResult:
    def load():
        data, hit = _cached_json(
            "crtsh", domain, "https://crt.sh/", params={"q": f"%.{domain}", "output": "json"}, ttl=21600
        )
        names, related_names, issuers, entities, relations, events = set(), set(), set(), [], [], []
        root = _entity_id("domain", domain)
        for record in data[:500]:
            issuers.add(str(record.get("issuer_name", "")))
            event_time = str(record.get("entry_timestamp") or record.get("not_before") or "")
            fingerprint = str(record.get("sha256") or record.get("serial_number") or record.get("id") or "").strip()
            certificate_id = ""
            if fingerprint:
                certificate = Entity(
                    "certificate",
                    fingerprint,
                    label=fingerprint[:16],
                    metadata={
                        "fingerprint_or_serial": fingerprint,
                        "issuer": record.get("issuer_name"),
                        "not_before": record.get("not_before"),
                        "not_after": record.get("not_after"),
                        "source": "crt.sh",
                        "evidence_state": "historical",
                    },
                )
                entities.append(certificate)
                certificate_id = certificate.id
                relations.append(
                    Relation(
                        root,
                        certificate_id,
                        "certificate_issuance",
                        "crt.sh",
                        "medium",
                        False,
                        "Certificate Transparency record; current deployment is not implied",
                        observed_at=event_time,
                        state="historical",
                    )
                )
            for name in str(record.get("name_value", "")).splitlines():
                host = name.strip().lower().removeprefix("*.").rstrip(".")
                if host == domain or host.endswith("." + domain):
                    names.add(host)
                    if certificate_id:
                        relations.append(
                            Relation(
                                certificate_id,
                                _entity_id("domain", host),
                                "certificate_contains",
                                "crt.sh",
                                "medium",
                                False,
                                "SAN/CN entry in Certificate Transparency",
                                observed_at=event_time,
                                state="historical",
                            )
                        )
                    if event_time:
                        events.append(
                            TimelineEvent(event_time, _now(), "crt.sh", "certificate_contains", domain, host, "medium")
                        )
                elif "." in host and not host.startswith("xn--"):
                    related_names.add(host)
        for host in sorted(names):
            entities.append(Entity("domain", host))
            relations.append(
                Relation(root, _entity_id("domain", host), "certificate_contains", "crt.sh", "medium", None)
            )
        for host in sorted(related_names)[:50]:
            entities.append(Entity("domain", host, metadata={"discovery": "certificate_co_occurrence"}))
            relations.append(
                Relation(
                    root,
                    _entity_id("domain", host),
                    "co_certificate_domain",
                    "crt.sh",
                    "low",
                    None,
                    "Appeared in a certificate record that also matched the target; common ownership is not proven.",
                )
            )
        return ProviderResult(
            "crt.sh",
            "cached" if hit else "ok",
            {
                "names": sorted(names),
                "related_names": sorted(related_names),
                "issuers": sorted(filter(None, issuers)),
                "record_count": len(data),
                "records": data[:200],
            },
            entities,
            relations,
            events,
        )

    return _run("crt.sh", load)


def certspotter(domain: str) -> ProviderResult:
    """Search CT through Cert Spotter and preserve certificate fingerprints."""
    token = credential("certspotter")

    def load():
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        data, hit = _cached_json(
            "certspotter",
            domain,
            "https://api.certspotter.com/v1/issuances",
            params={
                "domain": domain,
                "include_subdomains": "true",
                "expand": "dns_names,issuer",
                "match_wildcards": "true",
            },
            headers=headers,
            ttl=21600,
        )
        records = data if isinstance(data, list) else data.get("issuances", [])
        entities: list[Entity] = []
        relations: list[Relation] = []
        timeline: list[TimelineEvent] = []
        root = _entity_id("domain", domain)
        for record in records[:500]:
            if not isinstance(record, dict):
                continue
            fingerprint = str(record.get("cert_sha256") or record.get("tbs_sha256") or record.get("id") or "").strip()
            if not fingerprint:
                fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
            certificate = Entity(
                "certificate",
                fingerprint,
                label=fingerprint[:16],
                metadata={
                    "fingerprint_sha256": fingerprint,
                    "issuer": record.get("issuer"),
                    "not_before": record.get("not_before"),
                    "not_after": record.get("not_after"),
                    "source": "Cert Spotter",
                    "evidence_state": "historical",
                },
            )
            entities.append(certificate)
            relations.append(
                Relation(
                    root,
                    certificate.id,
                    "certificate_issuance",
                    "Cert Spotter",
                    "high",
                    False,
                    "Certificate Transparency issuance; current deployment is not implied",
                    observed_at=str(record.get("not_before") or ""),
                    state="historical",
                )
            )
            for name in record.get("dns_names", []) or []:
                hostname = str(name).casefold().removeprefix("*.").rstrip(".")
                if not DOMAIN_RE.fullmatch(hostname):
                    continue
                entities.append(Entity("domain", hostname, metadata={"source": "Cert Spotter"}))
                relations.append(
                    Relation(
                        certificate.id,
                        _entity_id("domain", hostname),
                        "certificate_contains",
                        "Cert Spotter",
                        "medium",
                        False,
                        "SAN entry; shared ownership is not implied",
                        observed_at=str(record.get("not_before") or ""),
                        state="historical",
                    )
                )
                if hostname == domain or hostname.endswith("." + domain):
                    relations.append(
                        Relation(
                            root,
                            _entity_id("domain", hostname),
                            "certificate_contains",
                            "Cert Spotter",
                            "medium",
                            None,
                            "In-scope hostname observed in Certificate Transparency",
                            observed_at=str(record.get("not_before") or ""),
                            state="candidate",
                        )
                    )
            if record.get("not_before"):
                timeline.append(
                    TimelineEvent(
                        str(record["not_before"]),
                        _now(),
                        "Cert Spotter",
                        "certificate_issued",
                        domain,
                        fingerprint,
                        "high",
                    )
                )
        return ProviderResult(
            "Cert Spotter",
            "cached" if hit else "ok",
            {"issuances": records[:500], "count": len(records)},
            entities,
            relations,
            timeline,
        )

    return _run("Cert Spotter", load)
