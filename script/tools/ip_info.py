import socket
import ipaddress
import concurrent.futures
import json
import re

import requests

from ..shared_utils import Color

try:
    from settings.proxy import make_session
    from settings.app_settings import settings as _app_settings
    _SESSION = make_session(_app_settings.proxy)
except Exception:
    _SESSION = requests.Session()
ABUSEIPDB_API_KEY  = ""   # https://www.abuseipdb.com/
VIRUSTOTAL_API_KEY = ""   # https://www.virustotal.com/
SHODAN_API_KEY     = ""   # https://shodan.io/

TIMEOUT = 12


def _section(title: str):
    bar = "─" * (40 - len(title))
    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{title} {Color.DARK_RED}]{bar}")


def _row(label: str, value, color=None):
    if value is None or value == "" or value == [] or value == {}:
        return
    c = color or Color.WHITE
    print(f"{Color.DARK_RED}│ {Color.LIGHT_RED}{label:<26}: {c}{value}{Color.RESET}")


def _ok(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {msg}{Color.RESET}")


def _warn(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.YELLOW}!{Color.DARK_GRAY}]{Color.YELLOW} {msg}{Color.RESET}")


def _err(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} {msg}{Color.RESET}")


def _end():
    print(f"{Color.DARK_RED}└{'─' * 44}{Color.RESET}")


def _safe_get(url: str, headers=None, params=None):
    try:
        r = _SESSION.get(url, headers=headers, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r, None
    except requests.exceptions.Timeout:
        return None, "request timed out"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {e.response.status_code}"
    except requests.exceptions.RequestException as e:
        return None, str(e)


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


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

    _row("IP",           info.get("ip"))
    _row("Type",         info.get("type"))           # IPv4 / IPv6
    _row("Continent",    info.get("continent"))
    _row("Country",      f"{info.get('country')} ({info.get('country_code')})")
    _row("Region",       info.get("region"))
    _row("City",         info.get("city"))
    _row("Latitude",     info.get("latitude"))
    _row("Longitude",    info.get("longitude"))
    _row("Postal Code",  info.get("postal"))
    _row("Timezone",     info.get("timezone", {}).get("id") if isinstance(info.get("timezone"), dict) else info.get("timezone"))

    conn = info.get("connection", {})
    _row("ASN",          conn.get("asn") or info.get("asn"))
    _row("Organization", conn.get("org") or info.get("org"))
    _row("ISP",          conn.get("isp") or info.get("isp"))
    _row("Domain",       conn.get("domain"))

    _end()
    return info


def _layer_rdns(ip: str):
    _section("L2 · Reverse DNS (PTR)")
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        _ok(hostname)
        keywords = ["mail", "smtp", "vpn", "gw", "gateway", "proxy",
                    "db", "database", "backup", "dev", "stg", "staging",
                    "printer", "cam", "router", "fw", "firewall", "nas",
                    "store", "cdn", "api", "admin"]
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


def _layer_asn(ip: str, geo_info: dict):
    _section("L3 · ASN & BGP context")

    conn = geo_info.get("connection", {})
    asn_raw = conn.get("asn") or geo_info.get("asn")
    org = conn.get("org") or geo_info.get("org") or ""

    if asn_raw:
        asn_num = str(asn_raw).replace("AS", "").strip()
        _row("ASN",      f"AS{asn_num}")
        _row("Org/Name", org)

    r, err = _safe_get(f"https://api.hackertarget.com/aslookup/?q={ip}")
    if r:
        line = r.text.strip()
        if "error" not in line.lower() and line:
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) >= 4:
                _row("Prefix",    parts[1] if len(parts) > 1 else "")
                _row("Country",   parts[2] if len(parts) > 2 else "")
                _row("AS Name",   parts[3] if len(parts) > 3 else "")

    if asn_raw:
        asn_num = str(asn_raw).replace("AS", "").strip()
        r2, err2 = _safe_get(f"https://api.hackertarget.com/aslookup/?q=AS{asn_num}")
        if r2 and "error" not in r2.text.lower():
            prefixes = [l.strip() for l in r2.text.strip().splitlines() if l.strip()]
            total = len(prefixes)
            if total:
                _row("Total prefixes in AS", total)
                for p in prefixes[:10]:
                    print(f"{Color.DARK_RED}│   {Color.WHITE}{p}{Color.RESET}")
                if total > 10:
                    print(f"{Color.DARK_RED}│   {Color.DARK_GRAY}... and {total - 10} more{Color.RESET}")

    _end()


def _layer_ports(ip: str):
    _section("L4 · Open ports & services (Shodan InternetDB)")

    r, err = _safe_get(f"https://internetdb.shodan.io/{ip}")
    if err or r is None:
        _err(f"Shodan InternetDB failed: {err}")
        _end()
        return

    try:
        data = r.json()
    except ValueError:
        _err("Could not parse Shodan InternetDB response")
        _end()
        return

    if data.get("detail") == "No information available":
        _warn("No data in Shodan InternetDB for this IP")
        _end()
        return

    ports = data.get("ports", [])
    _row("Open ports", ", ".join(str(p) for p in ports) if ports else "none")

    hostnames = data.get("hostnames", [])
    if hostnames:
        _row("Shodan hostnames", ", ".join(hostnames))

    cpes = data.get("cpes", [])
    if cpes:
        _row("CPEs (tech fingerprint)", "")
        for c in cpes:
            print(f"{Color.DARK_RED}│   {Color.WHITE}{c}{Color.RESET}")

    tags = data.get("tags", [])
    if tags:
        tag_color = Color.RED if any(t in tags for t in ["malware", "compromised", "c2"]) else Color.YELLOW
        _row("Tags", ", ".join(tags), color=tag_color)

    vulns = data.get("vulns", [])
    if vulns:
        _row("Known CVEs", "", color=Color.RED)
        for v in vulns:
            print(f"{Color.DARK_RED}│   {Color.RED}{v}{Color.RESET}")

    if SHODAN_API_KEY:
        r2, err2 = _safe_get(
            f"https://api.shodan.io/shodan/host/{ip}",
            params={"key": SHODAN_API_KEY}
        )
        if r2:
            try:
                sd = r2.json()
                _row("OS (Shodan)",    sd.get("os"))
                _row("Country",        sd.get("country_name"))
                _row("Last update",    sd.get("last_update"))
                svcs = sd.get("data", [])
                if svcs:
                    print(f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Services':<26}:{Color.RESET}")
                    for svc in svcs:
                        port  = svc.get("port", "?")
                        proto = svc.get("transport", "tcp")
                        prod  = svc.get("product", "")
                        ver   = svc.get("version", "")
                        banner_line = f"{port}/{proto}"
                        if prod:
                            banner_line += f" — {prod} {ver}".rstrip()
                        print(f"{Color.DARK_RED}│   {Color.WHITE}{banner_line}{Color.RESET}")
            except ValueError:
                pass

    _end()


def _layer_certs(ip: str, rdns_hostname: str | None):
    _section("L5 · TLS certificates & SAN domains (crt.sh)")

    targets = [ip]
    if rdns_hostname:
        parts = rdns_hostname.rstrip(".").split(".")
        if len(parts) >= 2:
            apex = ".".join(parts[-2:])
            targets.append(apex)

    all_domains: set[str] = set()

    for target in targets:
        r, err = _safe_get(
            "https://crt.sh/",
            params={"q": target, "output": "json"}
        )
        if err or r is None:
            continue
        try:
            entries = r.json()
        except ValueError:
            continue
        for entry in entries:
            name = entry.get("name_value", "")
            for d in name.splitlines():
                d = d.strip().lstrip("*.")
                if d:
                    all_domains.add(d)

    if all_domains:
        sorted_domains = sorted(all_domains)
        _row("Domains found via certs", len(sorted_domains))
        for d in sorted_domains[:30]:
            print(f"{Color.DARK_RED}│   {Color.WHITE}{d}{Color.RESET}")
        if len(sorted_domains) > 30:
            print(f"{Color.DARK_RED}│   {Color.DARK_GRAY}... and {len(sorted_domains) - 30} more{Color.RESET}")
        _warn("→ Each domain may resolve to different IPs — expand the graph!")
    else:
        _warn("No certificate records found")

    _end()
    return all_domains


def _layer_passive_dns(ip: str):
    _section("L6 · Passive DNS (historical domains → IP)")

    r, err = _safe_get(f"https://api.hackertarget.com/reverseiplookup/?q={ip}")
    if err or r is None:
        _err(f"HackerTarget reverse IP failed: {err}")
        _end()
        return set()

    text = r.text.strip()
    if "error" in text.lower() or not text:
        _warn("No passive DNS data found (or API limit reached)")
        _end()
        return set()

    domains = {l.strip() for l in text.splitlines() if l.strip()}
    _row("Hosted domains on this IP", len(domains))
    for d in sorted(domains)[:30]:
        print(f"{Color.DARK_RED}│   {Color.WHITE}{d}{Color.RESET}")
    if len(domains) > 30:
        print(f"{Color.DARK_RED}│   {Color.DARK_GRAY}... and {len(domains) - 30} more{Color.RESET}")

    interesting = ["admin", "dev", "stg", "staging", "test", "vpn",
                   "mail", "backup", "api", "portal", "cdn", "remote"]
    hits = [d for d in domains if any(kw in d.lower() for kw in interesting)]
    if hits:
        _warn("Interesting subdomains found:")
        for h in hits:
            print(f"{Color.DARK_RED}│   {Color.YELLOW}{h}{Color.RESET}")

    _end()
    return domains


def _layer_reputation(ip: str):
    _section("L7 · Reputation & threat intelligence")

    r_gn, _ = _safe_get(f"https://api.greynoise.io/v3/community/{ip}")
    if r_gn:
        try:
            gn = r_gn.json()
            noise   = gn.get("noise", False)
            riot    = gn.get("riot", False)
            classif = gn.get("classification", "unknown")
            name    = gn.get("name", "")
            msg     = gn.get("message", "")
            if noise or riot:
                color = Color.RED if classif == "malicious" else Color.YELLOW
                _row("GreyNoise",
                     f"noise={noise} riot={riot} class={classif} name={name}",
                     color=color)
            elif "not found" in msg.lower() or "404" in str(r_gn.status_code):
                _row("GreyNoise", "not observed on the internet", color=Color.LIGHT_GREEN)
            else:
                _row("GreyNoise", msg or "no data")
        except ValueError:
            pass

    if ABUSEIPDB_API_KEY:
        r_ab, err_ab = _safe_get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": ABUSEIPDB_API_KEY, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""}
        )
        if r_ab:
            try:
                ab = r_ab.json().get("data", {})
                score = ab.get("abuseConfidenceScore", 0)
                total = ab.get("totalReports", 0)
                domain = ab.get("domain", "")
                usage  = ab.get("usageType", "")
                last   = ab.get("lastReportedAt", "")
                color  = Color.RED if score > 50 else (Color.YELLOW if score > 0 else Color.LIGHT_GREEN)
                _row("AbuseIPDB score", f"{score}/100  (reports: {total}, last: {last})", color=color)
                _row("Usage type",      usage)
                _row("Abuse domain",    domain)

                reports = ab.get("reports", [])[:5]
                if reports:
                    _warn("Recent abuse reports (last 5):")
                    for rep in reports:
                        cats = rep.get("categories", [])
                        dt   = rep.get("reportedAt", "")[:10]
                        com  = rep.get("comment", "")[:80]
                        print(f"{Color.DARK_RED}│   {Color.YELLOW}{dt} cats={cats} {Color.DARK_GRAY}{com}{Color.RESET}")
            except ValueError:
                pass
    else:
        _warn("AbuseIPDB: no API key set (ABUSEIPDB_API_KEY)")

    if VIRUSTOTAL_API_KEY:
        r_vt, err_vt = _safe_get(
            f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
            headers={"x-apikey": VIRUSTOTAL_API_KEY}
        )
        if r_vt:
            try:
                vt = r_vt.json().get("data", {}).get("attributes", {})
                stats = vt.get("last_analysis_stats", {})
                mal   = stats.get("malicious", 0)
                sus   = stats.get("suspicious", 0)
                harm  = stats.get("harmless", 0)
                color = Color.RED if mal > 0 else (Color.YELLOW if sus > 0 else Color.LIGHT_GREEN)
                _row("VirusTotal",
                     f"malicious={mal} suspicious={sus} harmless={harm}",
                     color=color)
                cert = vt.get("last_https_certificate", {})
                sans = cert.get("extensions", {}).get("subject_alternative_name", [])
                if sans:
                    _row("VT cert SANs", ", ".join(sans[:10]))
            except ValueError:
                pass
    else:
        _warn("VirusTotal: no API key set (VIRUSTOTAL_API_KEY)")

    _end()


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
                url, timeout=8, allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (OSINT-ip_info)"},
                verify=False
            )
            headers = r.headers
            title_match = re.search(r"<title[^>]*>(.*?)</title>", r.text[:4096], re.I | re.S)
            title = title_match.group(1).strip()[:80] if title_match else ""

            print(f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Port ' + str(port):<26}: {Color.WHITE}{r.status_code} {r.url[:70]}{Color.RESET}")
            if title:
                _row(f"  Title",        title)
            _row(f"  Server",       headers.get("Server"))
            _row(f"  X-Powered-By", headers.get("X-Powered-By"))
            _row(f"  Location",     headers.get("Location"))

            for path in ["/robots.txt", "/sitemap.xml", "/.well-known/security.txt"]:
                r2 = _SESSION.get(f"{scheme}://{ip}:{port}{path}", timeout=5,
                                   verify=False,
                                   headers={"User-Agent": "Mozilla/5.0 (OSINT-ip_info)"})
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
            _ok(f"Tip: search crt.sh for all certs issued to IPs in this range")
    except Exception:
        pass
    _end()


def get_ip(data=None):
    """
    Multi-layer IP intelligence:
      L1  Geolocation & IP type      (ipwho.is)
      L2  Reverse DNS / PTR          (socket)
      L3  ASN & BGP context          (hackertarget)
      L4  Open ports & CVEs          (Shodan InternetDB + optional full API)
      L5  TLS certs & SAN domains    (crt.sh)
      L6  Passive DNS                (hackertarget)
      L7  Reputation / threat intel  (GreyNoise, AbuseIPDB*, VirusTotal*)
      L8  HTTP banner grab           (requests)
      L9  Subnet /24 hints

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
            print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]"
                  f"{Color.LIGHT_BLUE} Resolved {Color.WHITE}{ip_input}{Color.LIGHT_BLUE} → {Color.WHITE}{ip}{Color.RESET}")
    except socket.gaierror:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not resolve: {ip_input}")
        return

    if _is_private(ip):
        print(f"\n{Color.YELLOW}[!] {ip} is a private/loopback address — external lookups will be skipped.{Color.RESET}")
        _layer_rdns(ip)
        return

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]"
          f"{Color.LIGHT_BLUE} Starting multi-layer intelligence for "
          f"{Color.WHITE}{ip}{Color.RESET}\n")

    geo_info  = _layer_geo(ip)
    rdns      = _layer_rdns(ip)
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

    print(f"\n{Color.DARK_RED}╔{'═' * 44}╗")
    print(f"{Color.DARK_RED}║{Color.LIGHT_RED}  OSINT Graph — expand these pivot points:{' ' * 4}{Color.DARK_RED}║")
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
        "Google: \"" + ip + "\" in:logs OR in:config",
    ]
    for h in hints:
        print(f"{Color.DARK_RED}║  {Color.WHITE}→ {h[:40]:<40}{Color.DARK_RED}║")
    print(f"{Color.DARK_RED}╚{'═' * 44}╝{Color.RESET}\n")
