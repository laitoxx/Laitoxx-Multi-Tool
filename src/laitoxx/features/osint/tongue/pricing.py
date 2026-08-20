"""Optional fiat valuation for parsed TON movements."""

from __future__ import annotations

import os
from bisect import bisect_left
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import requests

from laitoxx.core.settings.network_manager import get_session


def _enrich_movement_prices(report: dict[str, Any]) -> None:
    """Attach approximate historical TON/USD values using one bounded request."""
    movements = [row for row in report.get("movements") or [] if isinstance(row, dict)]
    dated: list[tuple[dict[str, Any], int]] = []
    for row in movements:
        try:
            timestamp = int(datetime.fromisoformat(str(row.get("created_at"))).timestamp())
        except (TypeError, ValueError):
            continue
        dated.append((row, timestamp))
    if not dated:
        return
    headers = {"Accept": "application/json", "User-Agent": "Laitoxx-TONgue/1.0"}
    demo_key = os.getenv("COINGECKO_DEMO_API_KEY", "").strip()
    if demo_key:
        headers["x-cg-demo-api-key"] = demo_key
    moments = sorted({timestamp for _row, timestamp in dated})
    windows: list[list[int]] = []
    for timestamp in moments:
        if not windows or timestamp - windows[-1][-1] > 7 * 86_400:
            windows.append([timestamp])
        else:
            windows[-1].append(timestamp)
    samples: list[tuple[int, float]] = []
    for window in windows[:4]:
        try:
            response = get_session().get(
                "https://api.coingecko.com/api/v3/coins/the-open-network/market_chart/range",
                params={
                    "vs_currency": "usd",
                    "from": window[0] - 43_200,
                    "to": window[-1] + 43_200,
                },
                headers=headers,
                timeout=25,
            )
            if response.status_code >= 400:
                continue
            payload = response.json()
        except (requests.RequestException, ValueError):
            continue
        if not isinstance(payload, Mapping):
            continue
        samples.extend(
            (int(float(sample[0]) / 1000), float(sample[1]))
            for sample in payload.get("prices") or []
            if isinstance(sample, list) and len(sample) >= 2
        )
    samples.sort()
    if not samples:
        return
    timestamps = [sample[0] for sample in samples]
    for row, timestamp in dated:
        index = bisect_left(timestamps, timestamp)
        candidates = samples[max(0, index - 1) : min(len(samples), index + 1)]
        if not candidates:
            continue
        sampled_at, rate = min(candidates, key=lambda sample: abs(sample[0] - timestamp))
        # Do not present a distant quote as the price at transaction time.
        if abs(sampled_at - timestamp) > 172_800:
            continue
        amount = float(row.get("amount_ton") or row.get("price_ton") or 0)
        row["ton_usd_rate"] = round(rate, 6)
        row["amount_usd"] = round(amount * rate, 2)
        row["price_source"] = "CoinGecko historical TON/USD"
    priced = [row for row in movements if row.get("amount_usd") is not None]
    usd_by_pair: dict[tuple[str, str], float] = {}
    for row in priced:
        pair = (str(row.get("source") or ""), str(row.get("destination") or ""))
        usd_by_pair[pair] = usd_by_pair.get(pair, 0.0) + float(row.get("amount_usd") or 0)
    for edge in (report.get("graph") or {}).get("edges") or []:
        if not isinstance(edge, dict):
            continue
        pair = (
            str(edge.get("source") or edge.get("source_id") or ""),
            str(edge.get("target") or edge.get("target_id") or ""),
        )
        if pair in usd_by_pair:
            edge.setdefault("details", {})["estimated_usd"] = round(usd_by_pair[pair], 2)
            edge["details"]["price_source"] = "CoinGecko historical TON/USD"
    report.setdefault("summary", {}).update(
        {
            "incoming_ton": round(
                sum(float(row.get("amount_ton") or 0) for row in movements if row.get("direction") == "in"), 6
            ),
            "outgoing_ton": round(
                sum(float(row.get("amount_ton") or 0) for row in movements if row.get("direction") == "out"), 6
            ),
            "incoming_usd_estimate": round(
                sum(float(row.get("amount_usd") or 0) for row in priced if row.get("direction") == "in"), 2
            ),
            "outgoing_usd_estimate": round(
                sum(float(row.get("amount_usd") or 0) for row in priced if row.get("direction") == "out"), 2
            ),
            "priced_movements": len(priced),
            "price_source": "CoinGecko historical TON/USD" if priced else None,
        }
    )
