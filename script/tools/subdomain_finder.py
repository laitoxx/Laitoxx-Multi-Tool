import requests
import json
from urllib.parse import urlparse
from ..shared_utils import Color


def find_subdomains():
    """
    Finds subdomains of a given domain using the crt.sh API.
    """
    domain = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Enter the target domain (e.g., example.com): {Color.RESET}").strip()

    if not domain:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No domain entered.")
        return

    # Remove scheme if present
    parsed_domain = urlparse(domain)
    if parsed_domain.netloc:
        domain = parsed_domain.netloc

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Searching for subdomains of {domain} using crt.sh...")

    url = f"https://crt.sh/?q=%.{domain}&output=json"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        # The response is a stream of JSON objects, one per line
        subdomains = set()
        for line in response.text.strip().split('\n'):
            try:
                data = json.loads(line)
                # Add the common name to our set of subdomains
                subdomains.add(data['common_name'])
            except (json.JSONDecodeError, KeyError):
                continue  # Ignore lines that are not valid JSON or don't have the required key

        if not subdomains:
            print(
                f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No subdomains found for {domain}.")
            return

        print(
            f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Found {len(subdomains)} unique subdomains:")

        sorted_subdomains = sorted(list(subdomains))
        for sub in sorted_subdomains:
            print(f"  {Color.DARK_GRAY}-{Color.WHITE} {sub}")

        # Save to file option
        save_to_file = input(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Do you want to save the list to a file? (y/n) [default: y]: {Color.RESET}").strip().lower()

        if save_to_file != 'n':
            filename = f"{domain}_subdomains.txt"
            with open(filename, 'w') as f:
                f.write("\n".join(sorted_subdomains))
            print(
                f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Subdomain list saved to {filename}")

    except requests.exceptions.Timeout:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} The request to crt.sh timed out.")
    except requests.exceptions.RequestException as e:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An error occurred: {e}")
