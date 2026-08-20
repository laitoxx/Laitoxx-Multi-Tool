"""Load optional investigator-maintained TON address labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_labels(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(path)
    payload = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Labels JSON must be an object keyed by TON address")
    return payload
