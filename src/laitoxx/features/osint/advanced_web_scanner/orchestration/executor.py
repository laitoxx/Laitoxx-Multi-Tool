"""Concurrent provider execution and result aggregation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from ..models import ProviderResult, ScanReport

ProviderJob = Callable[[], ProviderResult]
ProgressCallback = Callable[[str, ProviderResult], None]


def merge_result(report: ScanReport, result: ProviderResult) -> None:
    result.checked_at = result.checked_at or datetime.now(UTC).isoformat()
    if result.status == "no_data":
        result.data.setdefault("negative_evidence", True)
        result.data.setdefault("checked_at", result.checked_at)
    report.providers.append(result)
    report.entities.extend(result.entities)
    report.relations.extend(result.relations)
    report.timeline.extend(result.timeline)


def run_jobs(
    jobs: Iterable[ProviderJob],
    report: ScanReport,
    *,
    workers: int,
    progress: ProgressCallback | None = None,
) -> None:
    scheduled = list(jobs)
    if not scheduled:
        return
    max_workers = max(1, min(workers, len(scheduled)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(job) for job in scheduled]
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                result = ProviderResult("Pipeline", "error", error=str(exc))
            merge_result(report, result)
            if progress:
                progress(result.name, result)
