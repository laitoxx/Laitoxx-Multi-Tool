from __future__ import annotations

from .models import Relation, RiskFactor, ScanReport


class ReportFinalizationMixin:
    @staticmethod
    def _correlate_relations(report: ScanReport):
        groups = {}
        for relation in report.relations:
            if relation.relation != "historical_resolves_to":
                continue
            groups.setdefault((relation.source, relation.target), []).append(relation)
        for (source, target), relations in groups.items():
            sources = sorted({relation.source_name for relation in relations})
            if len(sources) >= 2:
                report.relations.append(
                    Relation(
                        source,
                        target,
                        "historical_resolves_to",
                        "Correlation",
                        "high",
                        False,
                        "Independent passive-DNS sources: " + ", ".join(sources),
                    )
                )

    @staticmethod
    def _deduplicate(report: ScanReport):
        entities = {}
        for entity in report.entities:
            existing = entities.get(entity.id)
            if existing:
                for key, value in entity.metadata.items():
                    if isinstance(value, list) and isinstance(existing.metadata.get(key), list):
                        existing.metadata[key] = list(dict.fromkeys([*existing.metadata[key], *value]))
                    elif isinstance(value, dict) and isinstance(existing.metadata.get(key), dict):
                        existing.metadata[key] = {**existing.metadata[key], **value}
                    else:
                        existing.metadata[key] = value
            else:
                entities[entity.id] = entity
        report.entities = list(entities.values())
        relation_keys = set()
        unique_relations = []
        for relation in report.relations:
            key = (relation.source, relation.target, relation.relation, relation.source_name)
            if key not in relation_keys:
                relation_keys.add(key)
                unique_relations.append(relation)
        report.relations = unique_relations

    @staticmethod
    def _calculate_risk(report: ScanReport):
        factors = []
        internetdb_results = [
            item for item in report.providers if item.name == "Shodan InternetDB" and item.status in {"ok", "cached"}
        ]
        services = [entity for entity in report.entities if entity.kind == "service"]
        live_services = [
            entity
            for entity in services
            if entity.metadata.get("evidence_state") in {"live", "confirmed"}
            or entity.metadata.get("actively_verified")
        ]
        candidate_services = [entity for entity in services if entity not in live_services]
        live_ports = {
            int(entity.metadata["port"])
            for entity in services
            if entity in live_services and str(entity.metadata.get("port", "")).isdigit()
        }
        candidate_ports = {port for item in internetdb_results for port in item.data.get("ports", [])}
        candidate_ports.update(
            int(entity.metadata["port"])
            for entity in candidate_services
            if str(entity.metadata.get("port", "")).isdigit()
        )
        sensitive_set = {21, 22, 23, 25, 110, 135, 139, 445, 1433, 2375, 3306, 3389, 5432, 5900, 6379, 9200, 11211}
        sensitive_live = sorted(live_ports & sensitive_set)
        sensitive_candidates = sorted((candidate_ports - live_ports) & sensitive_set)
        if sensitive_live:
            factors.append(
                RiskFactor(
                    "Sensitive services confirmed live",
                    min(20, 4 * len(sensitive_live)),
                    ", ".join(map(str, sensitive_live)),
                )
            )
        if sensitive_candidates:
            factors.append(
                RiskFactor(
                    "Sensitive service candidates",
                    min(8, 1.5 * len(sensitive_candidates)),
                    ", ".join(map(str, sensitive_candidates)) + "; current reachability not confirmed",
                )
            )
        if len(live_ports) >= 8:
            factors.append(RiskFactor("Large confirmed external service surface", 8, f"{len(live_ports)} live ports"))
        high_interest = {
            "database": "Database endpoints",
            "admin_panel": "Administration interfaces",
            "devops": "Infrastructure control interfaces",
        }
        for category, label in high_interest.items():
            matches = [entity for entity in live_services if entity.metadata.get("category") == category]
            if matches:
                points = min(10, len(matches) * (3 if category == "database" else 2))
                evidence = ", ".join(entity.value for entity in matches[:5])
                factors.append(
                    RiskFactor(
                        label,
                        points,
                        f"{evidence}; reachable service observation only, authentication and exploitability are not implied",
                    )
                )

        leakix_findings = [
            entity
            for entity in report.entities
            if entity.kind == "finding" and entity.metadata.get("source") == "LeakIX"
        ]
        if leakix_findings:
            severity_weight = {"critical": 16, "high": 11, "medium": 6, "low": 3, "unknown": 2}
            points = min(
                25,
                max(
                    severity_weight.get(str(entity.metadata.get("severity", "unknown")).lower(), 2)
                    for entity in leakix_findings
                )
                + min(9, len(leakix_findings) - 1),
            )
            evidence = ", ".join(
                f"{entity.metadata.get('finding_type', 'exposure')} ({entity.metadata.get('severity', 'unknown')})"
                for entity in leakix_findings[:5]
            )
            live = any(entity.metadata.get("evidence_state") in {"live", "confirmed"} for entity in leakix_findings)
            factors.append(
                RiskFactor(
                    "LeakIX exposure intelligence",
                    points if live else round(points * 0.4, 1),
                    evidence + ("" if live else "; historical/indexed observation, current reachability not confirmed"),
                )
            )

        abuse = next(
            (item for item in report.providers if item.name == "AbuseIPDB" and item.status in {"ok", "cached"}), None
        )
        if abuse:
            confidence = float(abuse.data.get("abuseConfidenceScore", 0) or 0)
            if confidence:
                factors.append(
                    RiskFactor("AbuseIPDB reputation", min(20, confidence * 0.2), f"confidence {confidence:.0f}%")
                )

        nvd_scores = []
        for item in report.providers:
            if item.name == "NVD" and item.data.get("cvss") is not None:
                nvd_scores.append(float(item.data["cvss"]))
        if nvd_scores:
            cve_states = {
                str(entity.metadata.get("confidence_state") or "possible")
                for entity in report.entities
                if entity.kind == "cve"
            }
            applicability = (
                1.0
                if report.target.kind == "cve"
                else (1.0 if "confirmed" in cve_states else 0.65 if "probable" in cve_states else 0.2)
            )
            factors.append(
                RiskFactor(
                    "Known vulnerability severity",
                    min(22, max(nvd_scores) * 2.2) * applicability,
                    f"max CVSS {max(nvd_scores):.1f}; "
                    + ("direct CVE target" if applicability == 1 else "weak product/version signal"),
                )
            )

        kev_records = [item for item in report.providers if item.name == "CISA KEV" and item.data.get("listed")]
        if kev_records:
            applicability = (
                1.0
                if report.target.kind == "cve"
                else (
                    1.0
                    if any(
                        entity.kind == "cve" and entity.metadata.get("confidence_state") == "confirmed"
                        for entity in report.entities
                    )
                    else 0.35
                )
            )
            factors.append(
                RiskFactor(
                    "Known exploited vulnerability",
                    min(30, 15 + 5 * len(kev_records)) * applicability,
                    f"{len(kev_records)} KEV match(es); applicability not automatically confirmed",
                )
            )

        epss_values = []
        for item in report.providers:
            if item.name == "EPSS" and item.data.get("epss"):
                epss_values.append(float(item.data["epss"]))
        if epss_values:
            applicability = 1.0 if report.target.kind == "cve" else 0.5
            factors.append(
                RiskFactor(
                    "Exploit probability",
                    min(20, max(epss_values) * 20) * applicability,
                    f"max EPSS {max(epss_values):.1%}",
                )
            )

        errors = sum(item.status == "error" for item in report.providers)
        unavailable = sum(
            item.status in {"skipped", "rate_limited", "unavailable", "restricted", "auth_error"}
            for item in report.providers
        )
        if errors or unavailable:
            factors.append(
                RiskFactor(
                    "Coverage penalty", 0, f"{errors} failed, {unavailable} unavailable; score may be incomplete"
                )
            )

        score = round(min(100, sum(factor.points for factor in factors)), 1)
        report.risk_score = score
        report.risk_level = "critical" if score >= 75 else "high" if score >= 50 else "medium" if score >= 25 else "low"
        report.risk_factors = factors
