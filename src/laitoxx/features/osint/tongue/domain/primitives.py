"""Pure normalization and serialization helpers for TON investigations."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

NANOTON = 1_000_000_000


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ts_to_iso(value: Any) -> str | None:
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    return datetime.fromtimestamp(ts, tz=UTC).replace(microsecond=0).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def ton_amount(value: Any) -> float:
    return safe_int(value) / NANOTON


def short(value: str | None, left: int = 7, right: int = 5) -> str:
    if not value:
        return "?"
    if len(value) <= left + right + 3:
        return value
    return f"{value[:left]}…{value[-right:]}"


def stable_id(*parts: Any) -> str:
    raw = "\x1f".join(str(x) for x in parts)
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def flatten_text(value: Any, max_depth: int = 5) -> str:
    """Extract human-readable strings from nested decoded payloads/metadata."""
    found: list[str] = []

    def walk(obj: Any, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(obj, str):
            text = obj.strip()
            if text and len(text) <= 500:
                found.append(text)
        elif isinstance(obj, Mapping):
            preferred = ("comment", "text", "message", "name", "description", "symbol", "uri", "url")
            for key in preferred:
                if key in obj:
                    walk(obj[key], depth + 1)
            for key, val in obj.items():
                if key not in preferred:
                    walk(val, depth + 1)
        elif isinstance(obj, Sequence) and not isinstance(obj, (bytes, bytearray)):
            for item in obj[:50]:
                walk(item, depth + 1)

    walk(value, 0)
    # Stable de-duplication
    unique = list(dict.fromkeys(found))
    return " | ".join(unique)


def extract_comment(message: Mapping[str, Any] | None) -> str:
    if not message:
        return ""
    content = message.get("message_content") or {}
    decoded = content.get("decoded") if isinstance(content, Mapping) else None
    text = flatten_text(decoded)
    if text:
        return text[:500]
    # Some deployments/versions may expose a decoded field directly.
    text = flatten_text(message.get("decoded"))
    return text[:500]


def is_numeric_memo(text: str) -> bool:
    normalized = re.sub(r"[\s\-_.]", "", text or "")
    return normalized.isdigit() and 6 <= len(normalized) <= 32


def tx_succeeded(tx: Mapping[str, Any]) -> bool:
    desc = tx.get("description") or {}
    if not isinstance(desc, Mapping):
        return True
    if desc.get("aborted") is True:
        return False
    compute = desc.get("compute_ph") or {}
    action = desc.get("action") or {}
    if isinstance(compute, Mapping) and compute.get("success") is False:
        return False
    if isinstance(action, Mapping) and action.get("success") is False:
        return False
    return True


def repeated_params(name: str, values: Iterable[str]) -> list[tuple[str, str]]:
    return [(name, str(v)) for v in values]


# ---------------------------------------------------------------------------
# HTTP client with rate limiting and raw evidence preservation
# ---------------------------------------------------------------------------
