"""Canonical product identity and conservative version reconciliation."""

from __future__ import annotations

import re

from .models import Entity, ScanReport

_ALIASES = {
    "apache http server": ("apache", "http_server", "Apache HTTP Server"),
    "apache httpd": ("apache", "http_server", "Apache HTTP Server"),
    "httpd": ("apache", "http_server", "Apache HTTP Server"),
    "nginx": ("f5", "nginx", "nginx"),
    "microsoft iis": ("microsoft", "internet_information_services", "Microsoft IIS"),
    "iis": ("microsoft", "internet_information_services", "Microsoft IIS"),
    "postgres": ("postgresql", "postgresql", "PostgreSQL"),
    "postgresql": ("postgresql", "postgresql", "PostgreSQL"),
    "mongo": ("mongodb", "mongodb", "MongoDB"),
    "mongodb": ("mongodb", "mongodb", "MongoDB"),
    "elastic": ("elastic", "elasticsearch", "Elasticsearch"),
    "elasticsearch": ("elastic", "elasticsearch", "Elasticsearch"),
    "wordpress": ("wordpress", "wordpress", "WordPress"),
}
_VERSION_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+){0,4}(?:[-+._][0-9A-Za-z.-]+)?)(?!\d)")


def normalize_technologies(report: ScanReport) -> None:
    """Enrich technology/CPE nodes without inventing missing versions."""
    identities: dict[tuple[str, str], list[Entity]] = {}
    for entity in report.entities:
        if entity.kind not in {"technology", "cpe"}:
            continue
        metadata = entity.metadata
        raw_product = str(metadata.get("product") or metadata.get("service_name") or entity.value).strip()
        raw_version = str(metadata.get("version") or "").strip()
        if not raw_version:
            match = _VERSION_RE.search(entity.value)
            raw_version = match.group(1) if match else ""
        vendor, product, display = _canonical(raw_product)
        metadata.update(
            {
                "vendor": str(metadata.get("vendor") or vendor).strip().casefold(),
                "product": product,
                "canonical_product": product,
                "display_product": display,
                "version": _clean_version(raw_version),
            }
        )
        if product and metadata["vendor"]:
            metadata.setdefault(
                "purl",
                f"pkg:generic/{metadata['vendor']}/{product}"
                + (f"@{metadata['version']}" if metadata["version"] else ""),
            )
        metadata.setdefault("identity_confidence", "high" if entity.kind == "cpe" else "medium")
        if metadata["vendor"] in {"canonical", "debian", "redhat", "rocky", "suse", "ubuntu"}:
            metadata["distribution_backport_possible"] = True
            metadata["version_applicability"] = "requires_vendor_advisory"
        identities.setdefault((metadata["vendor"], product), []).append(entity)

    for (_vendor, _product), entities in identities.items():
        versions = sorted({str(entity.metadata.get("version") or "") for entity in entities} - {""})
        sources = sorted(
            {
                str(source)
                for entity in entities
                for source in entity.metadata.get("evidence_sources", entity.metadata.get("sources", []))
                if source
            }
        )
        for entity in entities:
            entity.metadata["observed_versions"] = versions
            entity.metadata["identity_sources"] = sources
            if len(versions) > 1:
                entity.metadata["version_conflict"] = True
                entity.metadata["version_applicability"] = "ambiguous"
            elif versions:
                entity.metadata.setdefault("version_applicability", "candidate")


def _canonical(raw: str) -> tuple[str, str, str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", raw.casefold()).strip()
    for alias, identity in _ALIASES.items():
        if normalized == alias or normalized.startswith(alias + " "):
            return identity
    product = normalized.replace(" ", "_")[:100]
    vendor = product.split("_", 1)[0] if product else "unknown"
    return vendor, product, raw.strip() or product


def _clean_version(value: str) -> str:
    value = value.strip().lstrip("vV")
    return value if _VERSION_RE.fullmatch(value) else ""
