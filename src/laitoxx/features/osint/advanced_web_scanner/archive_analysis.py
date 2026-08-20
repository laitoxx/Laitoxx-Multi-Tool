"""Local, non-fetching attack-surface extraction from archive URL results."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlparse

from .models import Entity, ProviderResult, Relation, ScanReport

_INTERESTING_SUFFIXES = {
    ".js": "javascript",
    ".map": "source_map",
    ".json": "json_document",
    ".yaml": "api_document",
    ".yml": "api_document",
    ".xml": "xml_document",
    ".sql": "database_artifact",
    ".env": "environment_file",
    ".git": "repository_artifact",
}
_API_RE = re.compile(r"(?:^|/)(?:api|graphql|swagger|openapi|actuator|management)(?:/|$)", re.I)
_ADMIN_RE = re.compile(r"(?:^|/)(?:admin|dashboard|console|manage|manager|phpmyadmin)(?:/|$)", re.I)
_STORAGE_SUFFIXES = (
    ".s3.amazonaws.com",
    ".s3-website.amazonaws.com",
    ".blob.core.windows.net",
    ".storage.googleapis.com",
    ".digitaloceanspaces.com",
)


def analyze(report: ScanReport, *, limit: int = 500) -> ProviderResult:
    urls = sorted({entity.value for entity in report.entities if entity.kind == "url"})[:limit]
    entities: list[Entity] = []
    relations: list[Relation] = []
    parameter_names: set[str] = set()
    for url in urls:
        parsed = urlparse(url)
        path = parsed.path or "/"
        lower_path = path.casefold()
        category = next((label for suffix, label in _INTERESTING_SUFFIXES.items() if lower_path.endswith(suffix)), "")
        if not category and _API_RE.search(path):
            category = "api_endpoint"
        elif not category and _ADMIN_RE.search(path):
            category = "administration_endpoint"
        elif parsed.hostname and any(parsed.hostname.casefold().endswith(suffix) for suffix in _STORAGE_SUFFIXES):
            category = "cloud_storage_endpoint"
        if category:
            artifact = Entity(
                "web_artifact",
                url,
                metadata={
                    "category": category,
                    "historical": True,
                    "evidence_state": "historical",
                    "active_fetch_required": True,
                },
            )
            entities.append(artifact)
            relations.append(
                Relation(
                    f"domain:{parsed.hostname.casefold()}",
                    artifact.id,
                    "archived_artifact",
                    "Archive Analyzer",
                    "low",
                    False,
                    "Derived from an archived URL; current availability is not implied",
                    state="historical",
                )
            )
        parameter_names.update(name for name, _value in parse_qsl(parsed.query, keep_blank_values=True) if name)

    for name in sorted(parameter_names)[:100]:
        entities.append(Entity("url_parameter", name, metadata={"historical": True, "evidence_state": "historical"}))

    return ProviderResult(
        "Archive Surface Analyzer",
        "ok" if entities else "no_data",
        data={
            "urls_analyzed": len(urls),
            "artifacts": sum(entity.kind == "web_artifact" for entity in entities),
            "parameter_names": sorted(parameter_names)[:100],
            "network_fetches": 0,
        },
        entities=entities,
        relations=relations,
        error="" if entities else "No archived API, script, source-map or administration artifacts were identified",
    )
