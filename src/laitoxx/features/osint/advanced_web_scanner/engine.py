from __future__ import annotations

import inspect
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlparse

from . import (
    archive_analysis,
    evidence,
    posture,
    shodan_filters,
    technology,
)
from . import (
    provider_api as providers,
)
from .models import Entity, ProviderResult, Relation, ScanReport, Target, normalize_target
from .options import ScanOptions
from .scanner_active import ActiveValidationMixin
from .scanner_correlation import CorrelationMixin
from .scanner_jobs import ScanJobsMixin
from .scanner_reporting import ReportFinalizationMixin
from .scanner_vulnerabilities import VulnerabilityMixin


class AdvancedWebScanner(
    ActiveValidationMixin, ScanJobsMixin, CorrelationMixin, VulnerabilityMixin, ReportFinalizationMixin
):
    def __init__(
        self, options: ScanOptions | None = None, progress: Callable[[str, ProviderResult], None] | None = None
    ):
        self.options = options or ScanOptions()
        self.progress = progress

    def _enabled(self, provider_id: str) -> bool:
        return bool(self.options.provider_config.get("providers", {}).get(provider_id, {}).get("enabled", True))

    def _configured_key_provider(self, provider_id: str) -> bool:
        item = self.options.provider_config.get("providers", {}).get(provider_id)
        return bool(item and item.get("enabled", True) and providers.credential(provider_id))

    def _enrichment_enabled(self, option: str) -> bool:
        values = self.options.provider_config.get("enrichments", {})
        return bool(values.get(option, True))

    def _dns_lookup(self, target: Target) -> ProviderResult:
        # Keep provider monkeypatches/plugins written for the original two-
        # argument API compatible while using consensus in the built-in
        # provider.
        parameters = inspect.signature(providers.dns).parameters
        if "consensus" in parameters:
            return providers.dns(
                target,
                self.options.dns_mode,
                consensus=self._enrichment_enabled("dns_consensus"),
            )
        return providers.dns(target, self.options.dns_mode)

    @staticmethod
    def _native_dns_provider() -> bool:
        return getattr(providers.dns, "__module__", "") == providers.__name__

    def scan(self, raw_target: str) -> ScanReport:
        target = normalize_target(raw_target)
        report = ScanReport(target=target, entities=[Entity(target.kind, target.value, label=target.value)])
        if target.kind == "url":
            domain = urlparse(target.value).hostname or target.value
            report.entities.append(Entity("domain", domain, label=domain))
            report.relations.append(
                Relation(
                    f"url:{target.value.casefold()}",
                    f"domain:{domain.casefold()}",
                    "has_host",
                    "Normalizer",
                    "high",
                    True,
                )
            )

        first_wave = list(self._initial_jobs(target))
        if self._configured_key_provider("shodan_account"):
            first_wave.append(providers.shodan_account_info)
        self._run_jobs(first_wave, report)

        if (
            target.kind in {"domain", "url"}
            and self._native_dns_provider()
            and self._enrichment_enabled("dns_misconfiguration")
        ):
            domain = urlparse(target.value).hostname if target.kind == "url" else target.value
            cname_targets = sorted(
                {
                    relation.target.split(":", 1)[1]
                    for relation in report.relations
                    if relation.source == f"domain:{domain.casefold()}"
                    and relation.relation == "dns_record"
                    and relation.evidence == "CNAME"
                    and relation.target.startswith("domain:")
                }
            )
            self._merge_local(report, providers.dns_misconfigurations(domain, cname_targets))

        # Resolve ownership/routing first.  Shared edge providers are kept on the
        # graph, but not treated as the target's own exposed infrastructure.
        # Only authoritative current A/AAAA answers are eligible for active IP
        # enrichment.  Passive sources (urlscan, OTX, VT, HackerTarget) remain
        # evidence in the report but must never displace live DNS addresses.
        root_domain = urlparse(target.value).hostname if target.kind == "url" else target.value
        current_ips = self._current_dns_ips(report, {root_domain})[: self.options.max_ip_pivots]
        if target.kind in {"domain", "url"} and current_ips:
            self._run_jobs((job for ip in current_ips for job in self._ip_baseline_jobs(ip)), report)
            self._run_routing_enrichment(report, current_ips)
            allowed_ips = self._clean_ip_pivots(report, current_ips)
            self._run_jobs(
                (job for ip in allowed_ips for job in self._ip_enrichment_jobs(ip, include_threat=True)), report
            )
            self._run_ip_domain_discovery(report, allowed_ips)

        if target.kind == "ip":
            self._run_routing_enrichment(report, [target.value])
            allowed_ips = self._clean_ip_pivots(report, [target.value])
            self._run_jobs(
                (job for ip in allowed_ips for job in self._ip_enrichment_jobs(ip, include_threat=True)), report
            )
            self._run_ip_domain_discovery(report, allowed_ips)

        # Recheck observed hostnames against current DNS before strengthening a
        # historical/observed relationship.
        self._verify_observed_hostnames(report)
        self._recurse_domains(report, target, enriched_ips=set(current_ips))

        if (
            self.options.profile == "maximum"
            and self.options.archive_enrichment
            and self._enrichment_enabled("archive_analysis")
        ):
            self._merge_local(report, archive_analysis.analyze(report))

        if self.options.active_scanning:
            self._run_active_validation(report, target)
            if self._enrichment_enabled("http_tls_posture"):
                self._merge_local(report, posture.analyze_active_posture(report))

        if self._enabled("shodan_account") and self._configured_key_provider("shodan_account"):
            self._run_shodan_contextual_enrichment(report, target)
        self._reconcile_exposure_states(report)

        # Scanner findings and passive sources frequently describe the same
        # CVE. Merge them before advisory enrichment so no evidence is lost.
        self._deduplicate(report)
        if self._enrichment_enabled("technology_identity"):
            technology.normalize_technologies(report)
        self._run_version_matching(report)
        self._deduplicate(report)

        cves = self._cves(report)
        if target.kind == "cve":
            cves.insert(0, target.value)
        elif not cves:
            internetdb = [item for item in report.providers if item.name == "Shodan InternetDB"]
            successful = [item for item in internetdb if item.status in {"ok", "cached"}]
            versioned = [
                entity
                for entity in report.entities
                if entity.kind in {"technology", "cpe"} and entity.metadata.get("version")
            ]
            reason = (
                "No in-scope provider returned a CVE and no product/version match produced a candidate. "
                "Historical or shared-IP neighbours are intentionally not attributed to the target."
            )
            discovery = ProviderResult(
                "Vulnerability Discovery",
                "no_data",
                data={
                    "reason": reason,
                    "internetdb_queries": len(internetdb),
                    "internetdb_successful": len(successful),
                    "internetdb_cves": 0,
                    "versioned_technologies": len(versioned),
                    "active_validation_enabled": self.options.active_scanning,
                    "next_step": (
                        "Enable authorized active validation to fingerprint versions and collect Nuclei evidence."
                        if not self.options.active_scanning
                        else "The authorized active stage also produced no CVE evidence for this target."
                    ),
                },
            )
            self._merge(report, discovery)
            if self.progress:
                self.progress(discovery.name, discovery)
        vulnerability_jobs = []
        for cve in list(dict.fromkeys(cves))[: self.options.max_cve_pivots]:
            for provider_id, fn in (
                ("nvd", providers.nvd),
                ("osv", providers.osv),
                ("github_advisories", providers.github_advisories),
                ("kev", providers.kev),
                ("epss", providers.epss),
            ):
                if self._enabled(provider_id):
                    vulnerability_jobs.append(lambda c=cve, fn=fn: fn(c))
            if self._enabled("vulncheck") and self._configured_key_provider("vulncheck"):
                vulnerability_jobs.extend(
                    (
                        lambda c=cve: providers.vulncheck_nvd(c),
                        lambda c=cve: providers.vulncheck_kev(c),
                    )
                )
        self._run_jobs(vulnerability_jobs, report)

        self._enrich_vulnerabilities(report)
        self._correlate_ownership(report)
        self._correlate_relations(report)
        self._deduplicate(report)
        if self._enrichment_enabled("evidence_freshness"):
            evidence.annotate_report(report)
            evidence.add_corroborated_relations(report)
            self._deduplicate(report)
            evidence.annotate_report(report)
        self._calculate_risk(report)
        report.timeline.sort(key=lambda item: item.event_time or "")
        report.completed_at = datetime.now(UTC).isoformat()
        return report

    def _run_shodan_contextual_enrichment(self, report: ScanReport, target: Target) -> None:
        pivot_target = target
        if target.kind == "url":
            domain = urlparse(target.value).hostname or ""
            if not domain:
                return
            pivot_target = Target("domain", domain, target.original)
        limit = self.options.max_shodan_filter_pivots
        if self.options.profile != "maximum":
            limit = min(3, limit)
        plans = shodan_filters.contextual_pivots(report, pivot_target, limit=limit)
        jobs = [
            lambda plan=plan: providers.shodan_search_enrichment(
                plan.anchor_kind,
                plan.anchor_value,
                query_override=plan.query,
                required_filters=plan.required_filters,
                purpose=plan.purpose,
                relation=plan.relation,
                confidence=plan.confidence,
                allow_search_results=plan.allow_search_results,
                collision_prone=plan.collision_prone,
            )
            for plan in plans
        ]
        self._run_jobs(jobs, report)

    def _run_version_matching(self, report: ScanReport):
        technologies = []
        for entity in report.entities:
            if entity.kind != "technology":
                continue
            product = str(entity.metadata.get("product") or "").strip()
            version = str(entity.metadata.get("version") or "").strip()
            if product and version:
                technologies.append((entity.value, product, version, str(entity.metadata.get("ecosystem") or "")))
        technologies = list(dict.fromkeys(technologies))[: self.options.max_technology_pivots]
        jobs = []
        for technology_value, product, version, ecosystem in technologies:
            if self._enabled("nvd"):
                jobs.append(lambda p=product, v=version, t=technology_value: providers.nvd_version_match(p, v, t))
            if self._enabled("github_advisories"):
                jobs.append(lambda p=product, v=version, t=technology_value: providers.github_version_match(p, v, t))
            if self._enabled("osv") and ecosystem:
                jobs.append(
                    lambda p=product, v=version, t=technology_value, e=ecosystem: providers.osv_version_match(
                        p, v, t, e
                    )
                )
            if self._enabled("vulncheck") and self._configured_key_provider("vulncheck"):
                jobs.append(lambda p=product, v=version, t=technology_value: providers.vulncheck_version_match(p, v, t))
        self._run_jobs(jobs, report)
