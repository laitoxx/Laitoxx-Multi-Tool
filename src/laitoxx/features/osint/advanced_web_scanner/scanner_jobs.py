from __future__ import annotations

from urllib.parse import urlparse

from . import (
    provider_api as providers,
)
from . import (
    scope,
)
from .models import ProviderResult, ScanReport, Target


class ScanJobsMixin:
    def _initial_jobs(self, target: Target):
        if target.kind == "cve":
            return []
        if target.kind == "asn":
            return [lambda: providers.rdap(target), lambda: providers.ripestat(target.value)]
        if target.kind == "ip":
            return self._ip_baseline_jobs(target.value)
        domain = urlparse(target.value).hostname if target.kind == "url" else target.value
        jobs = [
            lambda: self._dns_lookup(target),
            lambda: providers.rdap(target),
            lambda: providers.crtsh(domain),
            lambda: providers.otx("domain", domain),
        ]
        if self._enabled("shodan_account") and self._configured_key_provider("shodan_account"):
            jobs.append(lambda: providers.shodan_search_enrichment("domain", domain))
        if (
            self.options.dns_security_posture
            and self._native_dns_provider()
            and self._enrichment_enabled("dns_security_posture")
        ):
            jobs.append(lambda: providers.dns_security_posture(domain))
        if self.options.profile == "maximum":
            optional = [
                ("virustotal", lambda: providers.virustotal("domain", domain)),
                ("urlscan", lambda: providers.urlscan("domain", domain)),
                ("wayback", lambda: providers.wayback(domain)),
                ("commoncrawl", lambda: providers.commoncrawl(domain)),
                ("hackertarget", lambda: providers.hackertarget("domain", domain)),
                ("tls", lambda: providers.tls_certificate(domain)),
                ("certspotter", lambda: providers.certspotter(domain)),
            ]
            jobs.extend(job for provider_id, job in optional if self._enabled(provider_id))
            if self._enabled("leakix") and self._configured_key_provider("leakix"):
                jobs.append(lambda: providers.leakix("domain", domain))
        return jobs

    def _ip_baseline_jobs(self, ip: str):
        return [
            lambda ip=ip: providers.ipinfo(ip),
            lambda ip=ip: providers.rdap(Target("ip", ip, ip)),
            lambda ip=ip: providers.ripestat(ip),
        ]

    def _ip_enrichment_jobs(self, ip: str, include_threat: bool):
        jobs = [
            lambda ip=ip: providers.internetdb(ip),
        ]
        if self._enabled("shodan_account") and self._configured_key_provider("shodan_account"):
            jobs.append(lambda ip=ip: providers.shodan_search_enrichment("ip", ip))
        if include_threat:
            jobs.extend([lambda ip=ip: providers.otx("ip", ip), lambda ip=ip: providers.abuseipdb(ip)])
        if self.options.profile == "maximum":
            optional = [
                ("virustotal", lambda ip=ip: providers.virustotal("ip", ip)),
                ("urlscan", lambda ip=ip: providers.urlscan("ip", ip)),
                ("greynoise", lambda ip=ip: providers.greynoise(ip)),
            ]
            jobs.extend(job for provider_id, job in optional if self._enabled(provider_id))
            if self._enabled("leakix") and self._configured_key_provider("leakix"):
                jobs.append(lambda ip=ip: providers.leakix("ip", ip))
        return jobs

    def _run_ip_domain_discovery(self, report: ScanReport, ips: list[str]):
        """Use one quota-aware IP-to-domain provider at a time.

        The providers share a discovery role, but not semantics: WhoisJSON is
        a private reverse-WHOIS association, HackerTarget is an A-record
        database and Botoi is a live PTR resolver.  The selected evidence type
        remains visible on every relation.
        """
        chain = (
            ("whoisjson", providers.whoisjson_reverse_whois),
            ("hackertarget", providers.hackertarget_reverse_ip),
            ("botoi", providers.botoi_reverse_dns),
        )
        for ip in dict.fromkeys(ips):
            attempts = []
            selected = ""
            for provider_id, lookup in chain:
                if not self._enabled(provider_id):
                    continue
                if provider_id == "whoisjson" and not self._configured_key_provider("whoisjson"):
                    continue
                result = lookup(ip)
                self._merge_local(report, result)
                domains = sorted({entity.value for entity in result.entities if entity.kind == "domain"})
                attempts.append(
                    {
                        "provider": result.name,
                        "status": result.status,
                        "domains": len(domains),
                        "error": result.error,
                    }
                )
                if domains:
                    selected = result.name
                    break
            if attempts:
                self._merge_local(
                    report,
                    ProviderResult(
                        "IP Domain Discovery",
                        "ok" if selected else "no_data",
                        data={
                            "ip": ip,
                            "selected_provider": selected or None,
                            "attempts": attempts,
                            "fallback_policy": "WhoisJSON -> HackerTarget -> Botoi; continue on missing data, quota, auth or availability failure",
                        },
                    ),
                )

    def _clean_ip_pivots(self, report: ScanReport, ips: list[str]) -> list[str]:
        """Suppress shared edge expansion without hiding classification evidence."""
        if not self.options.clean_shared_infrastructure or not self._enrichment_enabled("scope_classifier"):
            return ips
        result = scope.classify_report(report, ips)
        self._merge_local(report, result)
        suppressed = set(result.data.get("suppressed_ips", []))
        return [ip for ip in ips if ip not in suppressed]

    def _run_routing_enrichment(self, report: ScanReport, ips: list[str]):
        if not self.options.routing_enrichment or not self._enrichment_enabled("routing_rpki"):
            return
        jobs = []
        for ip in dict.fromkeys(ips):
            ip_id = f"ip:{ip.casefold()}"
            prefix = next(
                (
                    relation.target.split(":", 1)[1]
                    for relation in report.relations
                    if relation.source == ip_id and relation.target.startswith("prefix:")
                ),
                "",
            )
            asn = next(
                (
                    relation.target.split(":", 1)[1].upper()
                    for relation in report.relations
                    if relation.source == ip_id and relation.target.startswith("asn:")
                ),
                "",
            )
            jobs.append(lambda ip=ip, prefix=prefix, asn=asn: providers.ripestat_routing(ip, prefix, asn))
        self._run_jobs(jobs, report)

    def _recurse_domains(self, report: ScanReport, target: Target, *, enriched_ips: set[str] | None = None):
        if self.options.max_depth < 2 or target.kind not in {"domain", "url"}:
            return
        root_domain = urlparse(target.value).hostname if target.kind == "url" else target.value
        visited = {root_domain.casefold()}
        # These relations can discover a concrete subdomain of the target.
        # Co-certificate domains are intentionally excluded: sharing a
        # certificate is evidence, but not enough to scan an unrelated domain.
        allowed_relations = {"certificate_contains", "observed_with", "scanned_on"}
        frontier = [root_domain.casefold()]
        budget = self.options.max_domain_pivots
        recursive_ip_budget = self.options.max_recursive_ip_pivots
        enriched_ips = set(enriched_ips or ())
        for _depth in range(1, self.options.max_depth):
            candidates = set()
            frontier_ids = {f"domain:{domain}" for domain in frontier}
            frontier_ip_ids = {
                relation.target
                for relation in report.relations
                if relation.source in frontier_ids
                and relation.source_name == "DNS"
                and relation.relation == "dns_record"
                and relation.current is True
                and relation.evidence in {"A", "AAAA", "A/AAAA"}
                and relation.target.startswith("ip:")
            }
            for relation in report.relations:
                candidate = ""
                if relation.relation in allowed_relations and relation.target.startswith("domain:"):
                    source_domain = (
                        relation.source.split(":", 1)[1].casefold() if relation.source.startswith("domain:") else ""
                    )
                    if source_domain in frontier:
                        candidate = relation.target.split(":", 1)[1].casefold()
                elif (
                    relation.relation == "current_resolves_to"
                    and relation.current is True
                    and relation.source.startswith("domain:")
                    and relation.target in frontier_ip_ids
                ):
                    # InternetDB hostnames start as a weak IP -> hostname
                    # observation.  _verify_observed_hostnames reverses and
                    # promotes only those still resolving to the same IP.
                    candidate = relation.source.split(":", 1)[1].casefold()
                if not candidate:
                    continue
                is_target_subdomain = candidate.endswith("." + root_domain.casefold())
                if candidate not in visited and is_target_subdomain:
                    candidates.add(candidate)
            frontier = sorted(candidates)[:budget]
            visited.update(frontier)
            if not frontier:
                break
            budget -= len(frontier)
            for domain in frontier:
                jobs = [
                    lambda domain=domain: self._dns_lookup(Target("domain", domain, domain)),
                    lambda domain=domain: providers.rdap(Target("domain", domain, domain)),
                ]
                if self._enabled("otx"):
                    jobs.append(lambda domain=domain: providers.otx("domain", domain))
                self._run_jobs(jobs, report)

            # DNS results from recursive domains must continue through the
            # same baseline, scope-cleaning and exposure pipeline as the root.
            # This was previously missing, so discovered subhosts could never
            # contribute services, CPEs or CVEs.
            recursive_ips = [ip for ip in self._current_dns_ips(report, set(frontier)) if ip not in enriched_ips][
                :recursive_ip_budget
            ]
            if recursive_ips:
                self._run_jobs(
                    (job for ip in recursive_ips for job in self._ip_baseline_jobs(ip)),
                    report,
                )
                self._run_routing_enrichment(report, recursive_ips)
                allowed_ips = self._clean_ip_pivots(report, recursive_ips)
                self._run_jobs(
                    (job for ip in allowed_ips for job in self._ip_enrichment_jobs(ip, include_threat=True)),
                    report,
                )
                self._run_ip_domain_discovery(report, allowed_ips)
                enriched_ips.update(recursive_ips)
                recursive_ip_budget -= len(recursive_ips)
            if budget <= 0:
                break
            if recursive_ip_budget <= 0:
                break
