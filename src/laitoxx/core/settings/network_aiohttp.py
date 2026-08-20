"""aiohttp adapters for NetworkManager state."""


def _system_ssl_context():
    """Use the native trust store when available, without weakening TLS checks."""
    import ssl

    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


def make_connector(state: dict):
    import aiohttp

    proxy_url = state["proxy_url"]
    proxy_type = state["proxy_type"]
    if proxy_url and proxy_type == "socks5":
        try:
            from aiohttp_socks import ProxyConnector
        except ImportError as exc:
            raise RuntimeError(
                "SOCKS proxy is active but aiohttp-socks is unavailable; refusing a direct fallback connection."
            ) from exc
        socks_url = proxy_url.replace("socks5h://", "socks5://")
        return ProxyConnector.from_url(socks_url, rdns=True)
    return aiohttp.TCPConnector(ssl=_system_ssl_context())


def request_proxy_url(state: dict) -> str | None:
    if not state["active"] or state["proxy_type"] == "socks5":
        return None
    return state["proxy_url"] or None
