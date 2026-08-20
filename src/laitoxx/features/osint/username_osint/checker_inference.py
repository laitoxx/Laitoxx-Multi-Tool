from __future__ import annotations

import difflib
import re
from typing import Any

from ._patterns import (
    HARD_TITLE_404,
    JS_REDIRECT_PATTERNS,
    LOGIN_WALL_MARKERS,
    MIN_PROFILE_BODY_SIZE,
    SOFT_TITLE_BAD,
    WAF_MARKERS,
)
from .models import SiteEntry

# Type aliases
_Verdict = tuple[str, str]  # (status, reason)
_Baseline = dict[str, Any]
_Facts = dict[str, Any]


class InferenceMixin:
    def _check_waf(self, body_lower: str) -> _Verdict | None:
        for marker in WAF_MARKERS:
            if marker in body_lower:
                return "waf_blocked", f"WAF/bot-protection detected: '{marker}'"
        return None

    def _check_http_status(self, status: int, site: SiteEntry) -> _Verdict | None:
        if status not in site.valid_status:
            return "not_found", f"Invalid status code: {status}"
        return None

    def _check_server_redirects(self, facts: _Facts, username: str) -> tuple[str, _Verdict | None]:
        """Returns (final_norm, verdict_or_None)."""
        initial_url: str = facts["initial_url"]
        final_url: str = facts["final_url"]
        initial_norm = self._normalize_url(initial_url)
        final_norm = self._normalize_url(final_url)

        if facts["history"] or initial_norm != final_norm:
            if self._is_benign_redirect(initial_url, final_url, username):
                final_norm = self._normalize_url(final_url)
            else:
                return final_norm, (
                    "not_found",
                    f"Redirected away from profile URL: {final_url}",
                )
        return final_norm, None

    def _check_login_wall(self, body_lower: str) -> _Verdict | None:
        for marker in LOGIN_WALL_MARKERS:
            if marker in body_lower:
                return "login_required", f"Login wall detected: '{marker}'"
        return None

    def _check_js_redirects(self, body: str) -> _Verdict | None:
        body_head = body[:8000]
        for pattern in JS_REDIRECT_PATTERNS:
            if pattern.search(body_head):
                return "not_found", "Hidden JS/Meta redirect detected"
        return None

    def _check_title(self, body: str, username: str) -> tuple[str, _Verdict | None]:
        """Returns (title_text, verdict_or_None)."""
        title_match = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
        if not title_match:
            return "", None

        title_text = title_match.group(1).lower().strip()

        if any(p in title_text for p in HARD_TITLE_404):
            return title_text, ("not_found", f"404 in page title: '{title_text}'")

        if any(p in title_text for p in SOFT_TITLE_BAD) and username not in title_text:
            return title_text, ("not_found", f"Suspicious title: '{title_text}'")

        return title_text, None

    def _check_per_site_patterns(self, site: SiteEntry, body_lower: str) -> _Verdict | None:
        for s in site.absence_strs:
            if s.lower() in body_lower:
                return "not_found", f"Absence indicator found: '{s}'"
        for s in site.invalid_indicators:
            if s.lower() in body_lower:
                return "not_found", f"Invalid indicator found: '{s}'"
        return None

    def _check_global_patterns(self, body: str) -> _Verdict | None:
        for regex in self._compiled_negative_regex:
            if regex.search(body):
                return "not_found", f"Negative pattern match: '{regex.pattern}'"
        return None

    def _check_baseline(
        self,
        facts: _Facts,
        final_norm: str,
        body_lower: str,
        baseline: _Baseline | None,
    ) -> _Verdict | None:
        if not baseline:
            return None

        username: str = facts["username"].lower()

        # Reject a landing URL shared with the non-existent control profile.
        if final_norm == baseline["url_normalized"] and username not in final_norm:
            return "not_found", "Landing URL matches non-existent user baseline"

        # Reject content that is effectively identical to the control response.
        len_diff = abs(facts["content_length"] - baseline["length"])
        if len_diff < 50:
            ratio = difflib.SequenceMatcher(None, body_lower[:2000], baseline["body_lower"][:2000]).ratio()
            if ratio > 0.97:
                return "not_found", f"Content identical to baseline ({ratio:.2f})"

        # Small pages remain valid when they contain a strong identity marker.
        strong_identity_marker = bool(
            re.search(
                r'"(?:username|user|login|handle|screen_name)"\s*:\s*"' + re.escape(username) + r'"',
                facts["body"],
                re.IGNORECASE,
            )
            or re.search(
                r"<(?:title|h1)[^>]*>[^<]*\b" + re.escape(username) + r"\b",
                facts["body"],
                re.IGNORECASE,
            )
        )
        if facts["content_length"] < MIN_PROFILE_BODY_SIZE and not strong_identity_marker:
            if facts["content_length"] <= baseline["length"] + 200:
                return (
                    "not_found",
                    f"Page too small ({facts['content_length']} bytes), likely a stub",
                )

        return None

    def _check_positive_confirmation(
        self,
        body: str,
        body_lower: str,
        title_text: str,
        username: str,
    ) -> _Verdict:
        """Confirm an exact username using structured fields before body text."""
        uname_escaped = re.escape(username)

        # Check structured JSON identity fields first.
        json_re = re.compile(
            r'"(?:username|user|login|handle|screen_name|name)"\s*:\s*"' + uname_escaped + r'"',
            re.IGNORECASE,
        )
        if json_re.search(body):
            return "found", "Exact username in a structured identity field"

        # b) <title>
        if title_text:
            title_token_re = re.compile(r'(?:^|[\s/\'"@:·\-|])' + uname_escaped + r'(?:$|[\s/\'"@:·\-|])')
            if title_token_re.search(title_text):
                return "found", "Exact username token in the page title"

        # c) <h1>
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.IGNORECASE | re.DOTALL)
        if h1_match:
            h1_text = h1_match.group(1).lower()
            h1_token_re = re.compile(r'(?:^|[\s/\'"@:·\-|])' + uname_escaped + r'(?:$|[\s/\'"@:·\-|])')
            if h1_token_re.search(h1_text):
                return "found", "Exact username token in the main heading"

        # d) og:title / og:url
        og_match = re.search(
            r'<meta[^>]+(?:og:title|og:url)[^>]+content=["\']([^"\']+)["\']',
            body,
            re.IGNORECASE,
        )
        if og_match and username in og_match.group(1).lower():
            return "found", "Username in OpenGraph profile metadata"

        # Check link and resource attributes.
        url_attr_re = re.compile(
            r'(?:href|src)=["\'][^"\']*/' + uname_escaped + r'(?:[/"\'?]|$)',
            re.IGNORECASE,
        )
        if url_attr_re.search(body):
            return "found", "Username in a profile link or resource attribute"

        # Use a distinct body token only as the final fallback.
        body_token_re = re.compile(
            r'(?:^|[\s/\\"\'@:,<>()\[\]{}|])' + uname_escaped + r'(?:$|[\s/\\"\'@:,<>()\[\]{}|])',
            re.MULTILINE,
        )
        if body_token_re.search(body_lower):
            return "found", "Exact username token in the profile response"

        return (
            "not_found",
            f"Username '{username}' not found as a distinct token on the page",
        )
