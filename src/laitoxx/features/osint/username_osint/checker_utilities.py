from __future__ import annotations

import random
import re
import string
from urllib.parse import urlparse

from .models import SiteEntry


class CheckerUtilitiesMixin:
    @staticmethod
    def _make_junk_username() -> str:
        """Generate a random control username that is unlikely to exist."""
        chars = string.ascii_lowercase + string.digits
        prefix = "".join(random.choices(string.ascii_lowercase, k=4))
        suffix = "".join(random.choices(chars, k=10))
        return f"{prefix}{suffix}"

    @staticmethod
    def _compile_negative_patterns(phrases: list[str]) -> list[re.Pattern]:
        """Compile literal absence phrases into case insensitive expressions."""
        return [re.compile(re.escape(p), re.IGNORECASE) for p in phrases if p.strip()]

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize a URL for redirect comparison using only host and path."""
        parsed = urlparse(url.lower())
        netloc = parsed.netloc.replace("www.", "")
        path = parsed.path.rstrip("/")
        return f"{netloc}{path}"

    @staticmethod
    def _is_benign_redirect(initial_url: str, final_url: str, username: str) -> bool:
        """Return whether a redirect only applies a benign profile URL normalization."""
        i = urlparse(initial_url.lower())
        f = urlparse(final_url.lower())

        i_host = i.netloc.replace("www.", "")
        f_host = f.netloc.replace("www.", "")
        i_path = i.path.rstrip("/")
        f_path = f.path.rstrip("/")

        # Accept scheme, case and trailing slash normalization on the same host.
        if i_host == f_host and i_path == f_path:
            return True

        # Accept a short language subdomain when the path is unchanged.
        if f_host.endswith("." + i_host):
            prefix = f_host[: -(len(i_host) + 1)]
            if re.match(r"^[a-z]{2,5}$", prefix) and i_path == f_path:
                return True

        # Accept a language prefix when the host and profile path are unchanged.
        if i_host == f_host:
            lang_prefix_re = re.compile(r"^/[a-z]{2}(?:-[a-z]{2})?" + re.escape(i_path) + r"$")
            if lang_prefix_re.match(f_path):
                return True

        return False

    @staticmethod
    def _validate_username(site: SiteEntry, username: str) -> bool:
        if not site.regex_check:
            return True
        try:
            return bool(re.match(site.regex_check, username))
        except re.error:
            return True

    @staticmethod
    def _compute_confidence(status_code: int, body: str, username: str) -> float:
        score = 0.4
        body_lower = body.lower()
        if status_code == 200:
            score += 0.2
        if username.lower() in body_lower:
            score += 0.3
        if f"<title>{username}" in body_lower:
            score += 0.1
        return min(score, 1.0)
