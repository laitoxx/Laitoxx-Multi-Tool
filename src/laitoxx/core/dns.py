"""Bounded DNS resolution with local and HTTPS providers."""

from __future__ import annotations

import json
import socket
import urllib.parse
import urllib.request

from laitoxx.core.settings.network_manager import NetworkManager, get_session
from laitoxx.core.settings.tls import trusted_ssl_context

_QTYPE = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "TXT": 16, "AAAA": 28, "CAA": 257}


def query_dns(name: str, record_type: str, timeout: float = 8) -> list[str]:
    """Resolve a supported DNS record type with bounded provider fallbacks."""

    kind = record_type.upper()
    qtype = _QTYPE.get(kind)
    if qtype is None:
        raise ValueError(f"Unsupported DNS record type: {record_type}")
    if kind in {"A", "AAAA"}:
        family = socket.AF_INET if kind == "A" else socket.AF_INET6
        try:
            return sorted({item[4][0] for item in socket.getaddrinfo(name, None, family, socket.SOCK_STREAM)})
        except (OSError, socket.gaierror):
            pass
    try:
        import dns._features

        # A broken optional QUIC dependency must not block UDP or TCP DNS.
        dns._features.force("doq", False)
        import dns.resolver

        resolver = dns.resolver.Resolver()
        resolver.timeout = min(3, timeout)
        resolver.lifetime = timeout
        answer = resolver.resolve(name, kind, raise_on_no_answer=False)
        return sorted({item.to_text().strip() for item in answer}) if answer.rrset else []
    except (ImportError, AttributeError):
        pass
    except Exception:
        pass
    params = {"name": name, "type": qtype}
    headers = {"Accept": "application/dns-json", "User-Agent": "Laitoxx-DNS/1.0"}
    try:
        response = get_session().get(
            "https://dns.google/resolve",
            params=params,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        if NetworkManager.is_active():
            return []
        url = "https://dns.google/resolve?" + urllib.parse.urlencode(params)
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(  # noqa: S310
                request,
                timeout=timeout,
                context=trusted_ssl_context(),
            ) as response:
                payload = json.load(response)
        except Exception:
            return []
    if int(payload.get("Status", -1)) != 0:
        return []
    return sorted(
        {
            str(item.get("data", "")).strip()
            for item in payload.get("Answer", [])
            if isinstance(item, dict) and int(item.get("type", -1)) == qtype and item.get("data")
        }
    )
