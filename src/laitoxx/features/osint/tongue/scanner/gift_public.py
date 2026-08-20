"""Public gift and profile resolution behavior."""

from __future__ import annotations

from typing import Any

from ..domain.gifts import normalize_gift_slug, split_slug
from ..domain.models import GiftIdentity
from ..provider.public_web import PublicPageParser, PublicWebError


class GiftPublicMixin:
    def resolve_gift(self, value: str, public_profiles: bool = True) -> GiftIdentity:
        """Resolve and cache the public Gift identity for enrichment stages."""
        return self._resolve_gift(value, public_profiles=public_profiles)

    def _resolve_gift(self, value: str, public_profiles: bool = True) -> GiftIdentity:
        slug = normalize_gift_slug(value)
        if slug in self._gift_cache:
            return self._gift_cache[slug]
        if public_profiles and self.resolver:
            try:
                gift = self.resolver.resolve(slug)
            except PublicWebError as exc:
                collection_slug, number = split_slug(slug)
                gift = GiftIdentity(
                    slug=slug,
                    source_url=f"https://t.me/nft/{slug}",
                    number=number,
                    collection_slug=collection_slug,
                    confidence=0.20,
                    evidence=[f"public page unavailable: {exc}"],
                )
        else:
            collection_slug, number = split_slug(slug)
            gift = GiftIdentity(
                slug=slug,
                source_url=f"https://t.me/nft/{slug}",
                number=number,
                collection_slug=collection_slug,
                confidence=0.20,
                evidence=["slug supplied without public page resolution"],
            )
        self._gift_cache[slug] = gift
        self.db.save_gift(gift)
        for profile in gift.public_profiles:
            self.db.save_gift_resolution(
                gift.slug,
                "PUBLICLY_DISPLAYED_BY",
                0.75,
                "t.me/fragment public page",
                gift.evidence,
                telegram_profile=profile,
            )
        return gift

    def _wallet_nfts(self, address: str, max_items: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        key = f"{address}:{max_items}"
        if key in self._wallet_cache:
            return self._wallet_cache[key]
        old_limit = self.scanner.nft_limit
        try:
            self.scanner.nft_limit = max_items
            result = self.scanner.get_nfts(address)
        finally:
            self.scanner.nft_limit = old_limit
        self._wallet_cache[key] = result
        return result

    def _verify_public_username(self, username: str) -> tuple[bool, list[str]]:
        if not self.resolver or not username:
            return False, []
        url = f"https://t.me/{username.lstrip('@')}"
        try:
            page, final_url, status = self.resolver.web.get_text(url)
        except PublicWebError:
            return False, []
        parser = PublicPageParser()
        parser.feed(page)
        public_text = " ".join(
            str(value or "")
            for value in (
                parser.meta.get("og:title"),
                parser.meta.get("og:description"),
                parser.meta.get("description"),
                " ".join(parser.text_parts[:30]),
            )
        ).casefold()
        needle = username.lstrip("@").casefold()
        unavailable = any(
            marker in public_text for marker in ("username not found", "page not found", "account unavailable")
        )
        if status == 200 and needle in public_text and not unavailable:
            return True, [
                f"public Telegram page resolves to @{username.lstrip('@')}",
                f"public source: {final_url}",
            ]
        return False, []
