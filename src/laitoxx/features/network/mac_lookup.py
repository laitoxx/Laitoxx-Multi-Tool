import re

import httpx
import requests

from laitoxx.features.network import AppleWLoc_pb2
from laitoxx.features.utilities.shared_utils import Color

# Shared session (respects proxy settings if available)
try:
    from laitoxx.core.settings.app_settings import settings as _app_settings
    from laitoxx.core.settings.proxy import make_session

    _SESSION = make_session(_app_settings.proxy)
except Exception:
    _SESSION = requests.Session()


def format_bssid(bssid):
    return ":".join(e.rjust(2, "0") for e in bssid.split(":"))


def query_apple_wloc(bssid):
    try:
        apple_wloc = AppleWLoc_pb2.AppleWLoc()
        wifi_device = apple_wloc.wifi_devices.add()
        wifi_device.bssid = bssid
        apple_wloc.unknown_value1 = 0
        apple_wloc.return_single_result = 0
        serialized = apple_wloc.SerializeToString()

        headers = {"User-Agent": "locationd/1753.17 CFNetwork/889.9 Darwin/17.2.0"}
        data = (
            b"\x00\x01\x00\x05"
            + b"en_US"
            + b"\x00\x13"
            + b"com.apple.locationd"
            + b"\x00\x0a"
            + b"8.1.12B411"
            + b"\x00\x00\x00\x01\x00\x00\x00"
            + bytes((len(serialized),))
            + serialized
        )

        with httpx.Client(http2=True, verify=False) as client:
            r = client.post(
                "https://gs-loc.apple.com/clls/wloc", headers=headers, content=data
            )

        res = AppleWLoc_pb2.AppleWLoc()
        res.ParseFromString(r.content[10:])

        device_locations = {}
        for wifi_device in res.wifi_devices:
            if wifi_device.HasField("location"):
                lat = wifi_device.location.latitude * 1e-8
                lon = wifi_device.location.longitude * 1e-8
                mac = format_bssid(wifi_device.bssid)
                if lat != -180.0 and lon != -180.0:
                    device_locations[mac] = (lat, lon)
        return device_locations
    except Exception:
        return None


def is_valid_mac_address(mac: str) -> bool:
    """
    Validates a MAC address format (e.g., 00:1A:2B:3C:4D:5E or 00-1A-2B-3C-4D-5E).
    """
    pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
    return pattern.match(mac) is not None


def search_mac_address(cli_input=None):
    """
    Searches for the manufacturer of a given MAC address using an API and locates it via Apple WPS.
    """
    if cli_input and isinstance(cli_input, dict) and "mac" in cli_input:
        mac_address = cli_input["mac"]
    elif cli_input and isinstance(cli_input, str):
        mac_address = cli_input.strip()
    else:
        mac_address = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the MAC address to search: {Color.RESET}"
        ).strip()

    if not is_valid_mac_address(mac_address):
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid MAC address format. Please use format like XX:XX:XX:XX:XX:XX."
        )
        return

    url = f"https://api.macvendors.com/{mac_address}"

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Looking up MAC address: {mac_address}..."
    )

    try:
        response = _SESSION.get(url, timeout=10)

        if response.status_code == 200:
            manufacturer = response.text
            print(
                f"\n{Color.DARK_GRAY}┌─[ {Color.WHITE}MAC Information{Color.DARK_GRAY} ]"
            )
            print(
                f"{Color.DARK_GRAY}│ {Color.WHITE}MAC Address: {Color.LIGHT_BLUE}{mac_address}"
            )
            print(
                f"{Color.DARK_GRAY}│ {Color.WHITE}Manufacturer: {Color.LIGHT_PURPLE}{manufacturer}"
            )
            print(
                f"{Color.DARK_GRAY}└───────────────────────────────────────────────────"
            )
        elif response.status_code == 404:
            print(
                f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No information found for MAC address: {mac_address}"
            )
        else:
            print(
                f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error: Received status code {response.status_code}"
            )

    except requests.exceptions.Timeout:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} The request timed out. The API might be down or your connection is slow."
        )
    except requests.exceptions.RequestException as e:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An error occurred while fetching data: {e}"
        )

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Querying Apple Location Services for {mac_address}..."
    )
    import urllib3

    urllib3.disable_warnings()
    import os

    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
    locations = query_apple_wloc(mac_address)

    if locations is None:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to query Apple WPS."
        )
    elif mac_address.lower() in [m.lower() for m in locations.keys()]:
        target_loc = None
        for k, v in locations.items():
            if k.lower() == mac_address.lower():
                target_loc = v
                break
        print(
            f"\n{Color.DARK_GRAY}┌─[ {Color.WHITE}Apple WPS Location{Color.DARK_GRAY} ]"
        )
        print(
            f"{Color.DARK_GRAY}│ {Color.WHITE}Latitude: {Color.LIGHT_PURPLE}{target_loc[0]}"
        )
        print(
            f"{Color.DARK_GRAY}│ {Color.WHITE}Longitude: {Color.LIGHT_PURPLE}{target_loc[1]}"
        )
        print(
            f"{Color.DARK_GRAY}│ {Color.WHITE}Nearby Routers: {Color.LIGHT_PURPLE}{len(locations) - 1}"
        )
        print(f"{Color.DARK_GRAY}└───────────────────────────────────────────────────")

        import json

        dump = json.dumps(
            [{"mac": k, "lat": v[0], "lon": v[1]} for k, v in locations.items()]
        )
        print(f"APPLE_WLOC_DATA:{dump}")
    else:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} MAC Address {mac_address} not found in Apple Location Services."
        )
