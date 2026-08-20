"""Project individual Shodan search matches into normalized evidence."""

from __future__ import annotations

import ipaddress
import re

from ..domain.exposure import classify_service
from ..domain.exposure import cpe_metadata as _cpe_metadata
from ..models import Entity, Relation, TimelineEvent
from ..provider_common import _domain_candidate, _entity_id, _now


def project_shodan_matches(
    *, name, kind, value, purpose, matches, relation, confidence, entities, relations, timeline, root
):
    for match in matches:
        event_ip = ""
        try:
            event_ip = str(ipaddress.ip_address(str(match.get("ip_str") or "")))
        except ValueError:
            pass
        try:
            port = int(match.get("port"))
        except (TypeError, ValueError):
            port = 0
        hostnames = sorted(
            {
                domain
                for domain in (
                    _domain_candidate(host) for host in [*(match.get("hostnames") or []), *(match.get("domains") or [])]
                )
                if domain
            }
        )
        anchor = _entity_id("ip", event_ip) if event_ip else root
        if event_ip:
            entities.append(Entity("ip", event_ip, metadata={"source": name, "shodan_observed": True}))
            if anchor != root:
                relations.append(
                    Relation(
                        root,
                        anchor,
                        relation,
                        name,
                        confidence,
                        False,
                        f"Filtered Shodan match for {purpose}; verify independently before attribution.",
                        observed_at=str(match.get("timestamp") or ""),
                        state="historical",
                    )
                )
        for hostname in hostnames:
            entities.append(Entity("domain", hostname, metadata={"source": name, "discovery": "shodan_search"}))
            hostname_id = _entity_id("domain", hostname)
            if hostname_id not in {root, anchor}:
                relations.append(
                    Relation(
                        anchor,
                        hostname_id,
                        "observed_hostname",
                        name,
                        "medium",
                        False,
                        observed_at=str(match.get("timestamp") or ""),
                        state="historical",
                    )
                )
        service_id = ""
        if port:
            endpoint_host = event_ip or value
            display_host = f"[{endpoint_host}]" if ":" in endpoint_host else endpoint_host
            service_value = f"{display_host}:{port}"
            product = str(match.get("product") or "")
            version = str(match.get("version") or "")
            title = str((match.get("http") or {}).get("title") or "")
            classification = classify_service(port, product, "Shodan", title)
            entities.append(
                Entity(
                    "service",
                    service_value,
                    metadata={
                        "port": port,
                        "host": value if kind == "domain" else endpoint_host,
                        "ip": event_ip,
                        "transport": str(match.get("transport") or "tcp"),
                        "product": product,
                        "version": version,
                        "title": title,
                        "source": name,
                        "observed_at": str(match.get("timestamp") or ""),
                        "evidence_state": "historical",
                        **classification,
                    },
                )
            )
            service_id = _entity_id("service", service_value)
            relations.append(
                Relation(
                    anchor,
                    service_id,
                    "indexed_service",
                    name,
                    "high",
                    False,
                    f"{classification['category_label']}: {classification['service_name']}; indexed by Shodan.",
                    observed_at=str(match.get("timestamp") or ""),
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

        http_match = match.get("http") or {}
        ssl_match = match.get("ssl") or {}
        fingerprint_values = {
            "favicon": (
                (http_match.get("favicon") or {}).get("hash")
                if isinstance(http_match.get("favicon"), dict)
                else http_match.get("favicon_hash")
            ),
            "http_html": http_match.get("html_hash"),
            "http_headers": http_match.get("headers_hash"),
            "http_title": http_match.get("title_hash"),
            "jarm": ssl_match.get("jarm"),
            "ja3s": ssl_match.get("ja3s"),
        }
        for fingerprint_type, raw_fingerprint in fingerprint_values.items():
            fingerprint = str(raw_fingerprint or "").strip()
            if not fingerprint:
                continue
            fingerprint_value = f"{fingerprint_type}:{fingerprint}"
            fingerprint_id = _entity_id("web_fingerprint", fingerprint_value)
            entities.append(
                Entity(
                    "web_fingerprint",
                    fingerprint_value,
                    label=fingerprint_type.upper(),
                    metadata={
                        "fingerprint_type": fingerprint_type,
                        "fingerprint": fingerprint,
                        "source": name,
                        "collision_prone": fingerprint_type != "certificate",
                    },
                )
            )
            relations.append(
                Relation(
                    service_id or anchor,
                    fingerprint_id,
                    "has_web_fingerprint",
                    name,
                    "medium",
                    False,
                    "Indexed Shodan fingerprint; correlations require independent confirmation.",
                    observed_at=str(match.get("timestamp") or ""),
                    state="historical",
                )
            )

        certificate = ssl_match.get("cert") or {}
        certificate_fingerprints = certificate.get("fingerprint") or {}
        if isinstance(certificate_fingerprints, dict):
            certificate_fingerprint = (
                str(
                    certificate_fingerprints.get("sha256")
                    or certificate_fingerprints.get("sha1")
                    or next(iter(certificate_fingerprints.values()), "")
                )
                .replace(":", "")
                .casefold()
            )
        else:
            certificate_fingerprint = str(certificate_fingerprints or "").replace(":", "").casefold()
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", certificate_fingerprint):
            subject_data = certificate.get("subject") or {}
            issuer_data = certificate.get("issuer") or {}
            certificate_entity = Entity(
                "certificate",
                certificate_fingerprint,
                metadata={
                    "fingerprint_sha256": certificate_fingerprint if len(certificate_fingerprint) == 64 else "",
                    "fingerprint": certificate_fingerprint,
                    "subject_cn": str(subject_data.get("CN") or subject_data.get("cn") or ""),
                    "issuer_cn": str(issuer_data.get("CN") or issuer_data.get("cn") or ""),
                    "source": name,
                    "evidence_state": "historical",
                },
            )
            entities.append(certificate_entity)
            relations.append(
                Relation(
                    service_id or anchor,
                    certificate_entity.id,
                    "presents_certificate",
                    name,
                    "high",
                    False,
                    observed_at=str(match.get("timestamp") or ""),
                    state="historical",
                )
            )
        for cpe in sorted({str(item).strip() for item in match.get("cpe") or [] if str(item).strip()}):
            entities.append(Entity("cpe", cpe, metadata={**_cpe_metadata(cpe), "source": name}))
            relations.append(
                Relation(
                    service_id or anchor,
                    _entity_id("cpe", cpe),
                    "fingerprinted_as",
                    name,
                    "high",
                )
            )
        raw_vulns = match.get("vulns") or []
        vuln_values = raw_vulns.keys() if isinstance(raw_vulns, dict) else raw_vulns
        for cve in sorted(
            {str(item).upper() for item in vuln_values if re.fullmatch(r"CVE-\d{4}-\d{4,}", str(item), re.I)}
        ):
            entities.append(
                Entity(
                    "cve",
                    cve,
                    metadata={
                        "sources": [name],
                        "applicability": "shodan_banner_signal",
                    },
                )
            )
            relations.append(
                Relation(
                    service_id or anchor,
                    _entity_id("cve", cve),
                    "possible_vulnerability",
                    name,
                    "medium",
                    False,
                    "Shodan banner vulnerability signal; validate against the live service.",
                    observed_at=str(match.get("timestamp") or ""),
                    state="candidate",
                )
            )
        timestamp = str(match.get("timestamp") or "")
        if timestamp:
            timeline.append(
                TimelineEvent(
                    timestamp,
                    _now(),
                    name,
                    "service_observed",
                    event_ip or value,
                    str(port or ""),
                    "medium",
                )
            )
    return entities, relations, timeline
