"""Persistent health observations for username providers."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from laitoxx.core.settings.paths import CACHE_DIR

from .models import CheckResult

_CONCLUSIVE = {"confirmed", "probable", "found", "not_found", "login_required"}
_UNHEALTHY = {"timeout", "network_error", "rate_limited", "waf_blocked", "error"}


class ProviderHealthStore:
    """Track provider reliability without modifying the shipped database."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or CACHE_DIR / "username_osint" / "provider_health.json")
        self._lock = threading.Lock()
        self._data = self._load()
        self._dirty = False

    def _load(self) -> dict[str, dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def get(self, site_name: str) -> dict:
        with self._lock:
            return dict(self._data.get(site_name, {}))

    def record(self, result: CheckResult) -> None:
        with self._lock:
            item = self._data.setdefault(result.site_name, {})
            item["checks"] = int(item.get("checks", 0)) + 1
            if result.status in _CONCLUSIVE:
                item["conclusive"] = int(item.get("conclusive", 0)) + 1
                item["consecutive_failures"] = 0
            elif result.status in _UNHEALTHY:
                item["consecutive_failures"] = int(item.get("consecutive_failures", 0)) + 1
            item["last_status"] = result.status
            item["last_checked"] = datetime.now(UTC).isoformat()
            checks = max(1, int(item["checks"]))
            item["reliability"] = round(int(item.get("conclusive", 0)) / checks, 3)
            self._dirty = True

    def is_degraded(self, site_name: str) -> bool:
        item = self.get(site_name)
        return int(item.get("checks", 0)) >= 5 and (
            float(item.get("reliability", 1.0)) < 0.2 or int(item.get("consecutive_failures", 0)) >= 5
        )

    def flush(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            snapshot = dict(self._data)
            self._dirty = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
