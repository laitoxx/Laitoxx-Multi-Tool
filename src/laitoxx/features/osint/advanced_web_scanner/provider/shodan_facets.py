"""Project Shodan aggregate facets into normalized evidence."""

from __future__ import annotations

import ipaddress
import re

from ..domain.exposure import classify_service
from ..domain.exposure import cpe_metadata as _cpe_metadata
from ..models import Entity, Relation, TimelineEvent
from ..provider_common import _domain_candidate, _entity_id


def _shodan_facet_values(data: dict, name: str) -> list[dict]:
    values = (data.get("facets") or {}).get(name) or []
    return [item for item in values if isinstance(item, dict) and item.get("value") is not None]


def project_shodan_facets(
    *, name, kind, value, query, purpose, required_filters, count_data, relation, confidence, collision_prone
):
    entities: list[Entity] = []
    relations: list[Relation] = []
    timeline: list[TimelineEvent] = []
    root = _entity_id(kind, value)
    facets = count_data.get("facets") or {}
    entities.append(
        Entity(
            kind,
            value,
            metadata={
                "source": name,
                "shodan_query": query,
                "shodan_filter_purpose": purpose,
                "shodan_required_filters": list(required_filters),
                "shodan_indexed_services": int(count_data.get("total") or 0),
                "shodan_facets": facets,
                "shodan_timeframe": "30_days",
                "collision_prone": collision_prone,
            },
        )
    )

    ports: set[int] = set()
    for item in _shodan_facet_values(count_data, "port"):
        try:
            ports.add(int(item["value"]))
        except (TypeError, ValueError):
            pass
    for port in sorted(ports) if kind in {"ip", "domain"} else []:
        endpoint_host = f"[{value}]" if ":" in value else value
        service_value = f"{endpoint_host}:{port}"
        classification = classify_service(port)
        count = next(
            (item.get("count") for item in _shodan_facet_values(count_data, "port") if str(item["value"]) == str(port)),
            None,
        )
        entities.append(
            Entity(
                "service",
                service_value,
                metadata={
                    "port": port,
                    "host": value,
                    "ip": value if kind == "ip" else "",
                    "source": name,
                    "shodan_facet_count": count,
                    "evidence_state": "historical",
                    **classification,
                },
            )
        )
        relations.append(
            Relation(
                root,
                _entity_id("service", service_value),
                "indexed_service",
                name,
                "medium",
                False,
                "Shodan facet observed this port during its rolling search timeframe; revalidate reachability.",
                state="historical",
                supporting_sources=[name],
            )
        )

    for item in _shodan_facet_values(count_data, "product"):
        product = str(item["value"]).strip()
        if not product:
            continue
        entities.append(
            Entity(
                "technology",
                product,
                metadata={
                    "product": product,
                    "source": name,
                    "shodan_facet_count": item.get("count"),
                },
            )
        )
        relations.append(
            Relation(
                root,
                _entity_id("technology", product),
                "indexed_product",
                name,
                "medium",
                False,
                "Aggregated Shodan product facet for the scoped target.",
                state="historical",
            )
        )

    for item in _shodan_facet_values(count_data, "ip"):
        try:
            related_ip = str(ipaddress.ip_address(str(item["value"])))
        except ValueError:
            continue
        related_id = _entity_id("ip", related_ip)
        entities.append(
            Entity(
                "ip",
                related_ip,
                metadata={
                    "source": name,
                    "shodan_facet_count": item.get("count"),
                    "evidence_state": "historical",
                },
            )
        )
        if related_id != root:
            relations.append(
                Relation(
                    root,
                    related_id,
                    relation,
                    name,
                    confidence,
                    False,
                    f"Shodan {purpose}; aggregate IP facet, not proof of current ownership.",
                    state="historical",
                )
            )

    related_domains: set[str] = set()
    for facet_name in ("domain", "hostname"):
        for item in _shodan_facet_values(count_data, facet_name):
            domain = _domain_candidate(item["value"])
            if domain:
                related_domains.add(domain)
    for domain in sorted(related_domains):
        domain_id = _entity_id("domain", domain)
        entities.append(
            Entity(
                "domain",
                domain,
                metadata={
                    "source": name,
                    "discovery": "shodan_filter_facet",
                    "evidence_state": "historical",
                },
            )
        )
        if domain_id != root:
            relations.append(
                Relation(
                    root,
                    domain_id,
                    relation,
                    name,
                    confidence,
                    False,
                    f"Shodan {purpose}; aggregate hostname/domain facet.",
                    state="historical",
                )
            )

    for item in _shodan_facet_values(count_data, "cpe"):
        cpe = str(item["value"]).strip()
        if not cpe.startswith("cpe:"):
            continue
        entities.append(
            Entity(
                "cpe",
                cpe,
                metadata={
                    **_cpe_metadata(cpe),
                    "source": name,
                    "shodan_facet_count": item.get("count"),
                },
            )
        )
        cpe_id = _entity_id("cpe", cpe)
        if cpe_id != root:
            relations.append(
                Relation(
                    root,
                    cpe_id,
                    "indexed_cpe",
                    name,
                    "medium",
                    False,
                    state="historical",
                )
            )

    facet_cves = {
        str(item["value"]).upper()
        for item in _shodan_facet_values(count_data, "vuln")
        if re.fullmatch(r"CVE-\d{4}-\d{4,}", str(item["value"]), re.I)
    }
    for cve in sorted(facet_cves):
        entities.append(
            Entity(
                "cve",
                cve,
                metadata={
                    "sources": [name],
                    "applicability": "shodan_facet_signal",
                },
            )
        )
        relations.append(
            Relation(
                root,
                _entity_id("cve", cve),
                "possible_vulnerability",
                name,
                "medium",
                False,
                "CVE appeared in Shodan's filtered facet data; applicability is not validated.",
                state="candidate",
            )
        )

    return entities, relations, timeline, root, facets
