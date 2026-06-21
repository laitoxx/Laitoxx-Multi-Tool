"""Connectivity pre-flight checker, called from start.py before the GUI launches."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent.parent

CHECK_URLS = [
    ("ipapi.is", "https://api.ipapi.is"),
    ("hackertarget.com", "https://api.hackertarget.com"),
    ("duckduckgo.com", "https://duckduckgo.com"),
    ("crt.sh", "https://crt.sh"),
]


def _read_proxy_settings() -> dict:
    settings_file = _ROOT / "settings" / "app_settings.json"
    try:
        with open(settings_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("proxy", {})
    except Exception:
        return {}


def build_proxies(proxy_cfg: dict) -> dict | None:
    """Build a requests-compatible proxy dict from app proxy settings."""
    if not proxy_cfg.get("enabled"):
        return None
    ptype = proxy_cfg.get("type", "http")
    host = proxy_cfg.get("host", "")
    port = proxy_cfg.get("port", "")
    user = proxy_cfg.get("username", "")
    pwd = proxy_cfg.get("password", "")
    if not host or not port:
        return None
    auth = f"{user}:{pwd}@" if (user and pwd) else ""
    url = f"{ptype}://{auth}{host}:{port}"
    return {"http": url, "https": url}


def _ping(url: str, proxies: dict | None, timeout: int) -> bool:
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        import requests

        requests.head(url, proxies=proxies, timeout=timeout, allow_redirects=True, verify=False)
        return True
    except Exception:
        return False


def run() -> int:
    """Check connectivity to key resources. Returns number of failed resources."""
    proxy_cfg = _read_proxy_settings()
    proxies = build_proxies(proxy_cfg)

    if proxies:
        proxy_type = proxy_cfg.get("type", "http").upper()
        host = proxy_cfg.get("host", "")
        port = proxy_cfg.get("port", "")
        print(f"  Using proxy: {proxy_type} {host}:{port}")

    failed: list[str] = []
    for label, url in CHECK_URLS:
        sys.stdout.write(f"  {label:<24}")
        sys.stdout.flush()
        if _ping(url, proxies, 10):
            sys.stdout.write("OK\n")
        else:
            sys.stdout.write("timeout, retrying... ")
            sys.stdout.flush()
            if _ping(url, proxies, 30):
                sys.stdout.write("OK\n")
            else:
                sys.stdout.write("FAILED\n")
                failed.append(label)

    if len(failed) >= 2:
        print()
        print(f"  ⚠  {len(failed)}/{len(CHECK_URLS)} resources unreachable ({', '.join(failed)}).")
        print("     Your connection may be too slow, or these resources are")
        print("     blocked in your region. Consider using a proxy or VPN")
        print("     (Settings → Proxy).")
        print()

    return len(failed)


if __name__ == "__main__":
    sys.exit(0 if run() == 0 else 1)
