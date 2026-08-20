"""Lazy matcher for the packaged Divener unified fingerprint database."""

from __future__ import annotations

import json
import re
import socket
from functools import lru_cache
from typing import Any

from laitoxx.core.settings.paths import RESOURCES_DIR

from .models import FingerprintMatch

DATABASE_DIR = RESOURCES_DIR / "fingerprints" / "runtime_index"

PORT_SERVICES = {
    20: "ftp",
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "domain",
    67: "dhcp",
    68: "dhcp",
    69: "tftp",
    80: "http",
    110: "pop3",
    111: "rpcbind",
    123: "ntp",
    135: "msrpc",
    137: "netbios_ns",
    138: "netbios_dgm",
    139: "netbios_ssn",
    143: "imap",
    161: "snmp",
    389: "ldap",
    443: "http",
    445: "microsoft_ds",
    465: "smtp",
    500: "isakmp",
    514: "syslog",
    515: "printer",
    587: "smtp",
    631: "ipp",
    636: "ldap",
    873: "rsync",
    993: "imap",
    995: "pop3",
    1080: "socks",
    1433: "ms_sql_s",
    1521: "oracle",
    1723: "pptp",
    1883: "mqtt",
    2049: "nfs",
    2375: "docker",
    2376: "docker",
    3000: "http",
    3306: "mysql",
    3389: "ms_wbt_server",
    5432: "postgresql",
    5672: "amqp",
    5900: "vnc",
    5985: "http",
    5986: "http",
    6379: "redis",
    8080: "http",
    8443: "http",
    8888: "http",
    9200: "http",
    11211: "memcached",
    27017: "mongodb",
}
SERVICE_ALIASES = {
    "ssl": "http",
    "https": "http",
    "http.server": "http",
    "imap4": "imap",
    "ms-sql-s": "ms_sql_s",
    "ms_wbt_server": "ms_wbt_server",
    "domain": "dns",
}


def service_for_port(port: int, protocol: str = "tcp") -> str:
    if port in PORT_SERVICES:
        return PORT_SERVICES[port]
    try:
        return socket.getservbyport(port, protocol).replace("-", "_")
    except OSError:
        return "unknown"


def _safe_service_name(service: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]", "_", service.casefold().replace("-", "_"))
    return SERVICE_ALIASES.get(normalized, normalized)


@lru_cache(maxsize=128)
def _load(service: str) -> tuple[dict[str, Any], ...]:
    path = DATABASE_DIR / f"{_safe_service_name(service)}.json"
    if not path.is_file():
        return ()
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    return tuple(row for row in rows if isinstance(row, dict))


def _replace_groups(value: Any, match: re.Match[str]) -> Any:
    if not isinstance(value, str):
        return value
    for index, group in enumerate(match.groups(), 1):
        value = value.replace(f"${index}", group or "")
    return value.replace("\\/", "/")


def _match_row(row: dict[str, Any], banner: str) -> FingerprintMatch | None:
    raw_pattern = str(row.get("pattern") or "")
    match_type = str(row.get("match_type") or "regex").casefold()
    source = str(row.get("source_project") or "unknown")
    fields = dict(row.get("extracted_fields") or {})
    match: re.Match[str] | None = None
    if source.casefold() == "fingerprinthub" and ("||" in raw_pattern or "&&" in raw_pattern):
        tokens = [token for token in re.findall(r'["\']([^"\']{3,})["\']', raw_pattern) if token]
        if not tokens:
            return None
        checks = [token.casefold() in banner.casefold() for token in tokens]
        if ("&&" in raw_pattern and not all(checks)) or ("&&" not in raw_pattern and not any(checks)):
            return None
        match_type = "text"
    elif match_type == "text":
        if raw_pattern.casefold() not in banner.casefold():
            return None
    elif match_type == "regex":
        try:
            match = re.search(raw_pattern, banner)
        except (re.error, OverflowError):
            return None
        if not match:
            return None
        fields = {key: _replace_groups(value, match) for key, value in fields.items()}
    else:
        return None
    service = str(row.get("service") or "unknown")
    product = str(fields.get("product") or fields.get("service.product") or fields.get("plugin") or "")
    version = str(fields.get("version") or fields.get("service.version") or "")
    return FingerprintMatch(
        service=service,
        product=product,
        version=version,
        info=str(fields.get("info") or fields.get("service.info") or ""),
        device_type=str(fields.get("device_type") or fields.get("service.device") or ""),
        operating_system=str(fields.get("operating_system") or fields.get("os.product") or ""),
        cpes=list(fields.get("cpes") or []),
        source=source,
        confidence=0.95 if match_type == "text" else 0.9,
        pattern_type=match_type,
    )


def _generic_match(service: str, banner: str) -> FingerprintMatch | None:
    expressions = {
        "ssh": r"^SSH-[\d.]+-([^\s\r\n]+)",
        "http": r"(?im)^Server:\s*([^\s/\r\n]+)(?:/([^\s\r\n]+))?",
        "ftp": r"(?im)^220[^\r\n]*?([A-Za-z][\w.-]*FTP[\w.-]*)?(?:[/ ]([\d.]+))?",
        "smtp": r"(?im)^220[^\r\n]*?\b(Postfix|Exim|Sendmail|Microsoft ESMTP|Haraka)\b(?:[/ ]([\d.]+))?",
    }
    expression = expressions.get(_safe_service_name(service))
    if not expression:
        return None
    match = re.search(expression, banner)
    if not match:
        return None
    product = (match.group(1) or service).strip()
    version = (match.group(2) or "").strip() if len(match.groups()) > 1 else ""
    if _safe_service_name(service) == "ssh" and "_" in product:
        product, version = product.split("_", 1)
    return FingerprintMatch(
        service=service,
        product=product,
        version=version,
        source="Built-in banner parser",
        confidence=0.88,
        pattern_type="structured_banner",
    )


def fingerprint_banner(service: str, banner: str, *, limit: int = 3) -> list[FingerprintMatch]:
    if not banner:
        return []
    matches: list[FingerprintMatch] = []
    seen: set[tuple[str, str, str]] = set()
    for row in _load(service):
        matched = _match_row(row, banner)
        if not matched or not (matched.product or matched.version or matched.device_type or matched.operating_system):
            continue
        key = (matched.service.casefold(), matched.product.casefold(), matched.version.casefold())
        if key in seen:
            continue
        seen.add(key)
        matches.append(matched)
        if len(matches) >= 20:
            break
    generic = _generic_match(service, banner)
    if generic:
        matches.append(generic)
    matches.sort(key=lambda item: (bool(item.product), bool(item.version), item.confidence), reverse=True)
    return matches[:limit]
