"""Passive SSL/TLS certificate and protocol inspection."""

import socket
import ssl
from datetime import UTC, datetime
from urllib.parse import urlparse

from laitoxx.features.utilities.shared_utils import Color

from .web_security_runtime import _TIMEOUT, _ensure_scheme, _fail, _ok, _row, _section, _warn


def check_ssl_tls(url: str):
    """Raw TLS inspection using stdlib ssl for full cert detail access."""
    parsed = urlparse(_ensure_scheme(url))
    host = parsed.hostname
    port = parsed.port or 443

    _section("SSL / TLS Checker")

    if parsed.scheme == "http":
        _warn("URL uses HTTP - no TLS to check on port 80.")
        _warn("Try with https:// to inspect the certificate.")
        return

    try:
        from laitoxx.core.settings.network_manager import _orig_getaddrinfo

        infos = _orig_getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        family, _, _, _, addr = infos[0]
    except Exception:
        try:
            infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            family, _, _, _, addr = infos[0]
        except Exception as e:
            _fail(f"DNS resolution failed: {e}")
            return

    try:
        from laitoxx.core.settings.network_manager import _orig_create_connection

        raw = _orig_create_connection(addr, timeout=_TIMEOUT.total)
    except Exception:
        try:
            raw = socket.create_connection(addr, timeout=_TIMEOUT.total)
        except Exception as e:
            _fail(f"TCP connection failed: {e}")
            return

    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            cert = tls.getpeercert()
            cipher = tls.cipher()
            version = tls.version()
    except ssl.SSLCertVerificationError as e:
        raw.close()
        _fail(f"Certificate verification failed: {e.reason}")
        return
    except Exception as e:
        raw.close()
        _fail(f"TLS connection error: {e}")
        return

    _row(
        "Protocol",
        version,
        Color.LIGHT_GREEN if "TLSv1.3" in version else Color.YELLOW if "TLSv1.2" in version else Color.RED,
    )
    _row("Cipher suite", cipher[0])
    _row("Key bits", str(cipher[2]))

    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))
    not_after = cert.get("notAfter", "")

    _row("Subject CN", subject.get("commonName", "N/A"))
    _row("Issuer", issuer.get("organizationName", "N/A"))
    _row("Valid until", not_after)

    if not_after:
        try:
            exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
            days_left = (exp - datetime.now(UTC)).days
            if days_left < 0:
                _fail(f"Certificate EXPIRED {abs(days_left)} day(s) ago!")
            elif days_left < 30:
                _warn(f"Certificate expires in {days_left} day(s) - renew soon.")
            else:
                _ok(f"Certificate valid for {days_left} more day(s).")
        except ValueError:
            pass

    sans = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
    if sans:
        display = ", ".join(sans[:6]) + (f"  (+{len(sans) - 6} more)" if len(sans) > 6 else "")
        _row("SANs", display)

    if "TLSv1.0" in version or "TLSv1.1" in version or "SSLv" in version:
        _fail(f"Deprecated protocol {version} in use - upgrade to TLS 1.2+.")
    elif "TLSv1.2" in version:
        _warn("TLS 1.2 is acceptable but TLS 1.3 is preferred.")
    else:
        _ok("TLS 1.3 - modern and secure.")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)
