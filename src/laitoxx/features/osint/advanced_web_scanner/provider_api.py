"""Stable provider API delegating to focused network adapters."""

from __future__ import annotations

from typing import Any

from .models import ProviderResult, Target


def _dns_providers():
    from .provider import dns as dns_provider

    return dns_provider


def dns(target: Target, mode: str = "doh", *, consensus: bool = True) -> ProviderResult:
    return _dns_providers().dns(target, mode, consensus=consensus)


def dns_security_posture(domain: str) -> ProviderResult:
    from .provider.dns_posture import dns_security_posture as provider

    return provider(domain)


def dns_misconfigurations(domain: str, cname_targets: list[str]) -> ProviderResult:
    from .provider.dns_posture import dns_misconfigurations as provider

    return provider(domain, cname_targets)


def rdap(target: Target) -> ProviderResult:
    from .provider.registration import rdap as provider

    return provider(target)


def _routing_providers():
    from .provider import routing

    return routing


def ipinfo(ip: str) -> ProviderResult:
    return _routing_providers().ipinfo(ip)


def ripestat(value: str) -> ProviderResult:
    return _routing_providers().ripestat(value)


def ripestat_routing(value: str, prefix: str = "", asn: str = "") -> ProviderResult:
    return _routing_providers().ripestat_routing(value, prefix, asn)


def internetdb(ip: str) -> ProviderResult:
    from .provider.exposure import internetdb as provider

    return provider(ip)


def _shodan_providers():
    from .provider import shodan

    return shodan


def shodan_account_info() -> ProviderResult:
    return _shodan_providers().shodan_account_info()


def shodan_search_enrichment(
    kind: str,
    value: str,
    *,
    query_override: str = "",
    required_filters: tuple[str, ...] = (),
    purpose: str = "Exact target filter",
    relation: str = "matches_shodan_filter",
    confidence: str = "medium",
    allow_search_results: bool = True,
    collision_prone: bool = False,
) -> ProviderResult:
    return _shodan_providers().shodan_search_enrichment(
        kind,
        value,
        query_override=query_override,
        required_filters=required_filters,
        purpose=purpose,
        relation=relation,
        confidence=confidence,
        allow_search_results=allow_search_results,
        collision_prone=collision_prone,
    )


def _reverse_lookup_providers():
    from .provider import reverse_lookup

    return reverse_lookup


def _domain_candidate(value: Any) -> str:
    return _reverse_lookup_providers().domain_candidate(value)


def whoisjson_reverse_whois(ip: str) -> ProviderResult:
    return _reverse_lookup_providers().whoisjson_reverse_whois(ip)


def botoi_reverse_dns(ip: str) -> ProviderResult:
    return _reverse_lookup_providers().botoi_reverse_dns(ip)


def _certificate_providers():
    from .provider import certificates

    return certificates


def crtsh(domain: str) -> ProviderResult:
    return _certificate_providers().crtsh(domain)


def certspotter(domain: str) -> ProviderResult:
    return _certificate_providers().certspotter(domain)


def _threat_providers():
    from .provider import threat_intel

    return threat_intel


def otx(kind: str, value: str) -> ProviderResult:
    return _threat_providers().otx(kind, value)


def abuseipdb(ip: str) -> ProviderResult:
    return _threat_providers().abuseipdb(ip)


def _vulnerability_providers():
    from .provider import vulnerabilities

    return vulnerabilities


def vulnerability(cve: str) -> list[ProviderResult]:
    return _vulnerability_providers().vulnerability(cve)


def nvd(cve: str) -> ProviderResult:
    return _vulnerability_providers().nvd(cve)


def osv(cve: str) -> ProviderResult:
    return _vulnerability_providers().osv(cve)


def github_advisories(cve: str) -> ProviderResult:
    return _vulnerability_providers().github_advisories(cve)


def vulncheck_nvd(cve: str) -> ProviderResult:
    return _vulnerability_providers().vulncheck_nvd(cve)


def vulncheck_kev(cve: str) -> ProviderResult:
    return _vulnerability_providers().vulncheck_kev(cve)


def nvd_version_match(product: str, version: str, technology_value: str) -> ProviderResult:
    return _vulnerability_providers().nvd_version_match(product, version, technology_value)


def osv_version_match(product: str, version: str, technology_value: str, ecosystem: str) -> ProviderResult:
    return _vulnerability_providers().osv_version_match(product, version, technology_value, ecosystem)


def github_version_match(product: str, version: str, technology_value: str) -> ProviderResult:
    return _vulnerability_providers().github_version_match(product, version, technology_value)


def vulncheck_version_match(product: str, version: str, technology_value: str) -> ProviderResult:
    return _vulnerability_providers().vulncheck_version_match(product, version, technology_value)


def kev(cve: str) -> ProviderResult:
    return _vulnerability_providers().kev(cve)


def epss(cve: str) -> ProviderResult:
    return _vulnerability_providers().epss(cve)


def _reputation_providers():
    from .provider import reputation

    return reputation


def virustotal(kind: str, value: str) -> ProviderResult:
    return _reputation_providers().virustotal(kind, value)


def urlscan(kind: str, value: str) -> ProviderResult:
    return _reputation_providers().urlscan(kind, value)


def _archive_providers():
    from .provider import archives

    return archives


def wayback(domain: str) -> ProviderResult:
    return _archive_providers().wayback(domain)


def commoncrawl(domain: str) -> ProviderResult:
    return _archive_providers().commoncrawl(domain)


def _hackertarget_provider():
    from .provider import hackertarget as provider

    return provider


def hackertarget(kind: str, value: str) -> ProviderResult:
    return _hackertarget_provider().hackertarget(kind, value)


def hackertarget_reverse_ip(ip: str) -> ProviderResult:
    return _hackertarget_provider().hackertarget_reverse_ip(ip)


def leakix(kind: str, value: str) -> ProviderResult:
    from .provider.leakix import leakix as provider

    return provider(kind, value)


def greynoise(ip: str) -> ProviderResult:
    from .provider.greynoise import greynoise as provider

    return provider(ip)


def tls_certificate(host: str, port: int = 443) -> ProviderResult:
    from .provider.tls import tls_certificate as provider

    return provider(host, port)


def _status_data(result: tuple[Any, bool]) -> tuple[str, Any]:
    data, hit = result
    return ("cached" if hit else "ok", data)
