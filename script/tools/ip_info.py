"""
 @@@  @@@  @@@@@@  @@@@@@@ @@@@@@@  @@@@@@@  @@@ @@@@@@@@ @@@ @@@
 @@!  @@@ @@!  @@@   @@!   @@!  @@@ @@!  @@@ @@! @@!      @@! !@@
 @!@!@!@! @!@  !@!   @!!   @!@  !@! @!@!!@!  !!@ @!!!:!    !@!@! 
 !!:  !!! !!:  !!!   !!:   !!:  !!! !!: :!!  !!: !!:        !!:  
  :   : :  : :. :     :    :: :  :   :   : : :    :         .:   
                                                                 
    HOTDRIFY cooked with the refactor for the LAITOXX squad.
                    github.com/hotdrify
                      t.me/hotdrify

                    github.com/laitoxx
                      t.me/laitoxx
"""

import socket

import requests

from ..shared_utils import Color


def get_ip():
    """
    Retrieves and displays information about an IP address or domain.
    """
    ip_input = input(
        f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter IP address or domain: {Color.RESET}')
    if ip_input is None:
        return
    ip_input = ip_input.strip()

    if not ip_input:
        print(
            f'{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}No input provided.')
        return

    # Resolve domain to IP if necessary
    try:
        ip = socket.gethostbyname(ip_input)
        print(
            f'\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Resolved {ip_input} to {ip}')
    except socket.gaierror:
        print(
            f'{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}Could not resolve host: {ip_input}')
        return

    print(
        f'{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Fetching information for {ip}...')

    try:
        response = requests.get(f"http://ipwho.is/{ip}", timeout=10)
        response.raise_for_status()
        info = response.json()

        if not info.get("success"):
            message = info.get("message", "An unknown error occurred.")
            print(
                f'\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} API Error: {message}')
            return

        # Map of keys to display labels for cleaner output
        display_map = {
            "ip": "IP Address", "type": "Type",
            "continent": "Continent", "country": "Country",
            "region": "Region", "city": "City",
            "latitude": "Latitude", "longitude": "Longitude",
            "postal": "Postal Code", "capital": "Capital",
            "asn": "ASN", "org": "Organization (ISP)",
            "isp": "ISP",
        }

        print(
            f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Information for {ip} {Color.DARK_RED}]─" + '─' * 15)
        for key, label in display_map.items():
            value = info.get(key)
            if value:
                print(
                    f"{Color.DARK_RED}│ {Color.LIGHT_RED}{label:<20}: {Color.WHITE}{value}")

        # Connection info is nested
        connection = info.get("connection", {})
        if connection:
            print(
                f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Connection ASN':<20}: {Color.WHITE}{connection.get('asn')}")
            print(
                f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Connection ORG':<20}: {Color.WHITE}{connection.get('org')}")
            print(
                f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Connection ISP':<20}: {Color.WHITE}{connection.get('isp')}")
            print(
                f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Connection Domain':<20}: {Color.WHITE}{connection.get('domain')}")

        print(f"{Color.DARK_RED}└" + '─' * (35 + len(ip)))

    except requests.exceptions.Timeout:
        print(
            f'\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}The request to ipwho.is timed out.')
    except requests.exceptions.RequestException as e:
        print(
            f'\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}An error occurred: {e}')
    except ValueError:  # JSONDecodeError
        print(
            f'\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}Could not decode the response from the API.')
