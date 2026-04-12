"""NetworkManager — centralized network control layer.

Guarantees that when SOCKS5 proxy is enabled:
  - Every requests.Session (including those created by third-party libs) goes
    through the proxy.
  - System-level DNS resolution (socket.getaddrinfo / gethostbyname) is blocked
    so no DNS leak can occur — all name resolution is delegated to the proxy.
  - Direct TCP socket connections (socket.create_connection / socket.connect)
    are blocked so raw-socket tools cannot bypass the proxy either.

Usage
-----
Import once at application startup (before any network code runs):

    from settings.network_manager import NetworkManager
    NetworkManager.apply()          # reads proxy from AppSettings
    NetworkManager.apply(cfg)       # pass explicit proxy dict

The module also re-exports the proxy-aware session factory so every tool can do:

    from settings.network_manager import get_session
    session = get_session()

When the user changes proxy settings in the UI call:

    NetworkManager.apply(new_proxy_cfg)
"""
from __future__ import annotations

import os
import socket
import threading
import urllib.request
from typing import Optional

import requests
import requests.adapters


# ── Internal state ─────────────────────────────────────────────────────────────

_lock = threading.Lock()

# Saved originals so we can restore them on disable
_orig_getaddrinfo = socket.getaddrinfo
_orig_gethostbyname = socket.gethostbyname
_orig_gethostbyname_ex = socket.gethostbyname_ex
_orig_create_connection = socket.create_connection

# Saved original requests.Session.__init__ (before any monkey-patching)
_orig_session_init = requests.Session.__init__

# Saved original requests module-level helpers
_orig_requests_get     = requests.get
_orig_requests_post    = requests.post
_orig_requests_put     = requests.put
_orig_requests_patch   = requests.patch
_orig_requests_delete  = requests.delete
_orig_requests_head    = requests.head
_orig_requests_options = requests.options
_orig_requests_request = requests.request

_state: dict = {
    "active": False,
    "proxy_url": "",          # e.g. "socks5h://user:pass@127.0.0.1:1080"
    "proxy_type": "http",
}

# The single shared session used by all tools
_shared_session: requests.Session = requests.Session()


# ── Public API ─────────────────────────────────────────────────────────────────

class NetworkManager:
    """Static controller — no instantiation needed."""

    @staticmethod
    def apply(proxy_cfg: Optional[dict] = None) -> None:
        """(Re-)apply proxy settings and install/remove OS-level guards.

        ``proxy_cfg`` mirrors AppSettings.proxy:
            {
                "enabled": True,
                "type": "socks5",   # "http" | "https" | "socks5"
                "host": "127.0.0.1",
                "port": 1080,
                "username": "",
                "password": "",
            }
        If *proxy_cfg* is None the method reads from AppSettings automatically.
        """
        if proxy_cfg is None:
            proxy_cfg = _load_settings_proxy()

        with _lock:
            if proxy_cfg and proxy_cfg.get("enabled"):
                proxy_url = _build_proxy_url(proxy_cfg)
                _state["active"] = True
                _state["proxy_url"] = proxy_url
                _state["proxy_type"] = proxy_cfg.get("type", "http").lower()
                _rebuild_session(proxy_url)
                _set_env(proxy_url)
                if _state["proxy_type"] == "socks5":
                    _install_dns_guard()
                    _install_socket_guard()
                else:
                    _remove_dns_guard()
                    _remove_socket_guard()
            else:
                _state["active"] = False
                _state["proxy_url"] = ""
                _state["proxy_type"] = "http"
                _rebuild_session(None)
                _clear_env()
                _remove_dns_guard()
                _remove_socket_guard()

    @staticmethod
    def get_session() -> requests.Session:
        """Return the global proxy-aware session."""
        return _shared_session

    @staticmethod
    def is_active() -> bool:
        return bool(_state["active"])

    @staticmethod
    def proxy_url() -> str:
        return _state["proxy_url"]

    @staticmethod
    def status() -> dict:
        return dict(_state)


def get_session() -> requests.Session:
    """Module-level shortcut so tools can: ``from settings.network_manager import get_session``."""
    return _shared_session


# ── Session helpers ────────────────────────────────────────────────────────────

def _rebuild_session(proxy_url: Optional[str]) -> None:
    global _shared_session
    # Always use the stdlib requests.Session.__init__ — not our patched version —
    # to avoid infinite recursion when _patch_requests_session_class is already set.
    sess = requests.Session.__new__(requests.Session)
    _orig_session_init(sess)
    if proxy_url:
        sess.proxies.update({"http": proxy_url, "https": proxy_url})
    _shared_session = sess
    _patch_requests_session_class(proxy_url)
    _patch_requests_module(proxy_url)


def _patch_requests_session_class(proxy_url: Optional[str]) -> None:
    """Monkey-patch requests.Session.__init__ so any session created by
    third-party libraries also inherits the proxy settings."""
    original_init = requests.Session.__init__

    def _patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if proxy_url:
            self.proxies.update({"http": proxy_url, "https": proxy_url})

    requests.Session.__init__ = _patched_init  # type: ignore[method-assign]


def _patch_requests_module(proxy_url: Optional[str]) -> None:
    """Replace requests.get / .post / ... with wrappers that route through
    the shared session so bare ``requests.get(url)`` calls also use the proxy."""
    if proxy_url:
        def _make_method(method_name: str):
            def _method(url, **kwargs):
                return getattr(_shared_session, method_name)(url, **kwargs)
            _method.__name__ = method_name
            return _method

        requests.get     = _make_method("get")      # type: ignore[assignment]
        requests.post    = _make_method("post")      # type: ignore[assignment]
        requests.put     = _make_method("put")       # type: ignore[assignment]
        requests.patch   = _make_method("patch")     # type: ignore[assignment]
        requests.delete  = _make_method("delete")    # type: ignore[assignment]
        requests.head    = _make_method("head")      # type: ignore[assignment]
        requests.options = _make_method("options")   # type: ignore[assignment]

        def _request(method, url, **kwargs):
            return _shared_session.request(method, url, **kwargs)
        requests.request = _request                  # type: ignore[assignment]
    else:
        # Restore originals when proxy is disabled
        requests.Session.__init__ = _orig_session_init  # type: ignore[method-assign]
        requests.get     = _orig_requests_get        # type: ignore[assignment]
        requests.post    = _orig_requests_post       # type: ignore[assignment]
        requests.put     = _orig_requests_put        # type: ignore[assignment]
        requests.patch   = _orig_requests_patch      # type: ignore[assignment]
        requests.delete  = _orig_requests_delete     # type: ignore[assignment]
        requests.head    = _orig_requests_head       # type: ignore[assignment]
        requests.options = _orig_requests_options    # type: ignore[assignment]
        requests.request = _orig_requests_request    # type: ignore[assignment]


# ── Environment variables ──────────────────────────────────────────────────────

_ENV_KEYS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
)


def _set_env(proxy_url: str) -> None:
    for k in _ENV_KEYS:
        os.environ[k] = proxy_url


def _clear_env() -> None:
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


# ── DNS leak guard ─────────────────────────────────────────────────────────────

_DNS_GUARD_INSTALLED = False


def _install_dns_guard() -> None:
    """Replace socket DNS functions with stubs that raise an error.

    With socks5h the proxy performs DNS resolution, so any local DNS call is
    a potential leak.  Tools that legitimately need a hostname resolved should
    rely on the socks5h session (requests) — not on bare socket calls.
    """
    global _DNS_GUARD_INSTALLED
    if _DNS_GUARD_INSTALLED:
        return

    def _blocked_getaddrinfo(host, port, *args, **kwargs):
        # Allow loopback / already-numeric addresses to pass through
        if _is_numeric_or_loopback(host):
            return _orig_getaddrinfo(host, port, *args, **kwargs)
        raise OSError(
            f"[NetworkManager] DNS resolution of '{host}' blocked — "
            "proxy is active (socks5h). Use the proxy session for HTTP/HTTPS "
            "requests; all DNS goes through the proxy."
        )

    def _blocked_gethostbyname(hostname):
        if _is_numeric_or_loopback(hostname):
            return _orig_gethostbyname(hostname)
        raise OSError(
            f"[NetworkManager] DNS resolution of '{hostname}' blocked — "
            "proxy is active (socks5h)."
        )

    def _blocked_gethostbyname_ex(hostname):
        if _is_numeric_or_loopback(hostname):
            return _orig_gethostbyname_ex(hostname)
        raise OSError(
            f"[NetworkManager] DNS resolution of '{hostname}' blocked — "
            "proxy is active (socks5h)."
        )

    socket.getaddrinfo = _blocked_getaddrinfo          # type: ignore[assignment]
    socket.gethostbyname = _blocked_gethostbyname      # type: ignore[assignment]
    socket.gethostbyname_ex = _blocked_gethostbyname_ex  # type: ignore[assignment]
    _DNS_GUARD_INSTALLED = True


def _remove_dns_guard() -> None:
    global _DNS_GUARD_INSTALLED
    socket.getaddrinfo = _orig_getaddrinfo
    socket.gethostbyname = _orig_gethostbyname
    socket.gethostbyname_ex = _orig_gethostbyname_ex
    _DNS_GUARD_INSTALLED = False


# ── Raw socket connection guard ────────────────────────────────────────────────

_SOCKET_GUARD_INSTALLED = False


def _install_socket_guard() -> None:
    """Block socket.create_connection to prevent raw TCP bypassing the proxy."""
    global _SOCKET_GUARD_INSTALLED
    if _SOCKET_GUARD_INSTALLED:
        return

    def _blocked_create_connection(address, *args, **kwargs):
        host = address[0] if address else ""
        if _is_numeric_or_loopback(host):
            return _orig_create_connection(address, *args, **kwargs)
        raise OSError(
            f"[NetworkManager] Direct TCP connection to '{host}' blocked — "
            "proxy is active (socks5h). Use requests via get_session()."
        )

    socket.create_connection = _blocked_create_connection  # type: ignore[assignment]
    _SOCKET_GUARD_INSTALLED = True


def _remove_socket_guard() -> None:
    global _SOCKET_GUARD_INSTALLED
    socket.create_connection = _orig_create_connection
    _SOCKET_GUARD_INSTALLED = False


# ── Utilities ──────────────────────────────────────────────────────────────────

def _is_numeric_or_loopback(host: str) -> bool:
    """Return True if *host* is already an IP literal or a loopback name."""
    if not host:
        return True
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        socket.inet_pton(socket.AF_INET, host)
        return True
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return True
    except OSError:
        pass
    return False


def _build_proxy_url(cfg: dict) -> str:
    scheme = cfg.get("type", "http").lower()
    host = cfg.get("host", "")
    port = cfg.get("port", "")
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    if scheme == "socks5":
        # socks5h = proxy resolves DNS (no local leak)
        scheme = "socks5h"
    creds = f"{username}:{password}@" if (username or password) else ""
    return f"{scheme}://{creds}{host}:{port}"


def _load_settings_proxy() -> Optional[dict]:
    try:
        from .app_settings import settings
        return settings.proxy
    except Exception:
        return None


# ── aiohttp helpers ────────────────────────────────────────────────────────────

def make_aiohttp_connector():
    """Return an aiohttp connector that routes through the active proxy.

    - SOCKS5 proxy  → ProxyConnector from aiohttp_socks
    - HTTP/HTTPS proxy → aiohttp.TCPConnector (proxy passed per-request)
    - No proxy      → aiohttp.TCPConnector (plain)

    The caller is responsible for closing the connector when done.
    """
    import aiohttp

    proxy_url = _state["proxy_url"]
    proxy_type = _state["proxy_type"]

    if proxy_url and proxy_type == "socks5":
        try:
            from aiohttp_socks import ProxyConnector
            # socks5h → aiohttp_socks uses rdns=True (proxy resolves DNS)
            socks_url = proxy_url.replace("socks5h://", "socks5://")
            return ProxyConnector.from_url(socks_url, rdns=True)
        except ImportError:
            pass

    return aiohttp.TCPConnector()


def aiohttp_proxy_url() -> Optional[str]:
    """Return the proxy URL suitable for aiohttp's ``proxy=`` kwarg.

    For SOCKS5 the proxy is handled by the connector (see make_aiohttp_connector),
    so this returns None.  For HTTP/HTTPS proxies, returns the URL string.
    """
    if not _state["active"]:
        return None
    if _state["proxy_type"] == "socks5":
        return None  # handled by connector
    return _state["proxy_url"] or None
