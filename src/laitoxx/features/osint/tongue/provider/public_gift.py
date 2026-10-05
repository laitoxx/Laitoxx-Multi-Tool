"""Resolve public Telegram/Fragment gift pages into domain evidence."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from ..domain.gifts import (
    extract_public_profiles,
    extract_ton_address_candidates,
    extract_trait,
    normalize_gift_slug,
    normalize_name,
    parse_title_number,
    split_slug,
)
from ..domain.models import GiftIdentity
from ..domain.primitives import safe_int
from .public_web import PublicPageParser, PublicWebClient, PublicWebError


class PublicGiftResolver:
    def __init__(self, web: PublicWebClient) -> None:
        self.web = web
        self._cache: dict[str, GiftIdentity] = {}

    def resolve(self, value: str, follow_fragment: bool = True) -> GiftIdentity:
        slug = normalize_gift_slug(value)
        if slug in self._cache:
            return self._cache[slug]
        url = f"https://t.me/nft/{slug}"
        page, final_url, _ = self.web.get_text(url)
        result = self._parse_page(slug, page, final_url)
        supplied = urlparse((value or "").strip())
        supplied_host = supplied.netloc.lower().split(":", 1)[0]
        if supplied.scheme in {"http", "https"} and supplied_host in {"fragment.com", "www.fragment.com"}:
            supplied_url = supplied.geturl()
            if supplied_url not in result.fragment_links:
                result.fragment_links.insert(0, supplied_url)
                result.evidence.append("Fragment URL supplied directly")
        if follow_fragment:
            self._merge_fragment_pages(result)
        self._cache[slug] = result
        return result

    def _parse_page(self, slug: str, page: str, final_url: str) -> GiftIdentity:
        parser = PublicPageParser()
        parser.feed(page)
        body_text = " | ".join(parser.text_parts)
        script_text = " | ".join(parser.scripts[:20])
        combined = " | ".join(
            x
            for x in (
                parser.meta.get("og:title"),
                parser.meta.get("twitter:title"),
                parser.meta.get("og:description"),
                parser.meta.get("description"),
                body_text,
                script_text,
            )
            if x
        )
        title, number = parse_title_number(
            parser.meta.get("og:title"),
            parser.meta.get("twitter:title"),
            parser.meta.get("description"),
            body_text,
        )
        collection_slug, slug_number = split_slug(slug)
        if not number:
            number_match = re.search(r"(?i)Collectible\s*#\s*(\d+)", combined)
            number = safe_int(number_match.group(1)) if number_match else None
        number = number or slug_number
        if not title or normalize_name(title) in {"collectible", "telegram collectible gift"}:
            ignored = ("collectible #", "owner", "model ", "backdrop ", "symbol ", "quantity ", "this nft", "download")
            for part in parser.text_parts:
                candidate = re.sub(r"\s+", " ", part).strip()
                lower_candidate = candidate.lower()
                if 2 <= len(candidate) <= 120 and not any(lower_candidate.startswith(x) for x in ignored):
                    title = candidate
                    break
        profiles = extract_public_profiles(final_url, parser.links)
        fragment_links = []
        for href in parser.links:
            absolute = urljoin(final_url, href)
            parsed = urlparse(absolute)
            netloc = parsed.netloc.lower()
            if netloc == "fragment.com" or netloc.endswith(".fragment.com"):
                fragment_links.append(absolute)
        addresses = extract_ton_address_candidates(combined, parser.links)
        evidence = ["public t.me collectible page fetched"]
        score = 0.35
        if title and number:
            score += 0.25
            evidence.append("title and collectible number parsed")
        if profiles:
            score += 0.20
            evidence.append("public Telegram profile link found")
        if addresses:
            score += 0.15
            evidence.append("public TON address candidate found")
        model = extract_trait(combined, ("Model",))
        backdrop = extract_trait(combined, ("Backdrop", "Background"))
        symbol = extract_trait(combined, ("Symbol", "Pattern"))
        if any((model, backdrop, symbol)):
            evidence.append("collectible traits parsed")
        return GiftIdentity(
            slug=slug,
            source_url=final_url,
            title=title,
            number=number,
            collection_slug=collection_slug,
            model=model,
            backdrop=backdrop,
            symbol=symbol,
            public_profiles=profiles,
            ton_address_candidates=addresses,
            fragment_links=list(dict.fromkeys(fragment_links)),
            image_url=parser.meta.get("og:image") or parser.meta.get("twitter:image"),
            description=parser.meta.get("og:description") or parser.meta.get("description"),
            confidence=min(score, 0.90),
            evidence=evidence,
        )

    def _merge_fragment_pages(self, gift: GiftIdentity) -> None:
        for url in gift.fragment_links[:3]:
            try:
                page, final_url, _ = self.web.get_text(url)
            except PublicWebError:
                continue
            parser = PublicPageParser()
            parser.feed(page)
            combined = " | ".join(parser.text_parts + parser.scripts[:10])
            new_profiles = extract_public_profiles(final_url, parser.links)
            new_addresses = extract_ton_address_candidates(combined, parser.links)
            before_profiles = len(gift.public_profiles)
            before_addresses = len(gift.ton_address_candidates)
            gift.public_profiles = list(dict.fromkeys(gift.public_profiles + new_profiles))
            by_address = {x["address"]: x for x in gift.ton_address_candidates}
            for row in new_addresses:
                by_address.setdefault(row["address"], row)
            gift.ton_address_candidates = list(by_address.values())
            if len(gift.public_profiles) > before_profiles:
                gift.evidence.append("public profile also found on linked Fragment page")
            if len(gift.ton_address_candidates) > before_addresses:
                gift.evidence.append("TON address candidate found on linked Fragment page")
            if new_profiles or new_addresses:
                gift.confidence = min(0.95, gift.confidence + 0.05)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
