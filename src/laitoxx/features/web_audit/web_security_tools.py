"""
Web Security Tools - four passive checks bundled in one module.

Checks
------
1. SSL/TLS Checker        - cert expiry, chain, cipher, protocol version
2. CORS Checker           - misconfigured Access-Control-Allow-Origin
3. Open Redirect Scanner  - common redirect parameters probed with sentinel
4. Security Headers       - CSP, HSTS, X-Frame-Options, etc. with grading

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
from urllib.parse import urlencode, urlparse

import aiohttp

from laitoxx.core.settings.network_manager import aiohttp_proxy_url
from laitoxx.features.utilities.shared_utils import Color

_CORS_ORIGINS = [
    "https://evil.com",
    "null",
    "https://attacker.net",
]


from .web_security_runtime import (
    _ensure_scheme,
    _fail,
    _make_session,
    _ok,
    _section,
    _warn,
)
from .web_security_tls import check_ssl_tls as check_ssl_tls


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
                        _warn("Wildcard ACAO (*) - public resources allowed from any origin.")
                        issues.append("wildcard")
                    elif acao == origin:
                        if acac == "true":
                            _fail(
                                f"CRITICAL: ACAO reflects '{origin}' + Allow-Credentials: true → CORS bypass possible!"
                            )
                            issues.append("reflect+creds")
                        else:
                            _warn(f"ACAO reflects '{origin}' (no credentials) - may be intentional but verify.")
                            issues.append("reflect")
                    elif acao == "null" and origin == "null":
                        _fail("ACAO: null accepted - exploitable via sandboxed iframe!")
                        issues.append("null")
                    else:
                        _ok(f"Origin '{origin}' → not reflected (ACAO: '{acao or 'absent'}')")

                    if "Origin" not in vary and acao:
                        _warn("'Vary: Origin' missing - caching may leak CORS responses.")

            except aiohttp.ClientError as e:
                _fail(f"Request failed ({origin}): {e}")

    if not issues:
        _ok("No CORS misconfigurations detected.")
    print(f"\n{Color.DARK_RED}└" + "─" * 45)


def check_cors(url: str):
    asyncio.run(_check_cors_async(_ensure_scheme(url)))


_REDIRECT_PARAMS = [
    "url",
    "redirect",
    "redirect_url",
    "redirectUrl",
    "return",
    "returnUrl",
    "return_url",
    "next",
    "goto",
    "dest",
    "destination",
    "target",
    "redir",
    "redirect_uri",
    "callback",
    "continue",
    "forward",
    "location",
    "to",
    "out",
    "link",
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
        print(
            f"\n{Color.DARK_GRAY}  [{Color.RED}!{Color.DARK_GRAY}]{Color.RED} {len(found)} open redirect(s) detected."
        )
    else:
        _ok(f"No open redirect found across {len(_REDIRECT_PARAMS)} parameters.")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)


def check_open_redirect(url: str):
    asyncio.run(_check_redirect_async(_ensure_scheme(url)))


_SECURITY_HEADERS = [
    ("Content-Security-Policy", "CSP", "high"),
    ("Strict-Transport-Security", "HSTS", "high"),
    ("X-Frame-Options", "X-Frame-Options", "medium"),
    ("X-Content-Type-Options", "X-Content-Type-Options", "medium"),
    ("Referrer-Policy", "Referrer-Policy", "low"),
    ("Permissions-Policy", "Permissions-Policy", "low"),
    ("Cross-Origin-Opener-Policy", "COOP", "medium"),
    ("Cross-Origin-Embedder-Policy", "COEP", "low"),
    ("Cross-Origin-Resource-Policy", "CORP", "low"),
    ("X-XSS-Protection", "X-XSS-Protection", "low"),
]


async def _check_headers_async(url: str):
    _section("Security Headers Checker")
    proxy = aiohttp_proxy_url()

    try:
        async with _make_session() as session:
            async with session.get(url, allow_redirects=True, proxy=proxy) as r:
                headers = r.headers
                missing_high = 0
                missing_med = 0

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
    "ssl": check_ssl_tls,
    "cors": check_cors,
    "redirect": check_open_redirect,
    "headers": check_security_headers,
}


def web_security_tools(data=None):
    if data:
        url = data.get("url", "").strip()
        check = data.get("check", "all").lower()
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Web Security Tools\n")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.DARK_RED} SSL/TLS Checker")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.DARK_RED} CORS Checker")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.DARK_RED} Open Redirect Scanner")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}]{Color.DARK_RED} Security Headers")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}5{Color.DARK_GRAY}]{Color.DARK_RED} Run all checks\n")

        sel = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Select check: ").strip()
        check = {"1": "ssl", "2": "cors", "3": "redirect", "4": "headers"}.get(sel, "all")

        url = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter target URL: {Color.RESET}"
        ).strip()

    if not url:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No URL provided.")
        return

    url = _ensure_scheme(url)
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Target: {Color.WHITE}{url}\n")

    if check == "all":
        for fn in _CHECK_MAP.values():
            fn(url)
    elif check in _CHECK_MAP:
        _CHECK_MAP[check](url)
    else:
        _fail(f"Unknown check '{check}'. Use: ssl, cors, redirect, headers, all.")

    print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Web security check complete.")
