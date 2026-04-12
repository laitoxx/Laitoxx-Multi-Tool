import ssl
import socket
import time
from urllib.parse import urlparse, ParseResult

import requests

from ..shared_utils import Color

try:
    from settings.network_manager import get_session as _get_nm_session
except Exception:
    _get_nm_session = None


USER_AGENT = "Mozilla/5.0 (OSINT Inspector)"
REQUEST_TIMEOUT = 15
TLS_TIMEOUT = 10
MAX_COOKIE_VALUE_LEN = 60
MAX_SAN_DISPLAY = 8


def _get_input_url(data) -> str:
    if data:
        return data.get("url", "").strip()
    return input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
        f" Enter URL to inspect: {Color.RESET}"
    ).strip()


def _normalize_url(url: str) -> tuple[str, ParseResult | None]:
    if not url:
        return url, None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        return url, None
    return url, parsed


def _fetch_response(url: str):
    try:
        session = _get_nm_session() if _get_nm_session else requests.Session()
        start = time.perf_counter()
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        return response, elapsed_ms, None
    except requests.exceptions.RequestException as exc:
        return None, None, exc


def _status_color(code: int) -> str:
    if 200 <= code < 300:
        return Color.LIGHT_GREEN
    if 300 <= code < 400:
        return Color.YELLOW
    return Color.RED


def _print_status(response, status_color: str, elapsed_ms: float):
    print(f"{Color.DARK_RED}[ {Color.LIGHT_RED}HTTP Status {Color.DARK_RED}]" + "-" * 27)
    print(f"{Color.DARK_GRAY}  - {Color.WHITE}Status:        {status_color}{response.status_code} {response.reason}")
    print(f"{Color.DARK_GRAY}  - {Color.WHITE}Response time: {Color.LIGHT_BLUE}{elapsed_ms:.0f} ms")
    print(f"{Color.DARK_GRAY}  - {Color.WHITE}Final URL:     {Color.LIGHT_BLUE}{response.url}")


def _print_redirect_chain(response, status_color: str):
    if not response.history:
        return
    print(
        f"\n{Color.DARK_RED}[ {Color.LIGHT_RED}Redirect Chain"
        f" ({len(response.history)} hop(s)) {Color.DARK_RED}]" + "-" * 10
    )
    for i, r in enumerate(response.history):
        print(f"{Color.DARK_GRAY}  [{i + 1}] {Color.YELLOW}{r.status_code}"
              f" {Color.DARK_GRAY}-> {Color.WHITE}{r.url}")
    print(f"{Color.DARK_GRAY}  [->] {status_color}{response.status_code}"
          f" {Color.DARK_GRAY}-> {Color.WHITE}{response.url}")


def _print_headers(response):
    print(
        f"\n{Color.DARK_RED}[ {Color.LIGHT_RED}Response Headers"
        f" ({len(response.headers)}) {Color.DARK_RED}]" + "-" * 10
    )
    for name, value in response.headers.items():
        print(f"{Color.DARK_GRAY}  {Color.LIGHT_RED}{name:<35}{Color.WHITE}{value}")


def _cookie_flags(cookie) -> str:
    flags = []
    if cookie.secure:
        flags.append("Secure")
    if cookie.has_nonstandard_attr("HttpOnly"):
        flags.append("HttpOnly")
    return f"  {Color.DARK_GRAY}[{', '.join(flags)}]" if flags else ""


def _print_cookies(response):
    print(f"\n{Color.DARK_RED}[ {Color.LIGHT_RED}Cookies {Color.DARK_RED}]" + "-" * 31)
    if not response.cookies:
        print(f"{Color.DARK_GRAY}  - {Color.DARK_GRAY}No cookies set.")
        return
    for cookie in response.cookies:
        value = cookie.value[:MAX_COOKIE_VALUE_LEN]
        print(
            f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}{cookie.name:<25}"
            f"{Color.WHITE}{value}{_cookie_flags(cookie)}"
        )


def _get_tls_host(parsed, response) -> str | None:
    final_parsed = urlparse(response.url)
    if parsed.scheme == "https" or final_parsed.scheme == "https":
        return final_parsed.hostname or parsed.hostname
    return None


def http_inspector(data=None):
    """
    Full HTTP/HTTPS analysis: status, all headers, redirect chain,
    TLS certificate, response time, cookies.

    GUI  -> http_inspector({"url": "https://example.com"})
    CLI  -> http_inspector()
    """
    url = _get_input_url(data)
    if not url:
        print(f"{Color.DARK_GRAY}[{Color.RED}x{Color.DARK_GRAY}]{Color.RED} No URL provided.")
        return

    url, parsed = _normalize_url(url)
    if not parsed:
        print(f"{Color.DARK_GRAY}[{Color.RED}x{Color.DARK_GRAY}]{Color.RED} Invalid URL.")
        return

    print()
    print(f"{Color.LIGHT_BLUE}Inspecting: {Color.WHITE}{url}")
    print()

    response, elapsed_ms, error = _fetch_response(url)
    if error:
        print(f"{Color.DARK_GRAY}[{Color.RED}x{Color.DARK_GRAY}]{Color.RED} Connection error: {error}")
        return

    status_color = _status_color(response.status_code)
    _print_status(response, status_color, elapsed_ms)
    _print_redirect_chain(response, status_color)
    _print_headers(response)
    _print_cookies(response)

    tls_host = _get_tls_host(parsed, response)
    if tls_host:
        _print_tls_info(tls_host)

    print()
    print(f"{Color.DARK_RED}└" + "─" * 45)
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Inspection complete.")

def _print_tls_info(host: str):
    print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}TLS Certificate {Color.DARK_RED}]" + "─" * 24)
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=TLS_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
    except Exception as e:
        print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} TLS error: {e}")
        return

    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))
    sans = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]

    print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}Subject CN:  {Color.WHITE}{subject.get('commonName', 'N/A')}")
    print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}Issuer:      {Color.WHITE}{issuer.get('organizationName', 'N/A')}")
    print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}Valid until: {Color.WHITE}{cert.get('notAfter', 'N/A')}")
    if sans:
        sans_display = ", ".join(sans[:MAX_SAN_DISPLAY])
        if len(sans) > MAX_SAN_DISPLAY:
            sans_display += f"  {Color.DARK_GRAY}(+{len(sans) - MAX_SAN_DISPLAY} more)"
        print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}SANs ({len(sans)}):   {Color.WHITE}{sans_display}")
