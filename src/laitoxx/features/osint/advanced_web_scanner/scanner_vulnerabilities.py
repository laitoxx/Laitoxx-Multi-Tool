from __future__ import annotations

import json

from .models import Entity, ScanReport


class VulnerabilityMixin:
    @staticmethod
    def _cves(report: ScanReport) -> list[str]:
        return list(dict.fromkeys(entity.value for entity in report.entities if entity.kind == "cve"))

    @staticmethod
    def _enrich_vulnerabilities(report: ScanReport):
        """Merge vulnerability-provider answers into the CVE graph entities."""
        cves = {entity.value.upper(): entity for entity in report.entities if entity.kind == "cve"}
        entity_by_id = {entity.id: entity for entity in report.entities}
        for cve, entity in cves.items():
            metadata = entity.metadata
            sources = set(metadata.get("sources", []))
            sources.update(metadata.get("version_match_sources", []))
            sources.update(metadata.get("validation_sources", []))
            explanations = []
            for result in report.providers:
                data = result.data or {}
                if result.name == "NVD" and str(data.get("id", "")).upper() == cve:
                    description = str(data.get("description", "")).strip()
                    metadata.update(
                        {
                            key: data[key]
                            for key in ("cvss", "published", "modified", "weaknesses")
                            if data.get(key) is not None
                        }
                    )
                    if description:
                        metadata["description"] = description
                        explanations.append(description)
                    sources.add("NVD")
                elif result.name == "OSV.dev":
                    aliases = {str(item).upper() for item in data.get("aliases", []) or []}
                    if str(data.get("id", "")).upper() == cve or cve in aliases:
                        summary = str(data.get("summary", "")).strip()
                        details = str(data.get("details", "")).strip()
                        if summary:
                            metadata["osv_summary"] = summary
                            explanations.append(summary)
                        if details and not metadata.get("description"):
                            metadata["description"] = details
                        sources.add("OSV.dev")
                elif result.name == "GitHub Advisories":
                    advisories = [
                        item for item in data.get("advisories", []) if str(item.get("cve_id", "")).upper() == cve
                    ]
                    if advisories:
                        advisory = advisories[0]
                        metadata["github_advisories"] = advisories
                        metadata["ghsa_ids"] = sorted(
                            {str(item.get("ghsa_id")) for item in advisories if item.get("ghsa_id")}
                        )
                        summary = str(advisory.get("summary") or "").strip()
                        if summary:
                            metadata["github_summary"] = summary
                            explanations.append(summary)
                        github_cvss = advisory.get("cvss") or {}
                        try:
                            score = float(github_cvss.get("score"))
                            if metadata.get("cvss") is None:
                                metadata["cvss"] = score
                        except (AttributeError, TypeError, ValueError):
                            pass
                        if advisory.get("withdrawn_at"):
                            metadata["withdrawn"] = True
                        sources.add("GitHub Advisories")
                elif result.name == "VulnCheck NVD Community":
                    records = data.get("records", []) or []
                    matching = [item for item in records if cve in json.dumps(item).upper()]
                    if matching:
                        metadata["vulncheck_nvd"] = matching[:3]
                        sources.add("VulnCheck NVD Community")
                elif result.name == "VulnCheck KEV Community":
                    records = data.get("records", []) or []
                    matching = [item for item in records if cve in json.dumps(item).upper()]
                    if matching:
                        metadata["known_exploited"] = True
                        metadata["vulncheck_kev"] = matching[:3]
                        explanations.append("VulnCheck KEV: exploitation in the wild is reported.")
                        sources.add("VulnCheck KEV Community")
                elif result.name == "CISA KEV":
                    record = data.get("record") or {}
                    if str(record.get("cveID", "")).upper() == cve:
                        metadata["known_exploited"] = True
                        metadata["kev"] = record
                        explanations.append("CISA KEV: confirmed exploitation in the wild.")
                        sources.add("CISA KEV")
                elif result.name == "EPSS" and str(data.get("cve", "")).upper() == cve:
                    try:
                        metadata["epss"] = float(data.get("epss"))
                    except (TypeError, ValueError):
                        pass
                    try:
                        metadata["epss_percentile"] = float(data.get("percentile"))
                    except (TypeError, ValueError):
                        pass
                    sources.add("EPSS")

            cvss = metadata.get("cvss")
            if cvss is not None:
                severity = (
                    "critical"
                    if float(cvss) >= 9
                    else "high"
                    if float(cvss) >= 7
                    else "medium"
                    if float(cvss) >= 4
                    else "low"
                )
                metadata["severity"] = severity
                explanations.append(f"CVSS {float(cvss):.1f} ({severity}).")
            if metadata.get("epss") is not None:
                explanations.append(f"EPSS estimates {metadata['epss']:.1%} exploitation probability.")
            metadata["sources"] = sorted(sources)
            metadata["explanation"] = (
                " ".join(dict.fromkeys(explanations))
                or "Potential vulnerability signal; applicability is not independently confirmed."
            )

            incoming = [relation for relation in report.relations if relation.target == entity.id]
            if metadata.get("withdrawn"):
                confidence_state, confidence_score = "rejected", 0.0
            elif any(
                relation.relation == "validated_vulnerability"
                and (relation.current is True or relation.state == "confirmed")
                for relation in incoming
            ):
                confidence_state, confidence_score = "confirmed", 0.95
            elif any(
                relation.relation == "version_matched_vulnerability"
                and entity_by_id.get(relation.source, Entity("unknown", "unknown")).metadata.get(
                    "version_applicability"
                )
                not in {"ambiguous", "requires_vendor_advisory"}
                for relation in incoming
            ):
                confidence_state, confidence_score = "probable", 0.75
            else:
                confidence_state, confidence_score = "possible", 0.40
            metadata["confidence_state"] = confidence_state
            metadata["confidence_score"] = confidence_score

            for relation in report.relations:
                if relation.target == entity.id and relation.relation == "possible_vulnerability":
                    signal = relation.evidence or "Product/version applicability has not been confirmed"
                    relation.evidence = f"{signal}. {metadata['explanation']}"
