"""URL normalization and crawl scope policy."""

from __future__ import annotations

import posixpath
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

_TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def normalize_url(value: str, base_url: str = "", query_policy: str = "sort") -> str:
    """Return a canonical HTTP URL or an empty string for unsupported input."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    if base_url:
        raw = urljoin(base_url, raw)
    elif "://" not in raw:
        raw = "https://" + raw
    parsed = urlsplit(raw)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or parsed.username or parsed.password:
        return ""
    host = (parsed.hostname or "").rstrip(".").casefold()
    if not host:
        return ""
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return ""
    port = parsed.port
    netloc = host
    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    path = parsed.path or "/"
    had_trailing_slash = path.endswith("/")
    path = posixpath.normpath(path)
    if not path.startswith("/"):
        path = "/" + path
    if had_trailing_slash and path != "/":
        path += "/"
    path = quote(path, safe="/%:@!$&'()*+,;=-._~")
    query = parsed.query
    if query_policy == "drop":
        query = ""
    elif query_policy == "sort":
        pairs = [
            (key, val) for key, val in parse_qsl(query, keep_blank_values=True) if key.casefold() not in _TRACKING_KEYS
        ]
        query = urlencode(sorted(pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


class CrawlScope:
    """Decide whether a normalized URL belongs to the selected crawl scope."""

    def __init__(self, seed_url: str, mode: str = "host") -> None:
        self.seed_url = normalize_url(seed_url)
        self.seed_host = (urlsplit(self.seed_url).hostname or "").casefold()
        self.mode = mode

    def contains(self, url: str) -> bool:
        host = (urlsplit(url).hostname or "").casefold()
        if self.mode == "subdomains":
            return host == self.seed_host or host.endswith("." + self.seed_host)
        return host == self.seed_host
