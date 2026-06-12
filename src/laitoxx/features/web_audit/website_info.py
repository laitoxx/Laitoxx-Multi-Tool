import whois
import requests
import time
from laitoxx.features.utilities.shared_utils import Color


def get_website_info():
    """
    Retrieves and displays WHOIS information for a given domain.
    """
    domain = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the website domain: {Color.RESET}"
    )
    if domain is None:
        return
    domain = domain.strip()

    if not domain:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} No domain entered."
        )
        return

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Retrieving WHOIS information for {domain}..."
    )

    try:
        domain_info = whois.whois(domain)

        if not domain_info.domain_name:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Could not retrieve WHOIS information. The domain may be incorrect or not registered."
            )
            return

        info_map = {
            "Domain": domain_info.domain_name,
            "Registrar": domain_info.registrar,
            "Creation Date": domain_info.creation_date,
            "Expiration Date": domain_info.expiration_date,
            "Last Updated": domain_info.updated_date,
            "Name Servers": domain_info.name_servers,
            "Status": domain_info.status,
            "Registrant Name": domain_info.name,
            "Organization": domain_info.org,
            "Address": domain_info.address,
            "City": domain_info.city,
            "State": domain_info.state,
            "Postal Code": domain_info.zipcode,
            "Country": domain_info.country,
        }

        print(
            f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}WHOIS Information for {domain} {Color.DARK_RED}]─"
            + "─" * 10
        )
        for label, value in info_map.items():
            if value:
                if isinstance(value, list):
                    value_str = ", ".join(map(str, value))
                else:
                    value_str = str(value).replace("\n", ", ")
                print(
                    f"{Color.DARK_RED}│ {Color.LIGHT_RED}{label:<20}: {Color.WHITE}{value_str}"
                )
        print(f"{Color.DARK_RED}└" + "─" * (45 + len(domain)))

        # Globalping Check
        print(
            f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Globalping Connectivity {Color.DARK_RED}]─"
            + "─" * 20
        )
        try:
            post_data = {"target": domain, "type": "ping", "limit": 4}
            r = requests.post(
                "https://api.globalping.io/v1/measurements", json=post_data, timeout=10
            )
            r.raise_for_status()
            m_id = r.json().get("id")
            if not m_id:
                print(f"{Color.DARK_RED}│ {Color.RED}Failed to get measurement ID")
            else:
                print(
                    f"{Color.DARK_RED}│ {Color.WHITE}Probing from 4 global locations... (eta 5-10s)"
                )
                for _ in range(10):
                    time.sleep(1.5)
                    res = requests.get(
                        f"https://api.globalping.io/v1/measurements/{m_id}", timeout=10
                    )
                    data = res.json()
                    if data.get("status") in ["finished", "failed"]:
                        results = data.get("results", [])
                        if not results:
                            print(f"{Color.DARK_RED}│ {Color.RED}No results returned")
                        else:
                            print(
                                f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Location (Network)':<30}: {Color.WHITE}Avg Ping  [ Min / Max ]  Loss{Color.RESET}"
                            )
                            for res in results:
                                probe = res.get("probe", {})
                                loc = f"{probe.get('city', '')}, {probe.get('country', '')} ({probe.get('network', '')})"
                                stats = res.get("result", {}).get("stats", {})
                                if res.get("result", {}).get("status") == "failed":
                                    print(
                                        f"{Color.DARK_RED}│ {Color.WHITE}{loc[:30]:<30}: {Color.RED}FAILED{Color.RESET}"
                                    )
                                    continue

                                avg = stats.get("avg", 0)
                                mn = stats.get("min", 0)
                                mx = stats.get("max", 0)
                                loss = stats.get("loss", 0)

                                color = (
                                    Color.LIGHT_GREEN
                                    if loss == 0
                                    else Color.YELLOW
                                    if loss < 100
                                    else Color.RED
                                )
                                ping_str = f"{avg}ms  [ {mn} / {mx} ]  {loss}% loss"
                                print(
                                    f"{Color.DARK_RED}│ {Color.WHITE}{loc[:30]:<30}: {color}{ping_str}{Color.RESET}"
                                )
                        break
        except Exception as e:
            print(f"{Color.DARK_RED}│ {Color.RED}Globalping failed: {e}")
        finally:
            print(f"{Color.DARK_RED}└" + "─" * 46)

    except whois.parser.PywhoisError as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Error: {e}"
        )
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} An unexpected error occurred: {e}"
        )
