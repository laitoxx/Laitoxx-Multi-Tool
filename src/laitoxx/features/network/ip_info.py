import socket

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.utilities.shared_utils import Color

_SESSION = get_session()
ABUSEIPDB_API_KEY = ""  # https://www.abuseipdb.com/
VIRUSTOTAL_API_KEY = ""  # https://www.virustotal.com/
SHODAN_API_KEY = ""  # https://shodan.io/

TIMEOUT = 12


from .ip_exposure import _layer_asn as _layer_asn
from .ip_exposure import _layer_certs as _layer_certs
from .ip_exposure import _layer_passive_dns as _layer_passive_dns
from .ip_exposure import _layer_ports as _layer_ports
from .ip_geolocation import _layer_geo as _layer_geo
from .ip_geolocation import _layer_ipapi as _layer_ipapi
from .ip_geolocation import _layer_rdns as _layer_rdns
from .ip_http import _layer_http_banner as _layer_http_banner
from .ip_http import _layer_subnet_hint as _layer_subnet_hint
from .ip_reputation import _layer_globalping as _layer_globalping
from .ip_reputation import _layer_reputation as _layer_reputation
from .ip_runtime import _is_private, _safe_get


def get_ip(data=None):
    """
    Multi-layer IP intelligence:
      L1   Geolocation & IP type
      L1.5 Security & Context
      L2   Reverse DNS / PTR
      L3   ASN & BGP context
      L4   Open ports & CVEs
      L5   TLS certs & SAN domains
      L6   Passive DNS
      L7   Reputation / threat intel
      L8   HTTP banner grab
      L9   Subnet /24 hints
      L10  Globalping Connectivity

    GUI: get_ip({"ip": "1.2.3.4"})
    CLI: get_ip()
    """
    if data:
        ip_input = data.get("ip", "").strip()
    else:
        ip_input = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]"
            f"{Color.DARK_RED}Enter IP address or domain: {Color.RESET}"
        ).strip()

    if not ip_input:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No input provided.")
        return

    try:
        ip = socket.gethostbyname(ip_input)
        if ip != ip_input:
            print(
                f"\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]"
                f"{Color.LIGHT_BLUE} Resolved {Color.WHITE}{ip_input}{Color.LIGHT_BLUE} → {Color.WHITE}{ip}{Color.RESET}"
            )
    except socket.gaierror:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not resolve: {ip_input}")
        return

    if _is_private(ip):
        print(
            f"\n{Color.YELLOW}[!] {ip} is a private/loopback address - external lookups will be skipped.{Color.RESET}"
        )
        _layer_rdns(ip)
        return

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]"
        f"{Color.LIGHT_BLUE} Starting multi-layer intelligence for "
        f"{Color.WHITE}{ip}{Color.RESET}\n"
    )

    geo_info = _layer_geo(ip)
    _layer_ipapi(ip)
    rdns = _layer_rdns(ip)
    _layer_asn(ip, geo_info)

    port_data: dict = {}
    r_ports, _ = _safe_get(f"https://internetdb.shodan.io/{ip}")
    if r_ports:
        try:
            port_data = r_ports.json()
        except ValueError:
            pass
    open_ports = port_data.get("ports", [])
    _layer_ports(ip)

    _layer_certs(ip, rdns)
    _layer_passive_dns(ip)
    _layer_reputation(ip)
    _layer_http_banner(ip, open_ports)
    _layer_subnet_hint(ip)
    _layer_globalping(ip)

    print(f"\n{Color.DARK_RED}╔{'═' * 44}╗")
    print(f"{Color.DARK_RED}║{Color.LIGHT_RED}  OSINT Graph - expand these pivot points:{' ' * 4}{Color.DARK_RED}║")
    print(f"{Color.DARK_RED}╠{'═' * 44}╣")
    hints = [
        "PTR hostname → naming pattern → sibling hosts",
        "ASN prefix list → all IPs of same org",
        "Cert SAN domains → new IPs via DNS resolve",
        "Passive DNS domains → historical infra",
        "AbuseIPDB reports → botnet/campaign peers",
        "Shodan CPE/banner → tech stack CVEs",
        "HTTP banner → domain in server header",
        "GitHub search for the IP in configs/logs",
        "Wayback Machine on domains found above",
        'Google: "' + ip + '" in:logs OR in:config',
    ]
    for h in hints:
        print(f"{Color.DARK_RED}║  {Color.WHITE}→ {h[:40]:<40}{Color.DARK_RED}║")
    print(f"{Color.DARK_RED}╚{'═' * 44}╝{Color.RESET}\n")
