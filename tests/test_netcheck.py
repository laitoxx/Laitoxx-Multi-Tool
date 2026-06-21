"""Unit tests for netcheck.py — proxy config builder."""
from __future__ import annotations

import pytest

from laitoxx.core.netcheck import build_proxies


class TestBuildProxies:
    def test_disabled_returns_none(self):
        cfg = {"enabled": False, "type": "http", "host": "127.0.0.1", "port": "8080"}
        assert build_proxies(cfg) is None

    def test_missing_host_returns_none(self):
        cfg = {"enabled": True, "type": "http", "host": "", "port": "8080"}
        assert build_proxies(cfg) is None

    def test_missing_port_returns_none(self):
        cfg = {"enabled": True, "type": "http", "host": "127.0.0.1", "port": ""}
        assert build_proxies(cfg) is None

    def test_empty_config_returns_none(self):
        assert build_proxies({}) is None

    def test_http_proxy(self):
        cfg = {"enabled": True, "type": "http", "host": "10.0.0.1", "port": "3128",
               "username": "", "password": ""}
        result = build_proxies(cfg)
        assert result is not None
        assert result["http"] == "http://10.0.0.1:3128"
        assert result["https"] == "http://10.0.0.1:3128"

    def test_https_proxy(self):
        cfg = {"enabled": True, "type": "https", "host": "proxy.example.com", "port": "443",
               "username": "", "password": ""}
        result = build_proxies(cfg)
        assert result is not None
        assert result["http"].startswith("https://")

    def test_socks5_proxy(self):
        cfg = {"enabled": True, "type": "socks5", "host": "127.0.0.1", "port": "1080",
               "username": "", "password": ""}
        result = build_proxies(cfg)
        assert result is not None
        assert result["http"].startswith("socks5://")

    def test_proxy_with_credentials(self):
        cfg = {"enabled": True, "type": "http", "host": "proxy.local", "port": "8080",
               "username": "user", "password": "pass"}
        result = build_proxies(cfg)
        assert result is not None
        assert "user:pass@" in result["http"]
        assert "proxy.local:8080" in result["http"]

    def test_proxy_without_credentials_no_at_sign(self):
        cfg = {"enabled": True, "type": "http", "host": "proxy.local", "port": "8080",
               "username": "", "password": ""}
        result = build_proxies(cfg)
        assert result is not None
        assert "@" not in result["http"]

    def test_http_and_https_keys_match(self):
        cfg = {"enabled": True, "type": "http", "host": "p.p", "port": "1234",
               "username": "", "password": ""}
        result = build_proxies(cfg)
        assert result["http"] == result["https"]
