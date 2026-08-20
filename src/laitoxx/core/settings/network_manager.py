"""Central proxy-aware requests session and direct-socket guards."""

from __future__ import annotations

import os
import socket
import threading

import requests
import requests.adapters

# ── Internal state ─────────────────────────────────────────────────────────────

_lock = threading.Lock()

# Saved originals so we can restore them on disable
_orig_getaddrinfo = socket.getaddrinfo
_orig_gethostbyname = socket.gethostbyname
_orig_gethostbyname_ex = socket.gethostbyname_ex
_orig_create_connection = socket.create_connection
_orig_socket_connect = socket.socket.connect

# Saved original requests.Session.__init__ (before any monkey-patching)
_orig_session_init = requests.Session.__init__

_state: dict = {
    "active": False,
    "proxy_url": "",  # e.g. "socks5h://user:pass@127.0.0.1:1080"
    "proxy_type": "http",
    "proxy_host": "",
}

# Maximum timeout (seconds) applied to every request that doesn't set its own.
_DEFAULT_TIMEOUT = 30

# The single shared session used by all tools
_shared_session: requests.Session = requests.Session()


# ── Public API ─────────────────────────────────────────────────────────────────


from .network_aiohttp import make_connector, request_proxy_url
from .proxy_config import (
    build_proxies as build_proxies,
)
from .proxy_config import (
    build_proxy_url as build_proxy_url,
)
from .proxy_config import (
    load_settings_proxy as _load_settings_proxy,
)


def make_aiohttp_connector():
    return make_connector(_state)


def aiohttp_proxy_url() -> str | None:
    return request_proxy_url(_state)


from .network_guards import NetworkGuards

_guards = NetworkGuards(
    _state,
    {
        "getaddrinfo": _orig_getaddrinfo,
        "gethostbyname": _orig_gethostbyname,
        "gethostbyname_ex": _orig_gethostbyname_ex,
        "create_connection": _orig_create_connection,
        "socket_connect": _orig_socket_connect,
    },
)


def _install_dns_guard() -> None:
    _guards.install_dns()


def _remove_dns_guard() -> None:
    _guards.remove_dns()


def _install_socket_guard() -> None:
    _guards.install_socket()


def _remove_socket_guard() -> None:
    _guards.remove_socket()


class NetworkManager:
    """Static controller - no instantiation needed."""

    @staticmethod
    def apply(proxy_cfg: dict | None = None) -> None:
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
                proxy_url = build_proxy_url(proxy_cfg)
                if not proxy_url:
                    raise ValueError("Proxy is enabled but host or port is missing")
                _state["active"] = True
                _state["proxy_url"] = proxy_url
                _state["proxy_type"] = proxy_cfg.get("type", "http").lower()
                _state["proxy_host"] = str(proxy_cfg.get("host", "")).strip()
                _rebuild_session(proxy_url)
                _set_env(proxy_url)
                # Fail closed for every proxy type. HTTP CONNECT and SOCKS both
                # resolve destinations without requiring application DNS.
                _install_dns_guard()
                _install_socket_guard()
            else:
                _state["active"] = False
                _state["proxy_url"] = ""
                _state["proxy_type"] = "http"
                _state["proxy_host"] = ""
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
    """Module-level shortcut so tools can: ``from laitoxx.core.settings.network_manager import get_session``."""
    return _shared_session


# ── Session helpers ────────────────────────────────────────────────────────────


def _apply_default_timeout_to_session(sess: requests.Session) -> None:
    """Wrap sess.request so calls that omit timeout get _DEFAULT_TIMEOUT."""
    _orig_req = sess.request

    def _bounded(method, url, **kwargs):
        kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
        return _orig_req(method, url, **kwargs)

    sess.request = _bounded  # type: ignore[method-assign]


def _rebuild_session(proxy_url: str | None) -> None:
    global _shared_session
    # Always use the stdlib requests.Session.__init__ - not our patched version -
    # to avoid infinite recursion when _patch_requests_session_class is already set.
    sess = requests.Session.__new__(requests.Session)
    _orig_session_init(sess)
    if proxy_url:
        sess.proxies.update({"http": proxy_url, "https": proxy_url})
    _apply_default_timeout_to_session(sess)
    _shared_session = sess
    _patch_requests_session_class(proxy_url)
    _patch_requests_module(proxy_url)


def _patch_requests_session_class(proxy_url: str | None) -> None:
    """Monkey-patch requests.Session.__init__ so any session created by
    third-party libraries also inherits the proxy settings and default timeout."""

    def _patched_init(self, *args, **kwargs):
        _orig_session_init(self, *args, **kwargs)
        if proxy_url:
            self.proxies.update({"http": proxy_url, "https": proxy_url})
        _apply_default_timeout_to_session(self)

    requests.Session.__init__ = _patched_init  # type: ignore[method-assign]


def _patch_requests_module(proxy_url: str | None) -> None:
    """Route requests.* through the shared session and enforce a default timeout.

    Always active (proxy or not) so bare ``requests.get(url)`` calls never
    block indefinitely - they get _DEFAULT_TIMEOUT if the caller omits one.
    """

    def _make_method(method_name: str):
        def _method(url, **kwargs):
            kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
            return getattr(_shared_session, method_name)(url, **kwargs)

        _method.__name__ = method_name
        return _method

    requests.get = _make_method("get")  # type: ignore[assignment]
    requests.post = _make_method("post")  # type: ignore[assignment]
    requests.put = _make_method("put")  # type: ignore[assignment]
    requests.patch = _make_method("patch")  # type: ignore[assignment]
    requests.delete = _make_method("delete")  # type: ignore[assignment]
    requests.head = _make_method("head")  # type: ignore[assignment]
    requests.options = _make_method("options")  # type: ignore[assignment]

    def _request(method, url, **kwargs):
        kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
        return _shared_session.request(method, url, **kwargs)

    requests.request = _request  # type: ignore[assignment]


# ── Environment variables ──────────────────────────────────────────────────────

_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def _set_env(proxy_url: str) -> None:
    for k in _ENV_KEYS:
        os.environ[k] = proxy_url


def _clear_env() -> None:
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


# ── DNS leak guard ─────────────────────────────────────────────────────────────


# ── Raw socket connection guard ────────────────────────────────────────────────


# ── Utilities ──────────────────────────────────────────────────────────────────


# ── aiohttp helpers ────────────────────────────────────────────────────────────


# ── Bootstrap: install timeout wrappers at import time ─────────────────────────
# This ensures _DEFAULT_TIMEOUT is enforced even if NetworkManager.apply() is
# never called (e.g. proxy disabled, app started without settings).
_patch_requests_session_class(None)
_patch_requests_module(None)
_apply_default_timeout_to_session(_shared_session)
