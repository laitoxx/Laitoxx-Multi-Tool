"""Public service exposure providers."""

from __future__ import annotations

import ipaddress
from urllib.parse import quote

from .. import provider_common as _common
from ..domain.exposure import classify_service, cpe_metadata
from ..models import Entity, ProviderResult, Relation

_cached_json = _common._cached_json
_entity_id = _common._entity_id
_run = _common._run
_cpe_metadata = cpe_metadata


def internetdb(ip: str) -> ProviderResult:
    if ipaddress.ip_address(ip).version == 6:
        return ProviderResult("Shodan InternetDB", "no_data", error="InternetDB does not return IPv6 host records")

    def load():
        data, hit = _cached_json("internetdb", ip, f"https://internetdb.shodan.io/{quote(ip)}", ttl=21600)
        entities, relations = [], []
        root = _entity_id("ip", ip)
        ports = sorted({int(port) for port in data.get("ports", []) if str(port).isdigit()})
        hostnames = sorted({str(host).lower().rstrip(".") for host in data.get("hostnames", []) if str(host).strip()})
        cpes = sorted({str(cpe).strip() for cpe in data.get("cpes", []) if str(cpe).strip()})
        cves = sorted({str(cve).upper() for cve in data.get("vulns", []) if str(cve).upper().startswith("CVE-")})
        tags = sorted({str(tag).strip() for tag in data.get("tags", []) if str(tag).strip()})
        # Re-emitting the IP enriches the already-normalized root node after
        # report deduplication.  Tags and compact exposure counts would
        # otherwise only be visible in raw provider JSON.
        entities.append(
            Entity(
                "ip",
                ip,
                metadata={
                    "internetdb_observed": True,
                    "internetdb_tags": tags,
                    "open_ports": ports,
                    "observed_hostnames": hostnames,
                    "observed_cpes": cpes,
                    "possible_cves": cves,
                    "exposure_count": len(ports),
                    "source": "Shodan InternetDB",
                },
            )
        )
        for port in ports:
            value = f"{ip}:{port}"
            metadata = {
                "port": port,
                "transport": "tcp",
                "ip": ip,
                "host": ip,
                "internetdb_tags": tags,
                "source": "Shodan InternetDB",
                **classify_service(port),
            }
            entities.append(Entity("service", value, metadata=metadata))
            metadata["evidence_state"] = "candidate"
            relations.append(
                Relation(
                    root,
                    _entity_id("service", value),
                    "exposes",
                    "Shodan InternetDB",
                    "medium",
                    None,
                    f"{metadata['category_label']}: {metadata['service_name']}. "
                    "Revalidate to establish current reachability.",
                    state="candidate",
                    supporting_sources=["Shodan InternetDB"],
                )
            )
        for host in hostnames:
            entities.append(Entity("domain", host, metadata={"discovery": "internetdb_hostname"}))
            relations.append(
                Relation(root, _entity_id("domain", host), "observed_hostname", "Shodan InternetDB", "low", None)
            )
        for cpe in cpes:
            entities.append(Entity("cpe", cpe, metadata=_cpe_metadata(cpe)))
            relations.append(Relation(root, _entity_id("cpe", cpe), "fingerprinted_as", "Shodan InternetDB", "medium"))
        for cve in cves:
            entities.append(
                Entity(
                    "cve",
                    cve,
                    metadata={
                        "applicability": "weak_signal",
                        "sources": ["Shodan InternetDB"],
                    },
                )
            )
            relations.append(
                Relation(
                    root,
                    _entity_id("cve", cve),
                    "possible_vulnerability",
                    "Shodan InternetDB",
                    "low",
                    None,
                    "Unverified InternetDB signal",
                )
            )
        return ProviderResult("Shodan InternetDB", "cached" if hit else "ok", data, entities, relations)

    return _run("Shodan InternetDB", load)
