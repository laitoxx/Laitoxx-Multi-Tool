from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.utilities.shared_utils import Color

_SESSION = get_session()
ABUSEIPDB_API_KEY = ""  # https://www.abuseipdb.com/
VIRUSTOTAL_API_KEY = ""  # https://www.virustotal.com/
SHODAN_API_KEY = ""  # https://shodan.io/

TIMEOUT = 12
from .ip_runtime import _end, _err, _row, _safe_get, _section, _warn


def _layer_asn(ip: str, geo_info: dict):
    _section("L3 · ASN & BGP context")

    conn = geo_info.get("connection", {})
    asn_raw = conn.get("asn") or geo_info.get("asn")
    org = conn.get("org") or geo_info.get("org") or ""

    if asn_raw:
        asn_num = str(asn_raw).replace("AS", "").strip()
        _row("ASN", f"AS{asn_num}")
        _row("Org/Name", org)

    r, err = _safe_get(f"https://api.hackertarget.com/aslookup/?q={ip}")
    if r:
        line = r.text.strip()
        if "error" not in line.lower() and line:
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) >= 4:
                _row("Prefix", parts[1] if len(parts) > 1 else "")
                _row("Country", parts[2] if len(parts) > 2 else "")
                _row("AS Name", parts[3] if len(parts) > 3 else "")

    if asn_raw:
        asn_num = str(asn_raw).replace("AS", "").strip()
        r2, err2 = _safe_get(f"https://api.hackertarget.com/aslookup/?q=AS{asn_num}")
        if r2 and "error" not in r2.text.lower():
            prefixes = [line.strip() for line in r2.text.strip().splitlines() if line.strip()]
            total = len(prefixes)
            if total:
                _row("Total prefixes in AS", total)
                for p in prefixes[:10]:
                    print(f"{Color.DARK_RED}│   {Color.WHITE}{p}{Color.RESET}")
                if total > 10:
                    print(f"{Color.DARK_RED}│   {Color.DARK_GRAY}... and {total - 10} more{Color.RESET}")

    _end()


def _layer_ports(ip: str):
    _section("L4 · Open ports & services")

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
        r2, err2 = _safe_get(f"https://api.shodan.io/shodan/host/{ip}", params={"key": SHODAN_API_KEY})
        if r2:
            try:
                sd = r2.json()
                _row("OS (Shodan)", sd.get("os"))
                _row("Country", sd.get("country_name"))
                _row("Last update", sd.get("last_update"))
                svcs = sd.get("data", [])
                if svcs:
                    print(f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Services':<26}:{Color.RESET}")
                    for svc in svcs:
                        port = svc.get("port", "?")
                        proto = svc.get("transport", "tcp")
                        prod = svc.get("product", "")
                        ver = svc.get("version", "")
                        banner_line = f"{port}/{proto}"
                        if prod:
                            banner_line += f" - {prod} {ver}".rstrip()
                        print(f"{Color.DARK_RED}│   {Color.WHITE}{banner_line}{Color.RESET}")
            except ValueError:
                pass

    _end()


def _layer_certs(ip: str, rdns_hostname: str | None):
    _section("L5 · TLS certificates & SAN domains")

    targets = [ip]
    if rdns_hostname:
        parts = rdns_hostname.rstrip(".").split(".")
        if len(parts) >= 2:
            apex = ".".join(parts[-2:])
            targets.append(apex)

    all_domains: set[str] = set()

    for target in targets:
        r, err = _safe_get("https://crt.sh/", params={"q": target, "output": "json"})
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
        _warn("→ Each domain may resolve to different IPs - expand the graph!")
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

    domains = {line.strip() for line in text.splitlines() if line.strip()}
    _row("Hosted domains on this IP", len(domains))
    for d in sorted(domains)[:30]:
        print(f"{Color.DARK_RED}│   {Color.WHITE}{d}{Color.RESET}")
    if len(domains) > 30:
        print(f"{Color.DARK_RED}│   {Color.DARK_GRAY}... and {len(domains) - 30} more{Color.RESET}")

    interesting = [
        "admin",
        "dev",
        "stg",
        "staging",
        "test",
        "vpn",
        "mail",
        "backup",
        "api",
        "portal",
        "cdn",
        "remote",
    ]
    hits = [d for d in domains if any(kw in d.lower() for kw in interesting)]
    if hits:
        _warn("Interesting subdomains found:")
        for h in hits:
            print(f"{Color.DARK_RED}│   {Color.YELLOW}{h}{Color.RESET}")

    _end()
    return domains
