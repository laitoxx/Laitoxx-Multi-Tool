import whois
from ..shared_utils import Color


def get_website_info():
    """
    Retrieves and displays WHOIS information for a given domain.
    """
    domain = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the website domain: {Color.RESET}")
    if domain is None:
        return
    domain = domain.strip()

    if not domain:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} No domain entered.")
        return

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Retrieving WHOIS information for {domain}...")

    try:
        domain_info = whois.whois(domain)

        if not domain_info.domain_name:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Could not retrieve WHOIS information. The domain may be incorrect or not registered.")
            return

        # A dictionary to hold the information for cleaner printing
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
            "Country": domain_info.country
        }

        print(
            f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}WHOIS Information for {domain} {Color.DARK_RED}]─" + '─' * 10)
        for label, value in info_map.items():
            if value:
                # Handle list values (like name_servers)
                if isinstance(value, list):
                    value_str = ", ".join(map(str, value))
                else:
                    value_str = str(value).replace('\n', ', ')
                print(
                    f"{Color.DARK_RED}│ {Color.LIGHT_RED}{label:<20}: {Color.WHITE}{value_str}")
        print(f"{Color.DARK_RED}└" + '─' * (45 + len(domain)))

    except whois.parser.PywhoisError as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Error: {e}")
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} An unexpected error occurred: {e}")
