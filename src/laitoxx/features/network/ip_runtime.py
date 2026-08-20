import ipaddress

import requests

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.utilities.shared_utils import Color

_SESSION = get_session()
ABUSEIPDB_API_KEY = ""  # https://www.abuseipdb.com/
VIRUSTOTAL_API_KEY = ""  # https://www.virustotal.com/
SHODAN_API_KEY = ""  # https://shodan.io/

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
