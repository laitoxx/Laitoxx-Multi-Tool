"""Passive subdomain discovery and optional endpoint verification."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import quote

import requests

from laitoxx.core.dns import query_dns
from laitoxx.core.settings.network_manager import NetworkManager, get_session
from laitoxx.core.settings.paths import CACHE_DIR
from laitoxx.core.settings.tls import trusted_ssl_context
from laitoxx.shared.execution import (
    JobControl,
    OperationCancelled,
    OperationIssue,
    ProgressCallback,
    ProgressEvent,
    emit_progress,
)


@dataclass(frozen=True)
class SubdomainDiscoveryConfig:
    """Controls passive discovery and optional verification work."""

    resolve_dns: bool = True
    probe_http: bool = False
    timeout: float = 8.0
    max_workers: int = 20
    max_results: int = 2000
    cache_ttl_seconds: int = 86400


@dataclass
class SubdomainRecord:
    """One normalized subdomain with source and verification evidence."""

    hostname: str
    sources: list[str] = field(default_factory=list)
    wildcard_observed: bool = False
    ipv4: list[str] = field(default_factory=list)
    ipv6: list[str] = field(default_factory=list)
    cname: list[str] = field(default_factory=list)
    http_url: str = ""
    http_status: int | None = None
    error: str = ""

    @property
    def resolves(self) -> bool:
        return bool(self.ipv4 or self.ipv6 or self.cname)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["resolves"] = self.resolves
        return data


@dataclass
class SubdomainDiscoveryReport:
    """Structured result for the Domain Intelligence subdomain panel."""

    domain: str
    records: list[SubdomainRecord] = field(default_factory=list)
    issues: list[OperationIssue] = field(default_factory=list)
    cached: bool = False
    cancelled: bool = False
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "records": [record.to_dict() for record in self.records],
            "issues": [issue.to_dict() for issue in self.issues],
            "cached": self.cached,
            "cancelled": self.cancelled,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "summary": {
                "discovered": len(self.records),
                "resolved": sum(record.resolves for record in self.records),
                "http_available": sum(record.http_status is not None for record in self.records),
            },
        }


def _cache_path(domain: str) -> Path:
    digest = hashlib.sha256(domain.encode("utf-8")).hexdigest()
    return CACHE_DIR / "domain_intelligence" / "certificate_transparency" / f"{digest}.json"


def _load_cache(domain: str, ttl: int) -> list[dict] | None:
    path = _cache_path(domain)
    try:
        if time.time() - path.stat().st_mtime > ttl:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else None
    except (OSError, ValueError, TypeError):
        return None


def _save_cache(domain: str, rows: list[dict]) -> None:
    path = _cache_path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def _fetch_crt_rows(domain: str, timeout: float) -> list[dict]:
    started = time.monotonic()
    url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"
    headers = {"Accept": "application/json", "User-Agent": "Laitoxx-Domain-Intelligence/1.0"}
    try:
        response = get_session().get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as primary_error:
        if NetworkManager.is_active():
            raise
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("crt.sh exceeded the request time budget") from primary_error
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(  # noqa: S310
            request,
            timeout=remaining,
            context=trusted_ssl_context(),
        ) as response:
            data = json.load(response)
    if not isinstance(data, list):
        raise ValueError("crt.sh returned an unexpected JSON document")
    return [row for row in data if isinstance(row, dict)]


def _normalize_candidate(value: str, root_domain: str) -> tuple[str, bool] | None:
    candidate = str(value or "").strip().casefold().rstrip(".")
    wildcard = candidate.startswith("*.")
    if wildcard:
        candidate = candidate[2:]
    try:
        candidate = candidate.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if candidate == root_domain or not candidate.endswith("." + root_domain):
        return None
    labels = candidate.split(".")
    if any(not label or len(label) > 63 for label in labels):
        return None
    return candidate, wildcard


def _records_from_rows(rows: list[dict], domain: str, limit: int) -> list[SubdomainRecord]:
    merged: dict[str, SubdomainRecord] = {}
    for row in rows:
        values: list[str] = []
        for field_name in ("common_name", "name_value"):
            raw = row.get(field_name, "")
            values.extend(str(raw).replace("\r", "\n").splitlines())
        for value in values:
            normalized = _normalize_candidate(value, domain)
            if normalized is None:
                continue
            hostname, wildcard = normalized
            record = merged.setdefault(hostname, SubdomainRecord(hostname=hostname))
            if "crt.sh" not in record.sources:
                record.sources.append("crt.sh")
            record.wildcard_observed = record.wildcard_observed or wildcard
            if len(merged) >= limit:
                break
        if len(merged) >= limit:
            break
    return sorted(merged.values(), key=lambda item: item.hostname)


def _probe_record(
    record: SubdomainRecord,
    config: SubdomainDiscoveryConfig,
    control: JobControl,
) -> SubdomainRecord:
    if config.resolve_dns:
        control.checkpoint()
        record.ipv4 = query_dns(record.hostname, "A", config.timeout)
        control.checkpoint()
        record.ipv6 = query_dns(record.hostname, "AAAA", config.timeout)
        control.checkpoint()
        record.cname = query_dns(record.hostname, "CNAME", config.timeout)
    if config.probe_http:
        last_error = ""
        with requests.Session() as session:
            for scheme in ("https", "http"):
                control.checkpoint()
                try:
                    response = session.head(
                        f"{scheme}://{record.hostname}",
                        timeout=config.timeout,
                        allow_redirects=True,
                        headers={"User-Agent": "Laitoxx-Domain-Intelligence/1.0"},
                    )
                    if response.status_code in {405, 501}:
                        response.close()
                        response = session.get(
                            f"{scheme}://{record.hostname}",
                            timeout=config.timeout,
                            allow_redirects=True,
                            stream=True,
                            headers={"User-Agent": "Laitoxx-Domain-Intelligence/1.0"},
                        )
                    record.http_status = response.status_code
                    record.http_url = response.url
                    response.close()
                    break
                except Exception as error:
                    last_error = str(error)
        if record.http_status is None:
            record.error = last_error
    return record


def discover_subdomains(
    value: str,
    config: SubdomainDiscoveryConfig | None = None,
    progress: ProgressCallback | None = None,
    control: JobControl | None = None,
) -> SubdomainDiscoveryReport:
    """Discover certificate names and optionally verify their endpoints."""

    from .domain_intelligence import normalize_domain

    started = time.monotonic()
    config = config or SubdomainDiscoveryConfig()
    control = control or JobControl()
    domain = normalize_domain(value)
    report = SubdomainDiscoveryReport(domain=domain)
    emit_progress(progress, ProgressEvent("certificate_transparency", message="Querying certificate transparency"))
    try:
        control.checkpoint()
        rows = _load_cache(domain, config.cache_ttl_seconds)
        if rows is None:
            rows = _fetch_crt_rows(domain, config.timeout)
            _save_cache(domain, rows)
        else:
            report.cached = True
        report.records = _records_from_rows(rows, domain, config.max_results)
    except OperationCancelled:
        report.cancelled = True
    except Exception as error:
        report.issues.append(OperationIssue("crt.sh", str(error), "certificate_transparency_error"))

    if report.records and (config.resolve_dns or config.probe_http) and not report.cancelled:
        emit_progress(progress, ProgressEvent("verification", 0, len(report.records), "Verifying subdomains"))
        workers = max(1, min(config.max_workers, 50))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="subdomain-verify") as executor:
            futures = {executor.submit(_probe_record, record, config, control): record for record in report.records}
            completed = 0
            for future in as_completed(futures):
                if control.cancelled:
                    report.cancelled = True
                    for pending in futures:
                        pending.cancel()
                    break
                try:
                    future.result()
                except OperationCancelled:
                    report.cancelled = True
                except Exception as error:
                    futures[future].error = str(error)
                completed += 1
                emit_progress(
                    progress,
                    ProgressEvent("verification", completed, len(report.records), item=futures[future].hostname),
                )
    report.elapsed_seconds = time.monotonic() - started
    emit_progress(progress, ProgressEvent("complete", len(report.records), len(report.records), "Discovery complete"))
    return report
