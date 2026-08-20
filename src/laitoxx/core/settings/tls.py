"""Shared system-trust TLS context for direct stdlib connections."""

from __future__ import annotations

import ssl


def trusted_ssl_context() -> ssl.SSLContext:
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()
