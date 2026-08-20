"""DNS security posture and misconfiguration analysis."""

from __future__ import annotations

import hashlib

from .. import provider_common as _common
from ..models import Entity, ProviderResult, Relation
from .dns import _doh_answers

_entity_id = _common._entity_id
_now = _common._now
_run = _common._run


def dns_security_posture(domain: str) -> ProviderResult:
    """Collect mail/security DNS policy and safe misconfiguration signals."""

    def load():
        queries = {
            "SPF": (domain, "TXT"),
            "DMARC": (f"_dmarc.{domain}", "TXT"),
            "MTA_STS": (f"_mta-sts.{domain}", "TXT"),
            "TLS_RPT": (f"_smtp._tls.{domain}", "TXT"),
            "CAA": (domain, "CAA"),
        }
        policies: dict[str, list[str]] = {}
        resolver_status = {}
        cached = True
        for policy, (name, record_type) in queries.items():
            answers, statuses, hit = _doh_answers(name, record_type, consensus=False)
            resolver_status[policy] = statuses
            cached &= hit
            values = []
            for answer in answers:
                value = str(answer.get("data") or "").strip().strip('"')
                if value and value not in values:
                    values.append(value)
            marker = {
                "SPF": "v=spf1",
                "DMARC": "v=dmarc1",
                "MTA_STS": "v=stsv1",
                "TLS_RPT": "v=tlsrptv1",
            }.get(policy)
            if marker:
                values = [value for value in values if marker in value.casefold()]
            policies[policy] = values

        findings: list[Entity] = []
        relations: list[Relation] = []
        root = _entity_id("domain", domain)
        checks = (
            ("DMARC", "Missing DMARC policy", "medium"),
            ("SPF", "Missing SPF policy", "low"),
            ("MTA_STS", "Missing MTA-STS DNS policy", "low"),
            ("TLS_RPT", "Missing SMTP TLS reporting policy", "low"),
            ("CAA", "No CAA restriction is published", "info"),
        )
        for policy, title, severity in checks:
            present = bool(policies[policy])
            value = f"{domain}:{policy.casefold()}"
            finding = Entity(
                "dns_policy",
                value,
                label=policy,
                metadata={
                    "policy": policy,
                    "present": present,
                    "values": policies[policy],
                    "severity": "info" if present else severity,
                    "hardening_finding": not present,
                    "explanation": f"{policy} is published."
                    if present
                    else title + ". This is a hardening observation, not proof of compromise.",
                },
            )
            findings.append(finding)
            relations.append(
                Relation(
                    root,
                    finding.id,
                    "publishes_policy" if present else "missing_policy",
                    "DNS Security Posture",
                    "high",
                    True,
                    finding.metadata["explanation"],
                    checked_at=_now(),
                    state="live",
                )
            )
        spf_values = [value for value in policies["SPF"] if value.casefold().startswith("v=spf1")]
        if len(spf_values) > 1:
            finding = Entity(
                "finding",
                f"{domain}:multiple-spf",
                label="Multiple SPF records",
                metadata={
                    "severity": "medium",
                    "category": "dns_misconfiguration",
                    "evidence_state": "live",
                    "explanation": "Multiple SPF records can cause a permanent SPF evaluation error.",
                },
            )
            findings.append(finding)
            relations.append(
                Relation(
                    root,
                    finding.id,
                    "has_misconfiguration",
                    "DNS Security Posture",
                    "high",
                    True,
                    finding.metadata["explanation"],
                    checked_at=_now(),
                    state="live",
                )
            )
        spf_lookup_terms = sum(
            token.casefold().startswith(("include:", "redirect=", "a", "mx", "exists:"))
            for value in spf_values
            for token in value.split()[1:]
        )
        if spf_lookup_terms > 10:
            finding = Entity(
                "finding",
                f"{domain}:spf-lookup-budget",
                label="SPF lookup budget exceeded",
                metadata={
                    "severity": "medium",
                    "category": "dns_misconfiguration",
                    "evidence_state": "live",
                    "lookup_terms": spf_lookup_terms,
                    "explanation": f"The SPF policy contains at least {spf_lookup_terms} DNS-triggering mechanisms, above the RFC evaluation limit of 10.",
                },
            )
            findings.append(finding)
            relations.append(
                Relation(
                    root,
                    finding.id,
                    "has_misconfiguration",
                    "DNS Security Posture",
                    "high",
                    True,
                    finding.metadata["explanation"],
                    checked_at=_now(),
                    state="live",
                )
            )
        if any("p=none" in value.casefold().replace(" ", "") for value in policies["DMARC"]):
            finding = Entity(
                "finding",
                f"{domain}:dmarc-monitoring",
                label="DMARC monitoring-only policy",
                metadata={
                    "severity": "low",
                    "category": "mail_hardening",
                    "evidence_state": "live",
                    "explanation": "DMARC is published with p=none, so it monitors failures but does not request quarantine or rejection.",
                },
            )
            findings.append(finding)
            relations.append(
                Relation(
                    root,
                    finding.id,
                    "has_hardening_observation",
                    "DNS Security Posture",
                    "high",
                    True,
                    finding.metadata["explanation"],
                    checked_at=_now(),
                    state="live",
                )
            )
        return ProviderResult(
            "DNS Security Posture",
            "cached" if cached else "ok",
            {"policies": policies, "resolver_status": resolver_status},
            findings,
            relations,
        )

    return _run("DNS Security Posture", load)


def dns_misconfigurations(domain: str, cname_targets: list[str]) -> ProviderResult:
    """Detect wildcard and dangling DNS candidates without claiming takeover."""

    def load():
        root = _entity_id("domain", domain)
        entities: list[Entity] = []
        relations: list[Relation] = []
        checks = []
        provider_suffixes = (
            ".azurewebsites.net",
            ".cloudapp.net",
            ".cloudfront.net",
            ".fastly.net",
            ".github.io",
            ".herokudns.com",
            ".netlify.app",
            ".s3.amazonaws.com",
            ".trafficmanager.net",
            ".vercel-dns.com",
            ".zendesk.com",
        )
        for target in list(dict.fromkeys(cname_targets))[:12]:
            resolved = []
            for record_type in ("A", "AAAA"):
                answers, statuses, _hit = _doh_answers(target, record_type, consensus=False)
                resolved.extend(answer for answer in answers if int(answer.get("type", 0) or 0) in {1, 28})
                checks.append({"target": target, "type": record_type, "status": statuses, "answers": len(answers)})
            if resolved:
                continue
            provider = next((suffix.removeprefix(".") for suffix in provider_suffixes if target.endswith(suffix)), "")
            finding_value = f"{domain}:dangling:{target}"
            finding = Entity(
                "finding",
                finding_value,
                label="Dangling CNAME candidate",
                metadata={
                    "category": "dns_misconfiguration",
                    "severity": "medium" if provider else "low",
                    "cname_target": target,
                    "provider_signature": provider,
                    "takeover_candidate": bool(provider),
                    "evidence_state": "candidate",
                    "explanation": (
                        f"CNAME target {target} currently has no A/AAAA answer. "
                        "This is only a candidate; provider-specific ownership validation is required."
                    ),
                },
            )
            entities.append(finding)
            relations.append(
                Relation(
                    root,
                    finding.id,
                    "has_dns_candidate",
                    "DNS Misconfiguration Analyzer",
                    "medium" if provider else "low",
                    None,
                    finding.metadata["explanation"],
                    state="candidate",
                )
            )

        random_label = hashlib.sha256(domain.encode()).hexdigest()[:12]
        wildcard_name = f"laitoxx-{random_label}.{domain}"
        wildcard_answers = []
        for record_type in ("A", "AAAA"):
            answers, statuses, _hit = _doh_answers(wildcard_name, record_type, consensus=False)
            wildcard_answers.extend(str(answer.get("data") or "") for answer in answers if answer.get("data"))
            checks.append({"target": wildcard_name, "type": record_type, "status": statuses, "answers": len(answers)})
        if wildcard_answers:
            finding = Entity(
                "finding",
                f"{domain}:wildcard-dns",
                label="Wildcard DNS",
                metadata={
                    "category": "dns_configuration",
                    "severity": "info",
                    "evidence_state": "live",
                    "answers": sorted(set(wildcard_answers)),
                    "explanation": "A deterministic nonexistent hostname resolves, indicating wildcard DNS. Subdomain discoveries require extra validation.",
                },
            )
            entities.append(finding)
            relations.append(
                Relation(
                    root,
                    finding.id,
                    "uses_wildcard_dns",
                    "DNS Misconfiguration Analyzer",
                    "high",
                    True,
                    finding.metadata["explanation"],
                    checked_at=_now(),
                    state="live",
                )
            )
        return ProviderResult(
            "DNS Misconfiguration Analyzer",
            "ok" if entities else "no_data",
            {"checks": checks, "cname_targets": cname_targets, "wildcard_probe": wildcard_name},
            entities,
            relations,
            error="" if entities else "No wildcard or dangling DNS candidate was identified",
        )

    return _run("DNS Misconfiguration Analyzer", load)
