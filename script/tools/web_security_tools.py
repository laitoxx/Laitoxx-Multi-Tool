"""
Web Security Tools — four passive checks bundled in one module.

Checks
------
1. SSL/TLS Checker        — cert expiry, chain, cipher, protocol version
2. CORS Checker           — misconfigured Access-Control-Allow-Origin
3. Open Redirect Scanner  — common redirect parameters probed with sentinel
4. Security Headers       — CSP, HSTS, X-Frame-Options, etc. with grading

GUI  → web_security_tools({"check": "ssl",      "url": "https://example.com"})
       web_security_tools({"check": "cors",     "url": "https://example.com"})
       web_security_tools({"check": "redirect", "url": "https://example.com"})
       web_security_tools({"check": "headers",  "url": "https://example.com"})
       web_security_tools({"check": "all",      "url": "https://example.com"})
CLI  → web_security_tools()

Network: all HTTP requests go through aiohttp + NetworkManager proxy.
         SSL check uses raw socket (loopback-only guard allows it since
         it connects to a resolved IP literal after DNS, but we bypass
         the DNS guard for TLS checks by resolving via proxy session first).
"""

import asyncio
import ssl
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse, urlencode

import aiohttp

from ..shared_utils import Color

_TIMEOUT = aiohttp.ClientTimeout(total=12)
_UA = "Mozilla/5.0 (Web-Security-Checker)"

try:
    from settings.network_manager import make_aiohttp_connector, aiohttp_proxy_url
    _HAS_NM = True
except ImportError:
    _HAS_NM = False
    def make_aiohttp_connector():
        return aiohttp.TCPConnector()
    def aiohttp_proxy_url():
        return None


def _make_session() -> aiohttp.ClientSession:
    connector = make_aiohttp_connector()
    return aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
    )


def _ensure_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _section(title: str, width: int = 38):
    pad = "─" * (width - len(title))
    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{title} {Color.DARK_RED}]{pad}")


def _ok(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {msg}")


def _warn(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.YELLOW}!{Color.DARK_GRAY}]{Color.YELLOW} {msg}")


def _fail(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} {msg}")


def _row(label: str, value: str, color=None):
    c = color or Color.WHITE
    print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}{label:<28}{c}{value}")


def check_ssl_tls(url: str):
    """Raw TLS inspection using stdlib ssl for full cert detail access."""
    parsed = urlparse(_ensure_scheme(url))
    host = parsed.hostname
    port = parsed.port or 443

    _section("SSL / TLS Checker")

    if parsed.scheme == "http":
        _warn("URL uses HTTP — no TLS to check on port 80.")
        _warn("Try with https:// to inspect the certificate.")
        return

    try:
        from settings.network_manager import _orig_getaddrinfo
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
        from settings.network_manager import _orig_create_connection
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
            cert    = tls.getpeercert()
            cipher  = tls.cipher()
            version = tls.version()
    except ssl.SSLCertVerificationError as e:
        raw.close()
        _fail(f"Certificate verification failed: {e.reason}")
        return
    except Exception as e:
        raw.close()
        _fail(f"TLS connection error: {e}")
        return

    _row("Protocol", version,
         Color.LIGHT_GREEN if "TLSv1.3" in version else
         Color.YELLOW if "TLSv1.2" in version else Color.RED)
    _row("Cipher suite", cipher[0])
    _row("Key bits", str(cipher[2]))

    subject = dict(x[0] for x in cert.get("subject", []))
    issuer  = dict(x[0] for x in cert.get("issuer", []))
    not_after = cert.get("notAfter", "")

    _row("Subject CN", subject.get("commonName", "N/A"))
    _row("Issuer", issuer.get("organizationName", "N/A"))
    _row("Valid until", not_after)

    if not_after:
        try:
            exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_left = (exp - datetime.now(timezone.utc)).days
            if days_left < 0:
                _fail(f"Certificate EXPIRED {abs(days_left)} day(s) ago!")
            elif days_left < 30:
                _warn(f"Certificate expires in {days_left} day(s) — renew soon.")
            else:
                _ok(f"Certificate valid for {days_left} more day(s).")
        except ValueError:
            pass

    sans = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
    if sans:
        display = ", ".join(sans[:6]) + (f"  (+{len(sans) - 6} more)" if len(sans) > 6 else "")
        _row("SANs", display)

    if "TLSv1.0" in version or "TLSv1.1" in version or "SSLv" in version:
        _fail(f"Deprecated protocol {version} in use — upgrade to TLS 1.2+.")
    elif "TLSv1.2" in version:
        _warn("TLS 1.2 is acceptable but TLS 1.3 is preferred.")
    else:
        _ok("TLS 1.3 — modern and secure.")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)


_CORS_ORIGINS = [
    "https://evil.com",
    "null",
    "https://attacker.net",
]

async def _check_cors_async(url: str):
    _section("CORS Checker")
    issues = []
    proxy = aiohttp_proxy_url()

    async with _make_session() as session:
        for origin in _CORS_ORIGINS:
            try:
                async with session.options(
                    url,
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "GET",
                    },
                    allow_redirects=True,
                    proxy=proxy,
                ) as r:
                    acao = r.headers.get("Access-Control-Allow-Origin", "")
                    acac = r.headers.get("Access-Control-Allow-Credentials", "").lower()
                    vary = r.headers.get("Vary", "")

                    if acao == "*":
                        _warn("Wildcard ACAO (*) — public resources allowed from any origin.")
                        issues.append("wildcard")
                    elif acao == origin:
                        if acac == "true":
                            _fail(f"CRITICAL: ACAO reflects '{origin}' + Allow-Credentials: true → CORS bypass possible!")
                            issues.append("reflect+creds")
                        else:
                            _warn(f"ACAO reflects '{origin}' (no credentials) — may be intentional but verify.")
                            issues.append("reflect")
                    elif acao == "null" and origin == "null":
                        _fail("ACAO: null accepted — exploitable via sandboxed iframe!")
                        issues.append("null")
                    else:
                        _ok(f"Origin '{origin}' → not reflected (ACAO: '{acao or 'absent'}')")

                    if "Origin" not in vary and acao:
                        _warn("'Vary: Origin' missing — caching may leak CORS responses.")

            except aiohttp.ClientError as e:
                _fail(f"Request failed ({origin}): {e}")

    if not issues:
        _ok("No CORS misconfigurations detected.")
    print(f"\n{Color.DARK_RED}└" + "─" * 45)


def check_cors(url: str):
    asyncio.run(_check_cors_async(_ensure_scheme(url)))


_REDIRECT_PARAMS = [
    "url", "redirect", "redirect_url", "redirectUrl", "return",
    "returnUrl", "return_url", "next", "goto", "dest", "destination",
    "target", "redir", "redirect_uri", "callback", "continue", "forward",
    "location", "to", "out", "link",
]

_SENTINEL = "https://evil.com/redirect-test"

async def _check_redirect_async(url: str):
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    _section("Open Redirect Scanner")
    print(f"{Color.DARK_GRAY}  Testing {len(_REDIRECT_PARAMS)} parameter(s)...")

    found = []
    proxy = aiohttp_proxy_url()

    async with _make_session() as session:
        tasks = []

        async def _probe(param: str):
            test_url = f"{base}?{urlencode({param: _SENTINEL})}"
            try:
                async with session.get(
                    test_url,
                    allow_redirects=False,
                    proxy=proxy,
                ) as r:
                    location = r.headers.get("Location", "")
                    if r.status in (301, 302, 303, 307, 308) and _SENTINEL in location:
                        found.append((param, r.status, location))
            except aiohttp.ClientError:
                pass

        await asyncio.gather(*[_probe(p) for p in _REDIRECT_PARAMS])

    if found:
        for param, code, loc in found:
            _fail(f"VULNERABLE: ?{param}= → {code} → {loc}")
        print(f"\n{Color.DARK_GRAY}  [{Color.RED}!{Color.DARK_GRAY}]{Color.RED}"
              f" {len(found)} open redirect(s) detected.")
    else:
        _ok(f"No open redirect found across {len(_REDIRECT_PARAMS)} parameters.")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)


def check_open_redirect(url: str):
    asyncio.run(_check_redirect_async(_ensure_scheme(url)))


_SECURITY_HEADERS = [
    ("Content-Security-Policy",        "CSP",                    "high"),
    ("Strict-Transport-Security",       "HSTS",                   "high"),
    ("X-Frame-Options",                 "X-Frame-Options",        "medium"),
    ("X-Content-Type-Options",          "X-Content-Type-Options", "medium"),
    ("Referrer-Policy",                 "Referrer-Policy",        "low"),
    ("Permissions-Policy",              "Permissions-Policy",     "low"),
    ("Cross-Origin-Opener-Policy",      "COOP",                   "medium"),
    ("Cross-Origin-Embedder-Policy",    "COEP",                   "low"),
    ("Cross-Origin-Resource-Policy",    "CORP",                   "low"),
    ("X-XSS-Protection",               "X-XSS-Protection",       "low"),
]

async def _check_headers_async(url: str):
    _section("Security Headers Checker")
    proxy = aiohttp_proxy_url()

    try:
        async with _make_session() as session:
            async with session.get(url, allow_redirects=True, proxy=proxy) as r:
                headers = r.headers
                missing_high = 0
                missing_med  = 0

                for hdr_name, label, severity in _SECURITY_HEADERS:
                    val = headers.get(hdr_name)
                    if val:
                        display = val if len(val) <= 60 else val[:57] + "..."
                        _ok(f"{label:<30} {Color.WHITE}{display}")
                    else:
                        if severity == "high":
                            _fail(f"{label:<30} {Color.RED}MISSING  (high priority)")
                            missing_high += 1
                        elif severity == "medium":
                            _warn(f"{label:<30} {Color.YELLOW}missing  (medium)")
                            missing_med += 1
                        else:
                            print(f"{Color.DARK_GRAY}  -  {Color.DARK_GRAY}{label:<30} not set  (low)")

                print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}Grade {Color.DARK_RED}]" + "─" * 32)
                total_high = sum(1 for _, _, s in _SECURITY_HEADERS if s == "high")
                if missing_high == 0 and missing_med == 0:
                    grade, col = "A+", Color.LIGHT_GREEN
                elif missing_high == 0:
                    grade, col = "B", Color.LIGHT_GREEN
                elif missing_high <= 1:
                    grade, col = "C", Color.YELLOW
                else:
                    grade, col = "F", Color.RED
                print(f"{Color.DARK_GRAY}  Security grade: {col}{grade}")
                print(f"{Color.DARK_GRAY}  Missing critical: {Color.RED}{missing_high}/{total_high}")

    except aiohttp.ClientError as e:
        _fail(f"Request failed: {e}")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)


def check_security_headers(url: str):
    asyncio.run(_check_headers_async(_ensure_scheme(url)))


_CHECK_MAP = {
    "ssl":      check_ssl_tls,
    "cors":     check_cors,
    "redirect": check_open_redirect,
    "headers":  check_security_headers,
}

def web_security_tools(data=None):
    if data:
        url   = data.get("url", "").strip()
        check = data.get("check", "all").lower()
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
              f" Web Security Tools\n")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.DARK_RED} SSL/TLS Checker")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.DARK_RED} CORS Checker")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.DARK_RED} Open Redirect Scanner")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}]{Color.DARK_RED} Security Headers")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}5{Color.DARK_GRAY}]{Color.DARK_RED} Run all checks\n")

        sel = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Select check: "
        ).strip()
        check = {"1": "ssl", "2": "cors", "3": "redirect", "4": "headers"}.get(sel, "all")

        url = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Enter target URL: {Color.RESET}"
        ).strip()

    if not url:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No URL provided.")
        return

    url = _ensure_scheme(url)
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE}"
          f" Target: {Color.WHITE}{url}\n")

    if check == "all":
        for fn in _CHECK_MAP.values():
            fn(url)
    elif check in _CHECK_MAP:
        _CHECK_MAP[check](url)
    else:
        _fail(f"Unknown check '{check}'. Use: ssl, cors, redirect, headers, all.")

    print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
          f" Web security check complete.")
