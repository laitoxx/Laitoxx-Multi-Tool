import re

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.utilities.shared_utils import Color

_SESSION = get_session()
ABUSEIPDB_API_KEY = ""  # https://www.abuseipdb.com/
VIRUSTOTAL_API_KEY = ""  # https://www.virustotal.com/
SHODAN_API_KEY = ""  # https://shodan.io/

TIMEOUT = 12
from .ip_runtime import _end, _ok, _row, _section


def _layer_http_banner(ip: str, open_ports: list[int]):
    web_ports = [p for p in open_ports if p in (80, 443, 8080, 8443)]
    if not web_ports:
        return

    _section("L8 · HTTP banner grab")
    for port in web_ports:
        scheme = "https" if port in (443, 8443) else "http"
        url = f"{scheme}://{ip}:{port}"
        try:
            r = _SESSION.get(
                url,
                timeout=8,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (OSINT-ip_info)"},
                verify=False,
            )
            headers = r.headers
            title_match = re.search(r"<title[^>]*>(.*?)</title>", r.text[:4096], re.I | re.S)
            title = title_match.group(1).strip()[:80] if title_match else ""

            print(
                f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Port ' + str(port):<26}: {Color.WHITE}{r.status_code} {r.url[:70]}{Color.RESET}"
            )
            if title:
                _row("  Title", title)
            _row("  Server", headers.get("Server"))
            _row("  X-Powered-By", headers.get("X-Powered-By"))
            _row("  Location", headers.get("Location"))

            for path in ["/robots.txt", "/sitemap.xml", "/.well-known/security.txt"]:
                r2 = _SESSION.get(
                    f"{scheme}://{ip}:{port}{path}",
                    timeout=5,
                    verify=False,
                    headers={"User-Agent": "Mozilla/5.0 (OSINT-ip_info)"},
                )
                if r2.status_code == 200 and len(r2.text) < 10000:
                    _ok(f"Found {path} ({len(r2.text)} bytes)")
        except Exception:
            pass
    _end()


def _layer_subnet_hint(ip: str):
    _section("L9 · Subnet context (/24 prefix)")
    try:
        parts = ip.split(".")
        if len(parts) == 4:
            cidr24 = ".".join(parts[:3]) + ".0/24"
            _row("Your /24 block", cidr24)
            _ok(f"Tip: search Shodan/Censys for net:{cidr24} to map all live hosts")
            _ok("Tip: search crt.sh for all certs issued to IPs in this range")
    except Exception:
        pass
    _end()
