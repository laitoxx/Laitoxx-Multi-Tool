from __future__ import annotations

import ipaddress

from .models import ProviderResult, Relation, ScanReport, Target
from .orchestration.executor import merge_result, run_jobs


class CorrelationMixin:
    @staticmethod
    def _reconcile_exposure_states(report: ScanReport):
        """Separate indexed candidates from services confirmed during this scan."""
        live_services = {
            relation.target
            for relation in report.relations
            if relation.target.startswith("service:")
            and relation.current is True
            and relation.source_name in {"Naabu Port Discovery", "httpx Fingerprinting"}
        }
        entity_by_id = {entity.id: entity for entity in report.entities}
        domain_ips: dict[str, set[str]] = {}
        for relation in report.relations:
            if (
                relation.relation == "dns_record"
                and relation.current is True
                and relation.source.startswith("domain:")
                and relation.target.startswith("ip:")
            ):
                domain_ips.setdefault(relation.source.split(":", 1)[1], set()).add(relation.target.split(":", 1)[1])

        live_endpoints = set()
        for service_id in live_services:
            service = entity_by_id.get(service_id)
            if not service or not str(service.metadata.get("port", "")).isdigit():
                continue
            port = int(service.metadata["port"])
            hosts = {
                str(service.metadata.get("ip") or "").casefold(),
                str(service.metadata.get("host") or "").casefold(),
            } - {""}
            for host in tuple(hosts):
                hosts.update(domain_ips.get(host, set()))
            live_endpoints.update((host, port) for host in hosts)

        for entity in report.entities:
            if entity.kind == "service":
                port = int(entity.metadata["port"]) if str(entity.metadata.get("port", "")).isdigit() else 0
                hosts = {
                    str(entity.metadata.get("ip") or "").casefold(),
                    str(entity.metadata.get("host") or "").casefold(),
                } - {""}
                for host in tuple(hosts):
                    hosts.update(domain_ips.get(host, set()))
                endpoint_confirmed = bool(port and any((host, port) in live_endpoints for host in hosts))
                if entity.id in live_services or entity.metadata.get("actively_verified") or endpoint_confirmed:
                    entity.metadata.update({"evidence_state": "live", "current": True})
                    live_services.add(entity.id)
                else:
                    entity.metadata.setdefault("evidence_state", "candidate")
                    entity.metadata.setdefault("current", None)
            elif entity.kind == "finding" and entity.metadata.get("scanner") in {"Nuclei", "WPScan"}:
                entity.metadata.update({"evidence_state": "confirmed", "current": True})
        for relation in report.relations:
            if relation.target in live_services:
                relation.current = True
                relation.state = "live"
            elif relation.target.startswith("service:") and relation.source_name == "Shodan InternetDB":
                relation.current = None
                relation.state = "candidate"

    @staticmethod
    def _correlate_ownership(report: ScanReport):
        entity_by_id = {entity.id: entity for entity in report.entities}
        privacy_tokens = {
            "privacy",
            "proxy",
            "redacted",
            "not disclosed",
            "data protected",
            "domains by proxy",
            "contact privacy",
            "withheld",
        }
        owners: dict[str, list[str]] = {}
        for relation in report.relations:
            if relation.relation == "registered_to" and relation.source.startswith("domain:"):
                owner = entity_by_id.get(relation.target)
                owner_name = owner.value.casefold() if owner else relation.target.casefold()
                if any(token in owner_name for token in privacy_tokens):
                    continue
                owners.setdefault(relation.target, []).append(relation.source)
        for owner, domains in owners.items():
            owner_entity = entity_by_id.get(owner)
            handle = str(owner_entity.metadata.get("handle") or "") if owner_entity else ""
            for domain in sorted(set(domains))[1:]:
                report.relations.append(
                    Relation(
                        sorted(set(domains))[0],
                        domain,
                        "same_registrant_candidate",
                        "Ownership correlation",
                        "medium" if handle else "low",
                        None,
                        f"Both domains expose the same RDAP registrant entity ({owner.split(':', 1)[1]}). "
                        "This signal requires corroboration and does not prove current common ownership.",
                        state="candidate",
                        supporting_sources=["RDAP"],
                    )
                )

    def _run_jobs(self, jobs, report: ScanReport):
        run_jobs(
            jobs,
            report,
            workers=self.options.workers,
            progress=self.progress,
        )

    @staticmethod
    def _merge(report: ScanReport, result: ProviderResult):
        merge_result(report, result)

    def _verify_observed_hostnames(self, report: ScanReport):
        candidates_by_hostname = {}
        for relation in report.relations:
            if relation.relation == "observed_hostname" and relation.current is None:
                hostname = relation.target.split(":", 1)[1]
                candidates_by_hostname.setdefault(hostname, (relation, hostname))
        candidates = list(candidates_by_hostname.values())[: self.options.max_hostname_verifications]
        for relation, hostname in candidates:
            result = self._dns_lookup(Target("domain", hostname, hostname))
            resolved = {entity.value for entity in result.entities if entity.kind == "ip"}
            source_ip = relation.source.split(":", 1)[1]
            domain_id = relation.target
            ip_id = relation.source
            relation.source = domain_id
            relation.target = ip_id
            if source_ip in resolved:
                relation.relation = "current_resolves_to"
                relation.current = True
                relation.confidence = "high"
                relation.evidence = "Current DNS confirmed the observed hostname"
            else:
                relation.relation = "historical_or_observed"
                relation.current = False
                relation.confidence = "low"
                relation.evidence = "Current DNS does not resolve to the observed IP"
            self._merge(report, result)

    @staticmethod
    def _current_dns_ips(report: ScanReport, domains: set[str] | None = None) -> list[str]:
        """Return deterministic live A/AAAA pivots, excluding passive history."""
        domain_ids = {f"domain:{domain.casefold()}" for domain in domains} if domains is not None else None
        entity_by_id = {entity.id: entity for entity in report.entities}
        ips = []
        seen = set()
        for relation in report.relations:
            if relation.source_name != "DNS" or relation.relation != "dns_record" or relation.current is not True:
                continue
            if relation.evidence not in {"A", "AAAA", "A/AAAA"}:
                continue
            if domain_ids is not None and relation.source not in domain_ids:
                continue
            entity = entity_by_id.get(relation.target)
            if not entity or entity.kind != "ip" or entity.value in seen:
                continue
            try:
                normalized_ip = str(ipaddress.ip_address(entity.value))
            except ValueError:
                # Provider data is untrusted.  A mislabeled CNAME must not be
                # passed into RDAP/InternetDB/Botoi as an IP pivot.
                continue
            if normalized_ip in seen:
                continue
            seen.add(normalized_ip)
            ips.append(normalized_ip)
        return sorted(ips)
