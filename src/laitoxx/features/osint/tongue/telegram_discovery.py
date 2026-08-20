"""Public Telegram discovery feeding identities into TONgue."""

from __future__ import annotations

import queue
import re
import threading
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from .domain.gifts import extract_ton_address_candidates
from .provider.public_web import PublicPageParser, PublicWebClient, PublicWebError

CancelCheck = Callable[[], bool]
EXPLICIT_GIFT_RE = re.compile(r"(?i)(?:https?://t\.me/nft/|tg://nft\?slug=)([a-z0-9][a-z0-9_-]*-\d+)")


def normalize_telegram_target(value: str) -> tuple[str, str]:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Enter a Telegram username, link, channel, chat or numeric ID")
    if raw.isdigit():
        return raw, "id"
    if "://" not in raw and raw.casefold().startswith(("t.me/", "telegram.me/")):
        raw = "https://" + raw
    if "://" in raw:
        parsed = urlparse(raw)
        if parsed.netloc.casefold() not in {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}:
            raise ValueError("Only public t.me or telegram.me links are supported")
        parts = [part for part in parsed.path.split("/") if part]
        if not parts or parts[0].casefold() in {"nft", "joinchat", "+"}:
            raise ValueError("Enter a public Telegram profile or channel link")
        raw = parts[1] if parts[0] == "s" and len(parts) > 1 else parts[0]
    username = raw.strip().lstrip("@").split("/", 1)[0]
    if not re.fullmatch(r"[A-Za-z0-9_]{4,32}", username):
        raise ValueError("Telegram username must contain 4-32 letters, digits or underscores")
    return username, "username"


def _paketlib_lookup(username: str) -> tuple[dict[str, Any], str | None]:
    output: queue.Queue[tuple[dict[str, Any], str | None]] = queue.Queue(maxsize=1)

    def lookup() -> None:
        try:
            import paketlib

            result = paketlib.search.Telegram().TelegramUsername(username)
            if isinstance(result, dict):
                data = {str(key): value for key, value in result.items() if value not in (None, "", [], {})}
            elif isinstance(result, list):
                data = {"results": result[:100]}
            else:
                data = {"result": result} if result else {}
            output.put_nowait((data, None))
        except Exception as error:
            output.put_nowait(({}, str(error)))

    threading.Thread(target=lookup, name="tongue-paketlib", daemon=True).start()
    try:
        return output.get(timeout=12)
    except queue.Empty:
        return {}, "Lookup timed out after 12 seconds"


def discover_telegram(
    value: str,
    *,
    web: PublicWebClient | None = None,
    cancelled: CancelCheck | None = None,
) -> dict[str, Any]:
    """Collect bounded public profile metadata and extract TON pivots."""
    target, kind = normalize_telegram_target(value)
    if cancelled and cancelled():
        raise RuntimeError("Telegram discovery cancelled")
    if kind == "id":
        return {
            "query": value,
            "target": target,
            "kind": kind,
            "status": "needs_api",
            "message": "A numeric Telegram ID cannot be resolved from public web pages without an authenticated Telegram API session.",
            "profile": {"id": target},
            "gift_candidates": [],
            "ton_candidates": [],
            "sources": [],
        }

    owns_web = web is None
    client = web or PublicWebClient(cancel_check=cancelled)
    sources: list[dict[str, Any]] = []
    page_text = ""
    links: list[str] = []
    profile: dict[str, Any] = {"username": "@" + target, "url": f"https://t.me/{target}"}
    try:
        try:
            html, final_url, status = client.get_text(f"https://t.me/{target}")
            parser = PublicPageParser()
            parser.feed(html)
            page_text = "\n".join(parser.text_parts)
            links = parser.links
            profile.update(
                {
                    "title": parser.meta.get("og:title") or parser.meta.get("twitter:title") or target,
                    "description": parser.meta.get("og:description") or parser.meta.get("description") or "",
                    "image": parser.meta.get("og:image") or "",
                    "canonical": parser.meta.get("canonical") or final_url,
                }
            )
            sources.append(
                {"name": "Telegram public page", "status": "fetched", "url": final_url, "http_status": status}
            )
        except PublicWebError as error:
            sources.append({"name": "Telegram public page", "status": "error", "message": str(error)})

        paket_data, paket_error = _paketlib_lookup(target)
        if paket_data:
            profile["paketlib"] = paket_data
            sources.append({"name": "paketlib Telegram lookup", "status": "fetched"})
        elif paket_error:
            sources.append({"name": "paketlib Telegram lookup", "status": "unavailable", "message": paket_error})

        combined = "\n".join((page_text, str(profile), *links))
        gifts = list(dict.fromkeys(match.group(1).lower() for match in EXPLICIT_GIFT_RE.finditer(combined)))
        addresses = extract_ton_address_candidates(combined, links)
        return {
            "query": value,
            "target": target,
            "kind": kind,
            "status": "found" if profile.get("title") or paket_data else "limited",
            "message": "Public Telegram discovery completed",
            "profile": profile,
            "gift_candidates": gifts[:100],
            "ton_candidates": addresses[:100],
            "sources": sources,
        }
    finally:
        if owns_web:
            client.close()


def discovery_report(discovery: dict[str, Any]) -> dict[str, Any]:
    username = str((discovery.get("profile") or {}).get("username") or discovery.get("target") or "")
    root_id = f"telegram:{username.lstrip('@').casefold()}"
    nodes = [
        {
            "id": root_id,
            "type": "telegram_profile",
            "label": username or "Telegram target",
            "confidence": 1.0,
            "details": discovery.get("profile") or {},
            "evidence": discovery.get("sources") or [],
        }
    ]
    edges = []
    for slug in discovery.get("gift_candidates") or []:
        node_id = f"gift:{slug}"
        nodes.append({"id": node_id, "type": "telegram_gift", "label": slug, "confidence": 0.8})
        edges.append({"source": root_id, "target": node_id, "relation": "PUBLIC_PAGE_REFERENCES", "confidence": 0.8})
    for item in discovery.get("ton_candidates") or []:
        address = str(item.get("address") or "")
        if not address:
            continue
        node_id = f"ton:{address}"
        nodes.append({"id": node_id, "type": "wallet", "label": address, "confidence": 0.65, "details": item})
        edges.append({"source": root_id, "target": node_id, "relation": "PUBLIC_PAGE_REFERENCES", "confidence": 0.65})
    return {
        "summary": {
            "title": str((discovery.get("profile") or {}).get("title") or username or "Telegram discovery"),
            "seed": username,
            "target_type": "telegram",
            "telegram_status": discovery.get("status"),
            "gift_candidates": len(discovery.get("gift_candidates") or []),
            "ton_candidates": len(discovery.get("ton_candidates") or []),
            "next_step": "Select a discovered Gift or TON entity for blockchain investigation"
            if nodes[1:]
            else "No public TON pivots were exposed by this Telegram page",
        },
        "telegram_discovery": discovery,
        "graph": {"nodes": nodes, "edges": edges},
        "history": [],
        "movements": [],
        "tongue": {"target_kind": "telegram", "public_only": True, "recursive": False},
    }
