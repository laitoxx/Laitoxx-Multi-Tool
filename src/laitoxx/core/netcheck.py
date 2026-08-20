"""Connectivity pre-flight checker, called from start.py before the GUI launches."""

from __future__ import annotations

import sys

from laitoxx.core.settings.app_settings import settings
from laitoxx.core.settings.network_manager import build_proxies, get_session

CHECK_URLS = [
    ("ipapi.is", "https://api.ipapi.is"),
    ("hackertarget.com", "https://api.hackertarget.com"),
    ("duckduckgo.com", "https://duckduckgo.com"),
    ("crt.sh", "https://crt.sh"),
]


def _read_proxy_settings() -> dict:
    return dict(settings.proxy)


def _ping(url: str, proxies: dict | None, timeout: int) -> bool:
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        get_session().head(url, proxies=proxies, timeout=timeout, allow_redirects=True, verify=False)
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
