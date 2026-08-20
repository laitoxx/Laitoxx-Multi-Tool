"""Gift slug, public profile and TON address normalization."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from .primitives import safe_int

GIFT_SLUG_RE = re.compile(r"(?i)(?:https?://t\.me/nft/|tg://nft\?slug=)?([a-z0-9][a-z0-9_-]*-\d+)")
TON_RAW_RE = re.compile(r"(?<![0-9A-Fa-f])(-?\d+:[0-9A-Fa-f]{64})(?![0-9A-Fa-f])")
TON_FRIENDLY_RE = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{48})(?![A-Za-z0-9_-])")
PUBLIC_PROFILE_EXCLUDES = {
    "nft",
    "share",
    "joinchat",
    "addstickers",
    "addemoji",
    "proxy",
    "socks",
    "login",
    "iv",
    "blog",
    "apps",
    "faq",
    "privacy",
    "terms",
    "telegram",
}


def normalize_gift_slug(value: str) -> str:
    raw = unquote((value or "").strip())
    if not raw:
        raise ValueError("Gift slug/link is empty")
    parsed = urlparse(raw)
    if parsed.scheme == "tg" and parsed.netloc.lower() == "nft":
        slug = (parse_qs(parsed.query).get("slug") or [""])[0]
        if slug:
            return slug.lower()
    match = GIFT_SLUG_RE.search(raw)
    if match:
        return match.group(1).lower()
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*-\d+", raw):
        return raw.lower()
    raise ValueError(f"Cannot extract collectible gift slug from: {value}")


def split_slug(slug: str) -> tuple[str, int | None]:
    match = re.fullmatch(r"(.+)-(\d+)", slug)
    if not match:
        return slug, None
    return match.group(1), safe_int(match.group(2), 0) or None


def normalize_name(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def parse_title_number(*values: Any) -> tuple[str | None, int | None]:
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            continue
        match = re.search(r"(?P<title>[^|·\n]{2,120}?)\s*#\s*(?P<num>\d{1,12})", text)
        if match:
            title = re.sub(r"^[\s|·-]+|[\s|·-]+$", "", re.sub(r"\s+", " ", match.group("title")))
            return title or None, safe_int(match.group("num")) or None
    return None, None


def extract_trait(text: str, names: Sequence[str]) -> str | None:
    for name in names:
        pattern = rf"(?i)(?:^|[|·;\n])\s*{re.escape(name)}\s*(?::|\-)?\s*([^|·;\n]{{1,100}})"
        match = re.search(pattern, text)
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            value = re.sub(r"\s+\d+(?:[.,]\d+)?%\s*$", "", value).strip()
            return value or None
    return None


def extract_public_profiles(base_url: str, links: Iterable[str]) -> list[str]:
    profiles: list[str] = []
    for href in links:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        host = parsed.netloc.lower().split(":", 1)[0]
        username = ""
        if host in {"t.me", "telegram.me", "www.t.me", "www.telegram.me"}:
            parts = [p for p in parsed.path.split("/") if p]
            if parts:
                username = parts[0]
        elif parsed.scheme == "tg" and parsed.netloc.lower() == "resolve":
            username = (parse_qs(parsed.query).get("domain") or [""])[0]
        username = username.strip("@")
        if (
            username
            and username.lower() not in PUBLIC_PROFILE_EXCLUDES
            and re.fullmatch(r"[A-Za-z0-9_]{4,32}", username)
        ):
            profiles.append("@" + username)
    return list(dict.fromkeys(profiles))


def extract_ton_address_candidates(text: str, links: Iterable[str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    haystacks: list[tuple[str, str]] = [("page_text", text)]
    for href in links:
        haystacks.append(("link", unquote(href)))
    seen: set[str] = set()
    for source, haystack in haystacks:
        for regex in (TON_RAW_RE, TON_FRIENDLY_RE):
            for match in regex.finditer(haystack):
                address = match.group(1)
                if address in seen:
                    continue
                # Friendly addresses have a CRC; false positives are later rejected by detectAddress.
                if ":" not in address and not address.startswith(("E", "U", "k", "0")):
                    continue
                seen.add(address)
                role = "unknown"
                lower = haystack.lower()
                around = lower[max(0, match.start() - 80) : match.end() + 80]
                if any(token in around for token in ("gift_address", "nft_address", "/nft/", "nft=")):
                    role = "nft_candidate"
                elif any(token in around for token in ("owner_address", "/address/", "owner=")):
                    role = "owner_candidate"
                candidates.append({"address": address, "role": role, "source": source})
    return candidates
