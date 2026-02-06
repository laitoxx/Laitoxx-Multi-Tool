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

import re

import requests

from ..shared_utils import Color


def is_valid_mac_address(mac: str) -> bool:
    pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return pattern.match(mac) is not None


def search_mac_address() -> bool:
    mac_address: str = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the MAC address to search: {Color.RESET}").strip()

    if not is_valid_mac_address(mac_address):
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid MAC address format. Please use format like XX:XX:XX:XX:XX:XX.")
        return

    url: str = f"https://api.macvendors.com/{mac_address}"

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Looking up MAC address: {mac_address}...")

    try:
        response: requests.Response = requests.get(url, timeout=10)

        if response.status_code == 200:
            manufacturer: str = response.text
            print(
                f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Manufacturer found:")
            print(
                f"{Color.DARK_GRAY}  - {Color.WHITE}MAC Address: {Color.LIGHT_BLUE}{mac_address}")
            print(
                f"{Color.DARK_GRAY}  - {Color.WHITE}Manufacturer: {Color.LIGHT_PURPLE}{manufacturer}")
        elif response.status_code == 404:
            print(
                f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No information found for MAC address: {mac_address}")
        else:
            print(
                f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error: Received status code {response.status_code}")

    except requests.exceptions.Timeout:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} The request timed out. The API might be down or your connection is slow.")
    except requests.exceptions.RequestException as e:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An error occurred while fetching data: {e}")
    
    return True
