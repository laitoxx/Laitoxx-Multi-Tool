"""Proxy configuration helpers.

Stores proxy settings in the central app_settings.json (via AppSettings).
Provides a helper to build a requests-compatible proxies dict and to
create a configured requests.Session.
"""
from __future__ import annotations

import os
import requests


def build_proxies(proxy_type: str, host: str, port: int | str,
                  username: str = "", password: str = "") -> dict:
    """Return a ``requests``-compatible proxies dict, or {} if disabled."""
    if not host or not port:
        return {}
    creds = f"{username}:{password}@" if (username or password) else ""
    scheme = proxy_type.lower()  # "http", "https", or "socks5"
    if scheme == "socks5":
        scheme = "socks5h"
    url = f"{scheme}://{creds}{host}:{port}"
    return {"http": url, "https": url}


def make_session(proxy_cfg: dict | None = None) -> requests.Session:
    """Create a requests.Session with the given proxy config applied.

    ``proxy_cfg`` is the dict stored inside AppSettings.proxy, e.g.::

        {
            "enabled": True,
            "type": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": "",
            "password": "",
        }
    """
    if proxy_cfg is None:
        try:
            from .app_settings import settings
            proxy_cfg = settings.proxy
        except Exception:
            proxy_cfg = None

    session = requests.Session()
    if proxy_cfg and proxy_cfg.get("enabled"):
        proxies = build_proxies(
            proxy_cfg.get("type", "http"),
            proxy_cfg.get("host", ""),
            proxy_cfg.get("port", ""),
            proxy_cfg.get("username", ""),
            proxy_cfg.get("password", ""),
        )
        if proxies:
            session.proxies.update(proxies)
    return session


# Module-level shared session — replaced when settings change.
_shared_session: requests.Session = requests.Session()


def get_session() -> requests.Session:
    """Return the current module-level shared session."""
    return _shared_session


def apply_proxy_settings(proxy_cfg: dict | None):
    """Rebuild the shared session and env from updated proxy config."""
    global _shared_session
    _shared_session = make_session(proxy_cfg)
    _apply_proxy_env(proxy_cfg)


def _apply_proxy_env(proxy_cfg: dict | None):
    keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy")
    if proxy_cfg and proxy_cfg.get("enabled"):
        url = build_proxies(
            proxy_cfg.get("type", "http"),
            proxy_cfg.get("host", ""),
            proxy_cfg.get("port", ""),
            proxy_cfg.get("username", ""),
            proxy_cfg.get("password", ""),
        ).get("http", "")
        if url:
            for k in keys:
                os.environ[k] = url
            return
    for k in keys:
        os.environ.pop(k, None)
