"""Safe report export helpers shared by GUI features."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path


def write_json_report(path: str | Path, data: Mapping) -> Path:
    """Write a structured report as UTF-8 JSON."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def write_csv_rows(path: str | Path, fieldnames: list[str], rows: Iterable[Mapping]) -> Path:
    """Write RFC compatible CSV rows with proper quoting."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return destination
