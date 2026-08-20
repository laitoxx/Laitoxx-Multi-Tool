"""LeakIX evidence sanitization rules.

Raw banners and credential values must never leave the provider boundary.
"""

from __future__ import annotations

import re
from typing import Any


def redact_text(value: Any, limit: int = 2000) -> str:
    text = str(value or "")
    text = re.sub(
        r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret|authorization)\b\s*[:=]\s*[^\s,;]+",
        r"\1=<redacted>",
        text,
    )
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/-]+", "Bearer <redacted>", text)
    return text[:limit]


def compact_event(event: dict) -> dict:
    """Keep investigation evidence while excluding raw leaked credentials."""
    service = event.get("service") or {}
    credentials = service.get("credentials") or {}
    software = service.get("software") or {}
    http_data = event.get("http") or {}
    leak = event.get("leak") or {}
    return {
        key: event.get(key)
        for key in (
            "event_type",
            "event_source",
            "event_fingerprint",
            "ip",
            "host",
            "reverse",
            "port",
            "transport",
            "protocol",
            "time",
            "creation_date",
            "update_date",
            "tags",
        )
    } | {
        "summary": redact_text(event.get("summary"), 1000),
        "http": {
            "root": str(http_data.get("root") or "").split("?", 1)[0],
            "url": str(http_data.get("url") or "").split("?", 1)[0],
            "status": http_data.get("status"),
            "length": http_data.get("length"),
            "title": http_data.get("title"),
        },
        "service": {
            "software": software,
            "credentials": {
                "noauth": bool(credentials.get("noauth")),
                "username_present": bool(credentials.get("username")),
                "password_present": bool(credentials.get("password")),
                "key_present": bool(credentials.get("key")),
                "raw_present": bool(credentials.get("raw")),
            },
        },
        "leak": {
            "stage": leak.get("stage"),
            "type": leak.get("type"),
            "severity": leak.get("severity"),
            "dataset": leak.get("dataset") or {},
        },
        "network": event.get("network") or {},
    }
