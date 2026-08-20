"""Vulnerability intelligence providers.

This module owns CVE lookups and version-to-vulnerability matching. Network,
shared cache and quota primitives live in provider_common.
"""

from __future__ import annotations

import json
import re
import threading
from urllib.parse import quote

from .. import provider_common as _common
from ..configuration import credential
from ..models import Entity, ProviderResult, Relation, TimelineEvent

_FEED_LOCK = threading.Lock()
_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run
skipped = _common.skipped


def vulnerability(cve: str) -> list[ProviderResult]:
    cve = cve.upper()
    results = [nvd(cve), osv(cve), github_advisories(cve), kev(cve), epss(cve)]
    if credential("vulncheck"):
        results.extend((vulncheck_nvd(cve), vulncheck_kev(cve)))
    return results


def nvd(cve: str) -> ProviderResult:
    def load():
        key = credential("nvd")
        headers = {"apiKey": key} if key else {}
        data, hit = _cached_json(
            "nvd",
            cve,
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"cveId": cve},
            headers=headers,
            ttl=86400,
        )
        records = data.get("vulnerabilities", [])
        compact = {}
        if records:
            item = records[0].get("cve", {})
            descriptions = item.get("descriptions", [])
            metrics = item.get("metrics", {})
            scores = []
            for values in metrics.values():
                for metric in values if isinstance(values, list) else []:
                    score = metric.get("cvssData", {}).get("baseScore")
                    if score is not None:
                        scores.append(float(score))
            compact = {
                "id": item.get("id", cve),
                "published": item.get("published"),
                "modified": item.get("lastModified"),
                "description": next((d.get("value") for d in descriptions if d.get("lang") == "en"), ""),
                "cvss": max(scores) if scores else None,
                "weaknesses": item.get("weaknesses", []),
            }
        events = (
            [TimelineEvent(compact["published"], _now(), "NVD", "published", cve, confidence="high")]
            if compact.get("published")
            else []
        )
        return ProviderResult("NVD", "cached" if hit else "ok", compact, timeline=events)

    return _run("NVD", load)


def osv(cve: str) -> ProviderResult:
    def load():
        data, hit = _cached_json("osv", cve, f"https://api.osv.dev/v1/vulns/{quote(cve)}", ttl=86400)
        compact = {
            key: data.get(key) for key in ("id", "summary", "details", "aliases", "modified", "published", "affected")
        }
        return ProviderResult("OSV.dev", "cached" if hit else "ok", compact)

    return _run("OSV.dev", load)


def github_advisories(cve: str) -> ProviderResult:
    """Query GitHub's public, global advisory database for one CVE."""
    cve = cve.upper()

    def load():
        token = credential("github_advisories")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data, hit = _cached_json(
            "github_advisories",
            cve,
            "https://api.github.com/advisories",
            params={"cve_id": cve, "per_page": 10},
            headers=headers,
            ttl=86400,
        )
        records = data if isinstance(data, list) else []
        compact = []
        for item in records[:10]:
            compact.append(
                {
                    key: item.get(key)
                    for key in (
                        "ghsa_id",
                        "cve_id",
                        "url",
                        "html_url",
                        "summary",
                        "description",
                        "severity",
                        "published_at",
                        "updated_at",
                        "withdrawn_at",
                        "cvss",
                        "cwes",
                        "references",
                        "vulnerabilities",
                    )
                }
            )
        events = [
            TimelineEvent(
                item["published_at"], _now(), "GitHub Advisories", "published", cve, item.get("ghsa_id", ""), "high"
            )
            for item in compact
            if item.get("published_at")
        ]
        status = "cached" if hit else "ok"
        if not compact:
            status = "no_data"
        return ProviderResult("GitHub Advisories", status, {"advisories": compact}, timeline=events)

    return _run("GitHub Advisories", load)


def _vulncheck_index(cve: str, index: str, namespace: str, name: str) -> ProviderResult:
    token = credential("vulncheck")
    if not token:
        return skipped(name, "VULNCHECK_API_TOKEN is not configured")
    cve = cve.upper()

    def load():
        data, hit = _cached_json(
            namespace,
            cve,
            f"https://api.vulncheck.com/v3/index/{index}",
            params={"cve": cve, "limit": 10},
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            ttl=86400,
        )
        records = data.get("data", []) if isinstance(data, dict) else []
        status = "cached" if hit else "ok"
        if not records:
            status = "no_data"
        return ProviderResult(name, status, {"cve": cve, "records": records[:10]})

    return _run(name, load)


def vulncheck_nvd(cve: str) -> ProviderResult:
    # nist-nvd2 is the Community index. vulncheck-nvd2 is a paid product.
    return _vulncheck_index(cve, "nist-nvd2", "vulncheck_nvd", "VulnCheck NVD Community")


def vulncheck_kev(cve: str) -> ProviderResult:
    return _vulncheck_index(cve, "vulncheck-kev", "vulncheck_kev", "VulnCheck KEV Community")


def _candidate_result(
    name: str, product: str, version: str, technology_value: str, records: list[dict], cves: set[str], cached: bool
) -> ProviderResult:
    cves = set(sorted(cves)[:12])
    technology_id = _entity_id("technology", technology_value)
    entities = [
        Entity(
            "cve",
            cve,
            metadata={
                "matched_product": product,
                "matched_version": version,
                "version_match_sources": [name],
            },
        )
        for cve in sorted(cves)
    ]
    relations = [
        Relation(
            technology_id,
            _entity_id("cve", cve),
            "version_matched_vulnerability",
            name,
            "medium",
            None,
            f"{product} {version}",
        )
        for cve in sorted(cves)
    ]
    return ProviderResult(
        name,
        "cached" if cached else "ok" if cves else "no_data",
        {"product": product, "version": version, "records": records[:20]},
        entities,
        relations,
    )


def nvd_version_match(product: str, version: str, technology_value: str) -> ProviderResult:
    name = "NVD Version Match"

    def load():
        key = credential("nvd")
        headers = {"apiKey": key} if key else {}
        data, hit = _cached_json(
            "nvd_match",
            f"{product}@{version}",
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"keywordSearch": f"{product} {version}", "noRejected": "", "resultsPerPage": 20},
            headers=headers,
            ttl=86400,
        )
        records = [item.get("cve", {}) for item in data.get("vulnerabilities", [])[:20]]
        cves = {
            str(item.get("id", "")).upper() for item in records if str(item.get("id", "")).upper().startswith("CVE-")
        }
        return _candidate_result(name, product, version, technology_value, records, cves, hit)

    return _run(name, load)


def osv_version_match(product: str, version: str, technology_value: str, ecosystem: str) -> ProviderResult:
    name = "OSV Version Match"
    if not ecosystem:
        return skipped(name, f"No OSV ecosystem mapping for {product}")

    def load():
        data, hit = _cached_json(
            "osv_match",
            f"{ecosystem}:{product}@{version}",
            "https://api.osv.dev/v1/query",
            method="post",
            body={"version": version, "package": {"name": product, "ecosystem": ecosystem}},
            ttl=86400,
        )
        records = data.get("vulns", []) if isinstance(data, dict) else []
        cves = {match.upper() for item in records for match in re.findall(r"CVE-\d{4}-\d{4,}", json.dumps(item), re.I)}
        return _candidate_result(name, product, version, technology_value, records, cves, hit)

    return _run(name, load)


def github_version_match(product: str, version: str, technology_value: str) -> ProviderResult:
    name = "GitHub Advisory Version Match"

    def load():
        token = credential("github_advisories")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data, hit = _cached_json(
            "github_affects",
            f"{product}@{version}",
            "https://api.github.com/advisories",
            params={"affects": f"{product}@{version}", "per_page": 20},
            headers=headers,
            ttl=86400,
        )
        records = data if isinstance(data, list) else []
        cves = {
            str(item.get("cve_id", "")).upper()
            for item in records
            if str(item.get("cve_id", "")).upper().startswith("CVE-")
        }
        return _candidate_result(name, product, version, technology_value, records, cves, hit)

    return _run(name, load)


def vulncheck_version_match(product: str, version: str, technology_value: str) -> ProviderResult:
    name = "VulnCheck CPE Version Match"
    token = credential("vulncheck")
    if not token:
        return skipped(name, "VULNCHECK_API_TOKEN is not configured")

    def load():
        normalized_product = re.sub(r"[^a-z0-9._-]+", "_", product.casefold()).strip("_")
        data, hit = _cached_json(
            "vulncheck_cpe_search",
            f"{normalized_product}@{version}",
            "https://api.vulncheck.com/v3/search/cpe",
            params={"part": "a", "product": normalized_product, "version": version, "isVulnerable": "true"},
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            ttl=86400,
        )
        records = data.get("data", []) if isinstance(data, dict) else []
        cves = {
            str(cve).upper() for item in records for cve in item.get("cves", []) if str(cve).upper().startswith("CVE-")
        }
        return _candidate_result(name, product, version, technology_value, records, cves, hit)

    return _run(name, load)


def kev(cve: str) -> ProviderResult:
    def load():
        with _FEED_LOCK:
            data, hit = _cached_json(
                "cisa_kev_feed",
                "catalog",
                "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                ttl=86400,
            )
        record = next((item for item in data.get("vulnerabilities", []) if item.get("cveID", "").upper() == cve), None)
        events = (
            [TimelineEvent(record["dateAdded"], _now(), "CISA KEV", "added_to_kev", cve, confidence="high")]
            if record
            else []
        )
        return ProviderResult(
            "CISA KEV", "cached" if hit else "ok", {"listed": bool(record), "record": record}, timeline=events
        )

    return _run("CISA KEV", load)


def epss(cve: str) -> ProviderResult:
    def load():
        data, hit = _cached_json("epss", cve, "https://api.first.org/data/v1/epss", params={"cve": cve}, ttl=43200)
        record = (data.get("data") or [{}])[0]
        return ProviderResult("EPSS", "cached" if hit else "ok", record)

    return _run("EPSS", load)
