import requests

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.utilities.shared_utils import Color

_SESSION = get_session()
ABUSEIPDB_API_KEY = ""  # https://www.abuseipdb.com/
VIRUSTOTAL_API_KEY = ""  # https://www.virustotal.com/
SHODAN_API_KEY = ""  # https://shodan.io/

TIMEOUT = 12
from .ip_runtime import _end, _err, _row, _safe_get, _section, _warn


def _layer_reputation(ip: str):
    _section("L7 · Reputation & threat intelligence")

    r_gn, _ = _safe_get(f"https://api.greynoise.io/v3/community/{ip}")
    if r_gn:
        try:
            gn = r_gn.json()
            noise = gn.get("noise", False)
            riot = gn.get("riot", False)
            classif = gn.get("classification", "unknown")
            name = gn.get("name", "")
            msg = gn.get("message", "")
            if noise or riot:
                color = Color.RED if classif == "malicious" else Color.YELLOW
                _row(
                    "GreyNoise",
                    f"noise={noise} riot={riot} class={classif} name={name}",
                    color=color,
                )
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
            params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""},
        )
        if r_ab:
            try:
                ab = r_ab.json().get("data", {})
                score = ab.get("abuseConfidenceScore", 0)
                total = ab.get("totalReports", 0)
                domain = ab.get("domain", "")
                usage = ab.get("usageType", "")
                last = ab.get("lastReportedAt", "")
                color = Color.RED if score > 50 else (Color.YELLOW if score > 0 else Color.LIGHT_GREEN)
                _row(
                    "AbuseIPDB score",
                    f"{score}/100  (reports: {total}, last: {last})",
                    color=color,
                )
                _row("Usage type", usage)
                _row("Abuse domain", domain)

                reports = ab.get("reports", [])[:5]
                if reports:
                    _warn("Recent abuse reports (last 5):")
                    for rep in reports:
                        cats = rep.get("categories", [])
                        dt = rep.get("reportedAt", "")[:10]
                        com = rep.get("comment", "")[:80]
                        print(f"{Color.DARK_RED}│   {Color.YELLOW}{dt} cats={cats} {Color.DARK_GRAY}{com}{Color.RESET}")
            except ValueError:
                pass

    if VIRUSTOTAL_API_KEY:
        r_vt, err_vt = _safe_get(
            f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
            headers={"x-apikey": VIRUSTOTAL_API_KEY},
        )
        if r_vt:
            try:
                vt = r_vt.json().get("data", {}).get("attributes", {})
                stats = vt.get("last_analysis_stats", {})
                mal = stats.get("malicious", 0)
                sus = stats.get("suspicious", 0)
                harm = stats.get("harmless", 0)
                color = Color.RED if mal > 0 else (Color.YELLOW if sus > 0 else Color.LIGHT_GREEN)
                _row(
                    "VirusTotal",
                    f"malicious={mal} suspicious={sus} harmless={harm}",
                    color=color,
                )
                cert = vt.get("last_https_certificate", {})
                sans = cert.get("extensions", {}).get("subject_alternative_name", [])
                if sans:
                    _row("VT cert SANs", ", ".join(sans[:10]))
            except ValueError:
                pass

    _end()


def _layer_globalping(ip: str):
    import time

    _section("L10 · Globalping Connectivity")
    try:
        post_data = {"target": ip, "type": "ping", "limit": 4}
        try:
            r = _SESSION.post(
                "https://api.globalping.io/v1/measurements",
                json=post_data,
                timeout=TIMEOUT,
            )
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            _err(f"Globalping failed to create measurement: {e}")
            _end()
            return

        m_id = r.json().get("id")
        if not m_id:
            _err("Failed to get measurement ID from Globalping")
            _end()
            return

        _row("Status", "Probing from 4 global locations... (eta 5-10s)")

        for _ in range(10):
            time.sleep(1.5)
            res, err = _safe_get(f"https://api.globalping.io/v1/measurements/{m_id}")
            if err or res is None:
                continue

            data = res.json()
            if data.get("status") in ["finished", "failed"]:
                results = data.get("results", [])
                if not results:
                    _err("No results returned")
                else:
                    print(
                        f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Location (Network)':<26}: {Color.WHITE}Avg Ping  [ Min / Max ]  Loss{Color.RESET}"
                    )
                    for res in results:
                        probe = res.get("probe", {})
                        loc = f"{probe.get('city', '')}, {probe.get('country', '')} ({probe.get('network', '')})"
                        stats = res.get("result", {}).get("stats", {})
                        if res.get("result", {}).get("status") == "failed":
                            print(f"{Color.DARK_RED}│ {Color.WHITE}{loc[:26]:<26}: {Color.RED}FAILED{Color.RESET}")
                            continue

                        avg = stats.get("avg", 0)
                        mn = stats.get("min", 0)
                        mx = stats.get("max", 0)
                        loss = stats.get("loss", 0)

                        color = Color.LIGHT_GREEN if loss == 0 else Color.YELLOW if loss < 100 else Color.RED
                        ping_str = f"{avg}ms  [ {mn} / {mx} ]  {loss}% loss"
                        print(f"{Color.DARK_RED}│ {Color.WHITE}{loc[:26]:<26}: {color}{ping_str}{Color.RESET}")
                break
    except Exception as e:
        _err(f"Globalping failed: {e}")
    finally:
        _end()
