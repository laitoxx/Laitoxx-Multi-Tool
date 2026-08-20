"""Rate-limited TON Center HTTP client with raw evidence preservation."""

from __future__ import annotations

import json
import random
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from laitoxx.core.settings.network_manager import get_session

from ..domain.primitives import jsonable, stable_id, utc_now_iso

V3_BASE = "https://toncenter.com/api/v3"
V2_BASE = "https://toncenter.com/api/v2"
USER_AGENT = "TON-Public-Correlator/0.5 (+public blockchain research)"


class TonCenterError(RuntimeError):
    pass


class OperationCancelled(RuntimeError):
    """Raised when the GUI asks a running public investigation to stop."""

    pass


class TonCenterClient:
    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        raw_dir: Path | None = None,
        min_interval: float | None = None,
        max_retries: int = 5,
        cancel_check=None,
    ) -> None:
        self.api_key = api_key or None
        self.timeout = timeout
        self.raw_dir = raw_dir
        self.max_retries = max_retries
        self.cancel_check = cancel_check
        # Official public mode: 1 RPS. Free API key: up to 10 RPS.
        self.min_interval = min_interval if min_interval is not None else (0.12 if self.api_key else 1.05)
        self._last_request_at = 0.0
        self.session = get_session()
        self.headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key

    def close(self) -> None:
        # The application-wide session owns proxy/DNS policy and its lifecycle.
        return None

    def _throttle(self) -> None:
        if self.cancel_check and self.cancel_check():
            raise OperationCancelled("TONgue investigation cancelled")
        elapsed = time.monotonic() - self._last_request_at
        delay = self.min_interval - elapsed
        if delay > 0:
            time.sleep(delay)

    def _save_raw(self, api: str, path: str, params: Any, payload: Any) -> None:
        if not self.raw_dir:
            return
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        digest = stable_id(api, path, json.dumps(params, sort_keys=True, default=str))[:12]
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        filename = self.raw_dir / f"{stamp}_{api}_{path.strip('/').replace('/', '_')}_{digest}.json"
        envelope = {
            "fetched_at": utc_now_iso(),
            "api": api,
            "path": path,
            "params": jsonable(params),
            "payload": jsonable(payload),
        }
        filename.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    def request(self, api: str, path: str, params: Any = None) -> Any:
        base = V3_BASE if api == "v3" else V2_BASE
        url = f"{base}/{path.lstrip('/')}"
        backoff = 1.5
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout,
                )
                self._last_request_at = time.monotonic()

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else backoff
                    if attempt == self.max_retries:
                        raise TonCenterError(f"Rate limit after {attempt} attempts: {response.text[:300]}")
                    time.sleep(delay + random.random() * 0.25)
                    backoff = min(backoff * 2, 20)
                    continue

                if response.status_code >= 500:
                    raise requests.HTTPError(f"TON Center {response.status_code}: {response.text[:300]}")
                if response.status_code >= 400:
                    raise TonCenterError(f"TON Center {response.status_code}: {response.text[:500]}")

                payload = response.json()
                if api == "v2" and isinstance(payload, Mapping) and payload.get("ok") is False:
                    raise TonCenterError(str(payload.get("result") or payload))
                if isinstance(payload, Mapping) and "error" in payload and "code" in payload:
                    raise TonCenterError(str(payload))

                self._save_raw(api, path, params, payload)
                return payload
            except (requests.RequestException, ValueError, TonCenterError) as exc:
                last_error = exc
                if isinstance(exc, TonCenterError) and " 4" in str(exc) and "429" not in str(exc):
                    break
                if attempt == self.max_retries:
                    break
                time.sleep(backoff + random.random() * 0.25)
                backoff = min(backoff * 2, 20)

        raise TonCenterError(f"Request failed: {url}: {last_error}")

    def v3(self, path: str, params: Any = None) -> Any:
        return self.request("v3", path, params)

    def v2(self, path: str, params: Any = None) -> Any:
        return self.request("v2", path, params)

    def paginate(
        self,
        path: str,
        result_key: str,
        params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None,
        max_items: int,
        chunk_size: int = 100,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if max_items <= 0:
            return [], {}
        items: list[dict[str, Any]] = []
        merged_context: dict[str, Any] = {"address_book": {}, "metadata": {}}
        offset = 0

        while len(items) < max_items:
            page_limit = min(chunk_size, max_items - len(items), 1000)
            query: list[tuple[str, Any]] = []
            if params:
                if isinstance(params, Mapping):
                    for key, value in params.items():
                        if isinstance(value, (list, tuple)):
                            query.extend((key, x) for x in value)
                        elif value is not None:
                            query.append((key, value))
                else:
                    query.extend(params)
            query.extend([("limit", page_limit), ("offset", offset)])
            payload = self.v3(path, query)
            if not isinstance(payload, Mapping):
                raise TonCenterError(f"Unexpected response for {path}: {type(payload).__name__}")
            page = payload.get(result_key) or []
            if not isinstance(page, list):
                raise TonCenterError(f"Missing list '{result_key}' in {path}")
            items.extend(x for x in page if isinstance(x, dict))
            for key in ("address_book", "metadata"):
                value = payload.get(key)
                if isinstance(value, Mapping):
                    merged_context[key].update(value)
            if len(page) < page_limit:
                break
            offset += len(page)

        return items[:max_items], merged_context


# ---------------------------------------------------------------------------
# Public Telegram/Fragment collectible resolver (no Telegram session)
# ---------------------------------------------------------------------------
