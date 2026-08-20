"""Derived HTTP/TLS hardening observations from authorized fingerprints."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from .models import Entity, ProviderResult, Relation, ScanReport

_SECURITY_HEADERS = {
    "strict-transport-security": ("HSTS", "medium"),
    "content-security-policy": ("CSP", "low"),
    "x-content-type-options": ("X-Content-Type-Options", "low"),
    "referrer-policy": ("Referrer-Policy", "info"),
}


def analyze_active_posture(report: ScanReport) -> ProviderResult:
    entities: list[Entity] = []
    relations: list[Relation] = []
    analyzed = 0
    for result in report.providers:
        if result.name != "httpx Fingerprinting":
            continue
        for record in result.data.get("records", []) or []:
            url = str(record.get("url") or record.get("input") or "").strip()
            if not url:
                continue
            analyzed += 1
            raw_headers = record.get("header") or record.get("headers") or record.get("response_headers") or {}
            if isinstance(raw_headers, list):
                headers = {}
                for line in raw_headers:
                    key, separator, value = str(line).partition(":")
                    if separator:
                        headers[key.casefold().strip()] = value.strip()
            elif isinstance(raw_headers, dict):
                headers = {str(key).casefold(): str(value) for key, value in raw_headers.items()}
            else:
                headers = {}
            if headers:
                for header, (label, severity) in _SECURITY_HEADERS.items():
                    if header in headers:
                        continue
                    finding = Entity(
                        "finding",
                        f"{url}:missing:{header}",
                        label=f"Missing {label}",
                        metadata={
                            "category": "http_hardening",
                            "severity": severity,
                            "evidence_state": "live",
                            "hardening_finding": True,
                            "explanation": f"The live HTTP response did not include {label}. This is a hardening observation, not a vulnerability confirmation.",
                        },
                    )
                    entities.append(finding)
                    relations.append(
                        Relation(
                            f"url:{url.casefold()}",
                            finding.id,
                            "missing_security_header",
                            "HTTP Posture Analyzer",
                            "high",
                            True,
                            finding.metadata["explanation"],
                            state="live",
                        )
                    )

            tls = record.get("tls") or {}
            if isinstance(tls, dict):
                not_after = str(tls.get("not_after") or tls.get("notafter") or "").strip()
                if not_after and _expired(not_after):
                    finding = Entity(
                        "finding",
                        f"{url}:expired-certificate",
                        label="Expired TLS certificate",
                        metadata={
                            "category": "tls_misconfiguration",
                            "severity": "high",
                            "evidence_state": "confirmed",
                            "not_after": not_after,
                            "explanation": "The certificate presented during active fingerprinting is expired.",
                        },
                    )
                    entities.append(finding)
                    relations.append(
                        Relation(
                            f"url:{url.casefold()}",
                            finding.id,
                            "has_tls_misconfiguration",
                            "TLS Posture Analyzer",
                            "high",
                            True,
                            finding.metadata["explanation"],
                            state="confirmed",
                        )
                    )
    return ProviderResult(
        "HTTP & TLS Posture Analyzer",
        "ok" if entities else "no_data",
        data={"responses_analyzed": analyzed, "findings": len(entities), "derived_only": True},
        entities=entities,
        relations=relations,
        error="" if entities else "No supported HTTP header or TLS hardening finding was derived",
    )


def _expired(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed < datetime.now(UTC)
