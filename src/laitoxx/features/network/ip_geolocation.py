import socket

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.utilities.shared_utils import Color

_SESSION = get_session()
ABUSEIPDB_API_KEY = ""  # https://www.abuseipdb.com/
VIRUSTOTAL_API_KEY = ""  # https://www.virustotal.com/
SHODAN_API_KEY = ""  # https://shodan.io/

TIMEOUT = 12
from .ip_runtime import _end, _err, _ok, _row, _safe_get, _section, _warn


def _layer_geo(ip: str) -> dict:
    _section("L1 · Geolocation & IP type")
    r, err = _safe_get(f"https://ipwho.is/{ip}")
    if err or r is None:
        _err(f"ipwho.is failed: {err}")
        return {}
    try:
        info = r.json()
    except ValueError:
        _err("Could not parse ipwho.is response")
        return {}

    if not info.get("success"):
        _err(f"ipwho.is: {info.get('message', 'unknown error')}")
        return {}

    _row("IP", info.get("ip"))
    _row("Type", info.get("type"))  # IPv4 / IPv6
    _row("Continent", info.get("continent"))
    _row("Country", f"{info.get('country')} ({info.get('country_code')})")
    _row("Region", info.get("region"))
    _row("City", info.get("city"))
    _row("Latitude", info.get("latitude"))
    _row("Longitude", info.get("longitude"))
    _row("Postal Code", info.get("postal"))
    _row(
        "Timezone",
        info.get("timezone", {}).get("id") if isinstance(info.get("timezone"), dict) else info.get("timezone"),
    )

    conn = info.get("connection", {})
    _row("ASN", conn.get("asn") or info.get("asn"))
    _row("Organization", conn.get("org") or info.get("org"))
    _row("ISP", conn.get("isp") or info.get("isp"))
    _row("Domain", conn.get("domain"))

    _end()
    return info


def _layer_ipapi(ip: str):
    _section("L1.5 · Security & Context")
    r, err = _safe_get(f"https://api.ipapi.is/?q={ip}")
    if err or r is None:
        _err(f"ipapi.is failed: {err}")
        _end()
        return

    try:
        data = r.json()
    except ValueError:
        _err("Could not parse ipapi.is response")
        _end()
        return

    if "error" in data:
        _err(f"ipapi.is error: {data.get('error')}")
        _end()
        return

    # Extract company info
    comp = data.get("company")
    if isinstance(comp, dict):
        ctype = comp.get("type", "unknown").upper()
        _row("Company Name", comp.get("name"))
        _row(
            "Network Type",
            ctype,
            color=Color.YELLOW if ctype != "ISP" else Color.LIGHT_GREEN,
        )
    elif isinstance(comp, str) and comp:
        _row("Company Name", comp)

    # Security flags
    def row_bool(label, val, danger=True):
        if val is None:
            return
        # Val can be boolean True/False
        if val:
            color = Color.RED if danger else Color.YELLOW
            text = "Yes"
        else:
            color = Color.LIGHT_GREEN
            text = "No"
        _row(label, text, color=color)

    row_bool("Is VPN?", data.get("is_vpn"))
    row_bool("Is Tor Node?", data.get("is_tor"))
    row_bool("Is Proxy?", data.get("is_proxy"))
    row_bool("Is Datacenter?", data.get("is_datacenter"), danger=False)
    row_bool("Is Mobile?", data.get("is_mobile"), danger=False)
    row_bool("Is Crawler?", data.get("is_crawler"), danger=False)
    row_bool("Known Abuser?", data.get("is_abuser"))

    vpn = data.get("vpn")
    if isinstance(vpn, dict):
        _row("VPN Service", vpn.get("service"), color=Color.RED)
    elif isinstance(vpn, str) and vpn:
        _row("VPN Service", vpn, color=Color.RED)

    _end()


def _layer_rdns(ip: str):
    _section("L2 · Reverse DNS (PTR)")
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        _ok(hostname)
        keywords = [
            "mail",
            "smtp",
            "vpn",
            "gw",
            "gateway",
            "proxy",
            "db",
            "database",
            "backup",
            "dev",
            "stg",
            "staging",
            "printer",
            "cam",
            "router",
            "fw",
            "firewall",
            "nas",
            "store",
            "cdn",
            "api",
            "admin",
        ]
        found = [kw for kw in keywords if kw in hostname.lower()]
        if found:
            _warn(f"Hostname hints at role: {', '.join(found)}")
        return hostname
    except socket.herror:
        _warn("No PTR record found")
        return None
    except Exception as e:
        _err(str(e))
        return None
    finally:
        _end()
