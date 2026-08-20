"""HTTP session and console presentation helpers for web audits."""

import aiohttp

from laitoxx.core.settings.network_manager import make_aiohttp_connector
from laitoxx.features.utilities.shared_utils import Color

_TIMEOUT = aiohttp.ClientTimeout(total=30)

_UA = "Mozilla/5.0 (Web-Security-Checker)"


def _make_session() -> aiohttp.ClientSession:
    connector = make_aiohttp_connector()
    return aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
    )


def _ensure_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _section(title: str, width: int = 38):
    pad = "─" * (width - len(title))
    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{title} {Color.DARK_RED}]{pad}")


def _ok(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {msg}")


def _warn(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.YELLOW}!{Color.DARK_GRAY}]{Color.YELLOW} {msg}")


def _fail(msg: str):
    print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} {msg}")


def _row(label: str, value: str, color=None):
    c = color or Color.WHITE
    print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}{label:<28}{c}{value}")
