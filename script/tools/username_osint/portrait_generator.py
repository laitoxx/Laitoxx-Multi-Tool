"""
portrait_generator.py — Digital portrait auto-generation.

Aggregates OSINT results into a structured forensic profile.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from .models import CheckResult, CATEGORY_ICONS


class DigitalPortrait:
    """
    Build a forensic digital portrait from username check results.

    Provides:
    - Category breakdown (sites found per category)
    - Online presence score (0.0 – 1.0)
    - Probable interests inferred from site tags
    - Active platforms list
    - Alt-account analysis (which nickname variants also had hits)
    """

    def __init__(
        self,
        username: str,
        results: list[CheckResult],
        alt_results: Optional[dict[str, list[CheckResult]]] = None,
    ):
        self.username = username
        self.results = results
        self.alt_results = alt_results or {}

    @property
    def found_results(self) -> list[CheckResult]:
        return [r for r in self.results if r.is_found]

    def generate(self) -> dict:
        """Return structured portrait dict."""
        found = self.found_results
        total = len(self.results)
        found_count = len(found)

        # Category breakdown
        cat_counter = Counter(r.category for r in found)

        # Tags → interests
        tag_counter: Counter = Counter()
        for r in found:
            # Extract tags from results (stored in CheckResult? No — we just
            # infer from category names since tags aren't in the result object)
            tag_counter[r.category] += 1

        # Presence score
        presence_score = found_count / max(total, 1)

        # Active platforms
        active = sorted(r.site_name for r in found)

        # Avatar URLs
        avatars = {r.site_name: r.avatar_url for r in found if r.avatar_url}

        # Alt-accounts that had hits
        alt_accounts: dict[str, int] = {}
        for nick, nick_results in self.alt_results.items():
            hits = sum(1 for r in nick_results if r.is_found)
            if hits > 0:
                alt_accounts[nick] = hits

        # Average response time
        times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
        avg_response = sum(times) / len(times) if times else 0

        # Confidence stats
        confidences = [r.confidence for r in found if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        high_conf = sum(1 for c in confidences if c >= 0.7)

        # WAF stats
        waf_blocked = sum(1 for r in self.results if r.status == "waf_blocked")

        # Retries used
        retried = sum(1 for r in self.results if r.retry_count > 0)

        return {
            "username": self.username,
            "total_checked": total,
            "total_found": found_count,
            "presence_score": round(presence_score, 3),
            "category_breakdown": dict(cat_counter.most_common()),
            "active_platforms": active,
            "probable_interests": [
                cat for cat, _ in cat_counter.most_common(5) if cat != "other"
            ],
            "avatar_urls": avatars,
            "alt_accounts": alt_accounts,
            "avg_response_ms": round(avg_response, 1),
            "errors": sum(1 for r in self.results if r.status == "error"),
            "timeouts": sum(1 for r in self.results if r.status == "timeout"),
            "avg_confidence": round(avg_confidence, 3),
            "high_confidence_count": high_conf,
            "waf_blocked": waf_blocked,
            "retried_sites": retried,
        }

    def to_text(self) -> str:
        """Pretty-print the portrait as formatted text."""
        p = self.generate()

        lines = []
        lines.append("=" * 60)
        lines.append(f"  DIGITAL PORTRAIT: @{p['username']}")
        lines.append("=" * 60)
        lines.append("")

        # Stats
        lines.append(f"  Online Presence Score: {p['presence_score']:.1%}")
        lines.append(f"  Found: {p['total_found']} / {p['total_checked']} sites")
        lines.append(f"  Avg Confidence: {p['avg_confidence']:.0%}  "
                      f"(High: {p['high_confidence_count']})")
        lines.append(f"  Avg Response: {p['avg_response_ms']:.0f}ms")
        status_parts = []
        if p["errors"]:
            status_parts.append(f"Errors: {p['errors']}")
        if p["timeouts"]:
            status_parts.append(f"Timeouts: {p['timeouts']}")
        if p["waf_blocked"]:
            status_parts.append(f"WAF Blocked: {p['waf_blocked']}")
        if p["retried_sites"]:
            status_parts.append(f"Retried: {p['retried_sites']}")
        if status_parts:
            lines.append(f"  {' | '.join(status_parts)}")
        lines.append("")

        # Category breakdown
        lines.append("  --- Category Breakdown ---")
        for cat, count in p["category_breakdown"].items():
            icon = CATEGORY_ICONS.get(cat, "")
            lines.append(f"    {icon} {cat.capitalize():<20} {count} sites")
        lines.append("")

        # Interests
        if p["probable_interests"]:
            interests_str = ", ".join(
                CATEGORY_ICONS.get(i, "") + " " + i.capitalize()
                for i in p["probable_interests"]
            )
            lines.append(f"  Probable Interests: {interests_str}")
            lines.append("")

        # Active platforms
        lines.append(f"  --- Active Platforms ({len(p['active_platforms'])}) ---")
        for i, platform in enumerate(p["active_platforms"], 1):
            lines.append(f"    {i:>3}. {platform}")
        lines.append("")

        # Avatars
        if p["avatar_urls"]:
            lines.append(f"  --- Avatars ({len(p['avatar_urls'])}) ---")
            for site, url in list(p["avatar_urls"].items())[:10]:
                lines.append(f"    {site}: {url}")
            lines.append("")

        # Alt-accounts
        if p["alt_accounts"]:
            lines.append("  --- Possible Alt-Accounts ---")
            for nick, hits in sorted(p["alt_accounts"].items(), key=lambda x: -x[1]):
                lines.append(f"    @{nick} — {hits} hits")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
