"""Validation and serialization of centralized proxy settings."""

from urllib.parse import quote


def build_proxy_url(cfg: dict) -> str:
    if not cfg or not cfg.get("enabled"):
        return ""
    host = str(cfg.get("host", "")).strip()
    port = str(cfg.get("port", "")).strip()
    if not host or not port:
        return ""
    scheme = str(cfg.get("type", "http")).lower()
    if scheme == "socks5":
        scheme = "socks5h"
    username = str(cfg.get("username", ""))
    password = str(cfg.get("password", ""))
    credentials = f"{quote(username, safe='')}:{quote(password, safe='')}@" if username or password else ""
    return f"{scheme}://{credentials}{host}:{port}"


def build_proxies(cfg: dict) -> dict | None:
    url = build_proxy_url(cfg)
    return {"http": url, "https": url} if url else None


def load_settings_proxy() -> dict | None:
    try:
        from .app_settings import settings

        return settings.proxy
    except Exception:
        return None
