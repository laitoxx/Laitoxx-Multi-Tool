"""GreyNoise community reputation provider."""

from __future__ import annotations

import ipaddress
from urllib.parse import quote

from .. import provider_common as _common
from ..configuration import credential
from ..models import ProviderResult

_cached_json = _common._cached_json
_run = _common._run
_status_data = _common._status_data


def greynoise(ip: str) -> ProviderResult:
    address = ipaddress.ip_address(ip)
    if address.version != 4 or not address.is_global:
        return ProviderResult(
            "GreyNoise Community",
            "no_data",
            error="GreyNoise Community accepts only valid routable IPv4 addresses",
        )
    key = credential("greynoise")
    headers = {"key": key} if key else {}
    return _run(
        "GreyNoise Community",
        lambda: ProviderResult(
            "GreyNoise Community",
            *(
                _status_data(
                    _cached_json(
                        "greynoise",
                        ip,
                        f"https://api.greynoise.io/v3/community/{quote(ip)}",
                        headers=headers,
                        ttl=10800,
                    )
                )
            ),
        ),
    )
