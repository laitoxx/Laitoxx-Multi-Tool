"""Infrastructure ownership and shared-edge classification.

The classifier is intentionally conservative: a generic cloud ASN is not
enough to suppress a host.  Suppression requires an edge/CDN ASN or a
provider-specific DNS name, preventing customer-owned cloud origins from being
discarded merely because they run in AWS, Azure or Google Cloud.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Entity, ProviderResult, Relation, ScanReport


@dataclass(frozen=True)
class InfrastructureSignature:
    provider: str
    role: str
    suppress: bool
    asns: frozenset[str] = frozenset()
    domain_suffixes: tuple[str, ...] = ()


SIGNATURES = (
    InfrastructureSignature("Cloudflare", "cdn_edge", True, frozenset({"AS13335"}), (".cdn.cloudflare.net",)),
    InfrastructureSignature(
        "Akamai",
        "cdn_edge",
        True,
        frozenset({"AS16625", "AS20940"}),
        (".akamaiedge.net", ".akamai.net", ".akamaitechnologies.com", ".edgekey.net", ".edgesuite.net"),
    ),
    InfrastructureSignature("Fastly", "cdn_edge", True, frozenset({"AS54113"}), (".fastly.net", ".fastlylb.net")),
    InfrastructureSignature("Imperva", "waf_edge", True, frozenset({"AS19551"}), (".incapdns.net",)),
    InfrastructureSignature("Amazon CloudFront", "cdn_edge", True, domain_suffixes=(".cloudfront.net",)),
    InfrastructureSignature("Azure Front Door", "cdn_edge", True, domain_suffixes=(".azurefd.net", ".azureedge.net")),
    InfrastructureSignature("Google Cloud CDN", "cdn_edge", True, domain_suffixes=(".googlehosted.com",)),
    InfrastructureSignature("Amazon Web Services", "cloud_hosted", False, frozenset({"AS14618", "AS16509"})),
    InfrastructureSignature("Microsoft Azure", "cloud_hosted", False, frozenset({"AS8075"})),
    InfrastructureSignature("Google Cloud", "cloud_hosted", False, frozenset({"AS15169", "AS396982"})),
)


def classify_report(report: ScanReport, ips: list[str] | None = None) -> ProviderResult:
    """Classify infrastructure and return IPs that must not be expanded."""
    entity_by_id = {entity.id: entity for entity in report.entities}
    ip_ids = {entity.id for entity in report.entities if entity.kind == "ip" and (ips is None or entity.value in ips)}
    ip_asns: dict[str, set[str]] = {entity_id: set() for entity_id in ip_ids}
    ip_domains: dict[str, set[str]] = {entity_id: set() for entity_id in ip_ids}

    for relation in report.relations:
        if relation.source in ip_ids and relation.target.startswith("asn:"):
            ip_asns[relation.source].add(relation.target.split(":", 1)[1].upper())
        if relation.target in ip_ids and relation.source.startswith("domain:"):
            ip_domains[relation.target].add(relation.source.split(":", 1)[1].casefold())
        if relation.source in ip_ids and relation.target.startswith("domain:"):
            ip_domains[relation.source].add(relation.target.split(":", 1)[1].casefold())

    # CNAME targets often contain the strongest provider signature. Associate
    # them with every IP reached from the same root domain.
    cname_by_root: dict[str, set[str]] = {}
    ips_by_root: dict[str, set[str]] = {}
    for relation in report.relations:
        if relation.relation != "dns_record":
            continue
        if relation.target.startswith("domain:") and relation.evidence == "CNAME":
            cname_by_root.setdefault(relation.source, set()).add(relation.target.split(":", 1)[1].casefold())
        if relation.target in ip_ids and relation.evidence in {"A", "AAAA", "A/AAAA"}:
            ips_by_root.setdefault(relation.source, set()).add(relation.target)
    for root, target_ips in ips_by_root.items():
        for ip_id in target_ips:
            ip_domains.setdefault(ip_id, set()).update(cname_by_root.get(root, set()))

    suppressed: list[str] = []
    classified: list[dict] = []
    relations: list[Relation] = []
    for ip_id in sorted(ip_ids):
        entity = entity_by_id[ip_id]
        matches = _matches(ip_asns.get(ip_id, set()), ip_domains.get(ip_id, set()))
        if not matches:
            entity.metadata.setdefault("infrastructure_role", "origin_candidate")
            continue
        best = max(matches, key=lambda match: (match.suppress, match.role in {"cdn_edge", "waf_edge"}))
        evidence = sorted({*ip_asns.get(ip_id, set()), *ip_domains.get(ip_id, set())})
        entity.metadata.update(
            {
                "infrastructure_provider": best.provider,
                "infrastructure_role": best.role,
                "shared_infrastructure": best.suppress,
                "pivot_suppressed": best.suppress,
                "scope_evidence": evidence,
                "explanation": (
                    f"{best.provider} {best.role.replace('_', ' ')} classification. "
                    + (
                        "Reverse-IP, service and vulnerability expansion is suppressed."
                        if best.suppress
                        else "The address is cloud-hosted; ownership is not inferred from the ASN alone."
                    )
                ),
            }
        )
        classified.append({"ip": entity.value, "provider": best.provider, "role": best.role, "evidence": evidence})
        if best.suppress:
            suppressed.append(entity.value)
        provider_entity = Entity("infrastructure_provider", best.provider, metadata={"role": best.role})
        relations.append(
            Relation(
                entity.id,
                provider_entity.id,
                "served_by" if best.suppress else "hosted_by",
                "Scope Classifier",
                "high" if evidence else "medium",
                True,
                ", ".join(evidence),
                state="confirmed" if best.suppress else "live",
                supporting_sources=["DNS", "IPinfo Lite", "RIPEstat"],
            )
        )
        if provider_entity.id not in entity_by_id:
            report.entities.append(provider_entity)
            entity_by_id[provider_entity.id] = provider_entity

    return ProviderResult(
        "Scope Cleaner",
        "ok" if classified else "no_data",
        data={"classified": classified, "suppressed_ips": sorted(set(suppressed))},
        relations=relations,
        error="" if classified else "No shared-edge or cloud signature was identified",
    )


def _matches(asns: set[str], domains: set[str]) -> list[InfrastructureSignature]:
    matches = []
    for signature in SIGNATURES:
        asn_match = bool(asns & signature.asns)
        domain_match = any(
            domain == suffix.removeprefix(".") or domain.endswith(suffix)
            for domain in domains
            for suffix in signature.domain_suffixes
        )
        if asn_match or domain_match:
            matches.append(signature)
    return matches
