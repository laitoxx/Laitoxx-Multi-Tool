"""High confidence public API probes for selected username providers."""

from __future__ import annotations

from .models import SiteEntry

_PUBLIC_API_PROBES = {
    "github": "https://api.github.com/users/{username}",
    "gitlab": "https://gitlab.com/api/v4/users?username={username}",
    "reddit": "https://www.reddit.com/user/{username}/about.json",
}


def apply_public_api_adapter(site: SiteEntry) -> SiteEntry:
    """Apply a stable public API probe to an exact provider definition."""

    probe = _PUBLIC_API_PROBES.get(site.name.casefold())
    if probe is None:
        return site
    site.url_probe = probe
    site.engine = "public_api"
    site.headers = {
        **site.headers,
        "Accept": "application/json",
    }
    return site
