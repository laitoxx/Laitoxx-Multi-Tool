from __future__ import annotations

import email.utils
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from laitoxx.core.settings.paths import CACHE_DIR

from .catalog import BY_ID
from .configuration import auth_mode


class QuotaExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class QuotaStatus:
    provider_id: str
    mode: str
    remaining: int | None
    reset_at: str | None
    label: str
    exhausted: bool = False


class QuotaLedger:
    """Thread-safe local request ledger plus server-reported quota state."""

    def __init__(self, path: str | None = None):
        self.path = path or str(Path(CACHE_DIR) / "advanced_web_scanner_quotas.sqlite3")
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS request_events (
                    id INTEGER PRIMARY KEY, provider_id TEXT NOT NULL, auth_mode TEXT NOT NULL,
                    requested_at REAL NOT NULL, status_code INTEGER, outcome TEXT NOT NULL DEFAULT 'reserved'
                );
                CREATE INDEX IF NOT EXISTS idx_quota_events
                    ON request_events(provider_id, auth_mode, requested_at);
                CREATE TABLE IF NOT EXISTS remote_quota (
                    provider_id TEXT PRIMARY KEY, remaining INTEGER, limit_value INTEGER,
                    reset_at REAL, observed_at REAL NOT NULL, source TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cooldowns (
                    provider_id TEXT PRIMARY KEY, until_at REAL NOT NULL, reason TEXT NOT NULL
                );
            """)

    @staticmethod
    def _next_fixed_reset(now: datetime, seconds: int) -> datetime:
        if seconds == 86400:
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return now + timedelta(seconds=seconds)

    @staticmethod
    def _window_start(now: datetime, seconds: int, fixed: bool) -> datetime:
        if fixed and seconds == 86400:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        return now - timedelta(seconds=seconds)

    def acquire(self, provider_id: str) -> int:
        now = datetime.now(UTC)
        mode = auth_mode(provider_id)
        spec = BY_ID[provider_id]
        with self._lock, self._connect() as db:
            cooldown = db.execute(
                "SELECT until_at, reason FROM cooldowns WHERE provider_id=?", (provider_id,)
            ).fetchone()
            if cooldown and cooldown["until_at"] > now.timestamp():
                reset = datetime.fromtimestamp(cooldown["until_at"], UTC).isoformat()
                raise QuotaExceeded(f"{spec.name}: cooldown until {reset} ({cooldown['reason']})")
            remote = db.execute(
                "SELECT remaining, reset_at, observed_at FROM remote_quota WHERE provider_id=?", (provider_id,)
            ).fetchone()
            remote_fresh = remote and (remote["reset_at"] or remote["observed_at"] > now.timestamp() - 900)
            if (
                remote_fresh
                and remote["remaining"] == 0
                and (not remote["reset_at"] or remote["reset_at"] > now.timestamp())
            ):
                reset = datetime.fromtimestamp(remote["reset_at"], UTC).isoformat() if remote["reset_at"] else "unknown"
                raise QuotaExceeded(f"{spec.name}: server-reported quota exhausted; reset {reset}")
            for window in (spec.quotas or {}).get(mode, ()):
                since = self._window_start(now, window.seconds, window.fixed_utc)
                count = db.execute(
                    "SELECT COUNT(*) FROM request_events WHERE provider_id=? AND auth_mode=? AND requested_at>=?",
                    (provider_id, mode, since.timestamp()),
                ).fetchone()[0]
                if count >= window.limit:
                    if window.fixed_utc:
                        reset_dt = self._next_fixed_reset(now, window.seconds)
                    else:
                        oldest = db.execute(
                            "SELECT MIN(requested_at) FROM request_events WHERE provider_id=? AND auth_mode=? AND requested_at>=?",
                            (provider_id, mode, since.timestamp()),
                        ).fetchone()[0]
                        reset_dt = datetime.fromtimestamp(oldest + window.seconds, UTC)
                    raise QuotaExceeded(
                        f"{spec.name}: local quota {window.label} exhausted; reset {reset_dt.isoformat()}"
                    )
            cursor = db.execute(
                "INSERT INTO request_events(provider_id, auth_mode, requested_at) VALUES(?,?,?)",
                (provider_id, mode, now.timestamp()),
            )
            return int(cursor.lastrowid)

    def record_response(self, event_id: int, provider_id: str, status_code: int, headers) -> None:
        now = datetime.now(UTC)
        normalized = {str(key).lower(): value for key, value in dict(headers).items()}
        remaining = self._int_header(
            normalized,
            "x-ratelimit-remaining",
            "x-rate-limit-remaining",
            "remaining-requests",
            "x-api-quota",
        )
        limit_value = self._int_header(normalized, "x-ratelimit-limit", "x-rate-limit-limit")
        if provider_id == "hackertarget":
            limit_value = self._int_header(normalized, "x-api-quota")
            count = self._int_header(normalized, "x-api-count")
            boost = self._int_header(normalized, "x-api-boost") or 0
            if limit_value is not None and count is not None:
                remaining = max(0, limit_value + boost - count)
        reset_at = self._reset_header(normalized, now)
        if provider_id == "leakix" and status_code == 429 and reset_at is None:
            reset_at = self._limited_for_header(normalized, now)
        with self._lock, self._connect() as db:
            db.execute(
                "UPDATE request_events SET status_code=?, outcome=? WHERE id=?",
                (status_code, "ok" if status_code < 400 else "error", event_id),
            )
            if provider_id == "urlscan" and status_code != 200:
                db.execute("DELETE FROM request_events WHERE id=?", (event_id,))
            if remaining is not None or limit_value is not None or reset_at is not None:
                db.execute(
                    "INSERT OR REPLACE INTO remote_quota(provider_id,remaining,limit_value,reset_at,observed_at,source) VALUES(?,?,?,?,?,?)",
                    (
                        provider_id,
                        remaining,
                        limit_value,
                        reset_at.timestamp() if reset_at else None,
                        now.timestamp(),
                        "response headers",
                    ),
                )
            if status_code == 429:
                until = reset_at or (now + timedelta(minutes=1))
                db.execute(
                    "INSERT OR REPLACE INTO cooldowns VALUES(?,?,?)", (provider_id, until.timestamp(), "HTTP 429")
                )

    def update_remote(
        self,
        provider_id: str,
        *,
        remaining: int | None,
        limit_value: int | None = None,
        reset_at: datetime | None = None,
        source: str = "account endpoint",
    ) -> None:
        now = datetime.now(UTC)
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO remote_quota(provider_id,remaining,limit_value,reset_at,observed_at,source) VALUES(?,?,?,?,?,?)",
                (
                    provider_id,
                    remaining,
                    limit_value,
                    reset_at.timestamp() if reset_at else None,
                    now.timestamp(),
                    source,
                ),
            )

    @staticmethod
    def _int_header(headers: dict, *names: str) -> int | None:
        for name in names:
            try:
                return int(headers[name])
            except (KeyError, TypeError, ValueError):
                pass
        return None

    @staticmethod
    def _reset_header(headers: dict, now: datetime) -> datetime | None:
        value = headers.get("x-ratelimit-reset") or headers.get("x-rate-limit-reset") or headers.get("retry-after")
        if not value:
            return None
        try:
            number = float(value)
            return datetime.fromtimestamp(number, UTC) if number > 10_000_000 else now + timedelta(seconds=number)
        except (TypeError, ValueError, OSError):
            try:
                parsed = email.utils.parsedate_to_datetime(str(value))
                return parsed.astimezone(UTC)
            except (TypeError, ValueError):
                return None

    @staticmethod
    def _limited_for_header(headers: dict, now: datetime) -> datetime | None:
        value = str(headers.get("x-limited-for") or "").strip().lower()
        if not value:
            return None
        try:
            if value.endswith("ms"):
                seconds = float(value[:-2]) / 1000
            elif value.endswith("s"):
                seconds = float(value[:-1])
            else:
                seconds = float(value)
        except ValueError:
            return None
        return now + timedelta(seconds=max(0.05, seconds))

    def status(self, provider_id: str) -> QuotaStatus:
        spec = BY_ID[provider_id]
        mode = auth_mode(provider_id)
        now = datetime.now(UTC)
        candidates: list[tuple[int, datetime, str]] = []
        with self._connect() as db:
            cooldown = db.execute(
                "SELECT until_at, reason FROM cooldowns WHERE provider_id=?",
                (provider_id,),
            ).fetchone()
            if cooldown and cooldown["until_at"] > now.timestamp():
                reset = datetime.fromtimestamp(cooldown["until_at"], UTC)
                return QuotaStatus(
                    provider_id,
                    mode,
                    0,
                    reset.isoformat(),
                    str(cooldown["reason"]),
                    True,
                )
            remote = db.execute(
                "SELECT remaining, reset_at, observed_at FROM remote_quota WHERE provider_id=?", (provider_id,)
            ).fetchone()
            remote_fresh = remote and (remote["reset_at"] or remote["observed_at"] > now.timestamp() - 900)
            if (
                remote_fresh
                and remote["remaining"] is not None
                and (not remote["reset_at"] or remote["reset_at"] > now.timestamp())
            ):
                reset = datetime.fromtimestamp(remote["reset_at"], UTC) if remote["reset_at"] else None
                candidates.append((remote["remaining"], reset, "server"))
            for window in (spec.quotas or {}).get(mode, ()):
                since = self._window_start(now, window.seconds, window.fixed_utc)
                count = db.execute(
                    "SELECT COUNT(*) FROM request_events WHERE provider_id=? AND auth_mode=? AND requested_at>=?",
                    (provider_id, mode, since.timestamp()),
                ).fetchone()[0]
                if window.fixed_utc:
                    reset = self._next_fixed_reset(now, window.seconds)
                elif count:
                    oldest = db.execute(
                        "SELECT MIN(requested_at) FROM request_events WHERE provider_id=? AND auth_mode=? AND requested_at>=?",
                        (provider_id, mode, since.timestamp()),
                    ).fetchone()[0]
                    reset = datetime.fromtimestamp(oldest + window.seconds, UTC)
                else:
                    reset = None
                candidates.append((max(0, window.limit - count), reset, window.label))
        if not candidates:
            return QuotaStatus(provider_id, mode, None, None, "not published")
        remaining, reset, label = min(candidates, key=lambda item: item[0])
        if provider_id == "shodan_account":
            # Zero query credits disables banner downloads, not the free
            # filtered /host/count facet endpoint used by the scanner.
            return QuotaStatus(
                provider_id,
                mode,
                remaining,
                reset.isoformat() if reset else None,
                f"{remaining} search credits · free filtered facets available",
                False,
            )
        return QuotaStatus(provider_id, mode, remaining, reset.isoformat() if reset else None, label, remaining <= 0)


ledger = QuotaLedger()
