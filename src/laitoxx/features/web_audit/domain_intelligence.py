"""Passive, structured profile used by the Domain Intelligence workspace."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from urllib.parse import quote, urlparse

from laitoxx.core.dns import query_dns
from laitoxx.core.settings.network_manager import NetworkManager, get_session
from laitoxx.core.settings.tls import trusted_ssl_context

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    re.I,
)
_DNS_TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "CAA")
_SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "cross-origin-opener-policy",
)


def normalize_domain(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Enter a domain or URL")
    host = urlparse(raw if "://" in raw else f"//{raw}").hostname or raw
    host = host.rstrip(".").casefold()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError("The international domain name is invalid") from error
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Domain Intelligence expects a domain name, not an IP address")
    if not _DOMAIN_RE.fullmatch(host) or not any(char.isalpha() for char in host.rsplit(".", 1)[-1]):
        raise ValueError(f"Invalid domain: {host}")
    return host


def _dns_profile(domain: str) -> dict:
    records: dict[str, list[str]] = {}
    queries = [(kind, domain, kind) for kind in _DNS_TYPES]
    queries += [("DMARC", f"_dmarc.{domain}", "TXT"), ("MTA-STS", f"_mta-sts.{domain}", "TXT")]
    with ThreadPoolExecutor(max_workers=8, thread_name_prefix="domain-dns") as executor:
        futures = {executor.submit(query_dns, name, kind, 5): label for label, name, kind in queries}
        for future in as_completed(futures):
            values = future.result()
            if values:
                records[futures[future]] = values
    return records


def _rdap_profile(domain: str) -> dict:
    url = f"https://rdap.org/domain/{quote(domain)}"
    headers = {"Accept": "application/rdap+json", "User-Agent": "Laitoxx-Domain-Intelligence/1.0"}
    try:
        response = get_session().get(url, timeout=8, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception:
        if NetworkManager.is_active():
            raise
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=8, context=trusted_ssl_context()) as response:  # noqa: S310
            data = json.load(response)
    return {
        "handle": data.get("handle"),
        "ldh_name": data.get("ldhName"),
        "status": data.get("status") or [],
        "port43": data.get("port43"),
        "events": {
            str(item.get("eventAction", "")): str(item.get("eventDate", ""))
            for item in data.get("events", [])
            if isinstance(item, dict)
        },
        "nameservers": sorted(
            {
                str(item.get("ldhName", "")).casefold()
                for item in data.get("nameservers", [])
                if isinstance(item, dict) and item.get("ldhName")
            }
        ),
        "entities": [
            {"roles": item.get("roles") or [], "handle": item.get("handle") or ""}
            for item in data.get("entities", [])
            if isinstance(item, dict)
        ][:20],
    }


def _http_profile(domain: str) -> dict:
    def build_result(status: int, final_url: str, response_headers, body: bytes, encoding: str = "utf-8") -> dict:
        text = body.decode(encoding or "utf-8", errors="replace")
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        headers = {key.casefold(): value for key, value in response_headers.items()}
        return {
            "status": status,
            "final_url": final_url,
            "title": re.sub(r"\s+", " ", title.group(1)).strip()[:300] if title else "",
            "server": headers.get("server", ""),
            "content_type": headers.get("content-type", ""),
            "security_headers": {name: headers[name] for name in _SECURITY_HEADERS if name in headers},
            "missing_security_headers": [name for name in _SECURITY_HEADERS if name not in headers],
        }

    last_error = ""
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            with get_session().get(
                url,
                timeout=12,
                allow_redirects=True,
                stream=True,
                headers={"User-Agent": "Laitoxx-Domain-Intelligence/1.0"},
            ) as response:
                body = response.raw.read(65_536, decode_content=True)
                return build_result(response.status_code, response.url, response.headers, body, response.encoding)
        except Exception as error:  # independent network provider boundary
            last_error = str(error)
            if NetworkManager.is_active():
                continue
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Laitoxx-Domain-Intelligence/1.0"},
            )
            with urllib.request.urlopen(  # noqa: S310
                request,
                timeout=12,
                context=trusted_ssl_context(),
            ) as response:
                body = response.read(65_536)
                encoding = response.headers.get_content_charset() or "utf-8"
                return build_result(response.status, response.url, response.headers, body, encoding)
        except Exception as error:  # system trust-store fallback boundary
            last_error = str(error)
    raise RuntimeError(last_error or "No HTTP endpoint responded")


def _tls_profile(domain: str) -> dict:
    with socket.create_connection((domain, 443), timeout=8) as raw:
        with trusted_ssl_context().wrap_socket(raw, server_hostname=domain) as connection:
            certificate, cipher = connection.getpeercert(), connection.cipher()
            return {
                "protocol": connection.version(),
                "cipher": cipher[0] if cipher else "",
                "subject": dict(item[0] for item in certificate.get("subject", [])),
                "issuer": dict(item[0] for item in certificate.get("issuer", [])),
                "not_before": certificate.get("notBefore", ""),
                "not_after": certificate.get("notAfter", ""),
                "san_count": len(certificate.get("subjectAltName", [])),
            }


def collect_domain_intelligence(value: str) -> dict:
    domain = normalize_domain(value)
    report = {
        "domain": domain,
        "collected_at": datetime.now(UTC).isoformat(),
        "dns": {},
        "registration": {},
        "http": {},
        "tls": {},
        "errors": {},
    }
    jobs = {"dns": _dns_profile, "registration": _rdap_profile, "http": _http_profile, "tls": _tls_profile}
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="domain-intel") as executor:
        futures = {executor.submit(function, domain): name for name, function in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                report[name] = future.result()
            except Exception as error:
                report["errors"][name] = str(error)
    return report


def domain_intelligence(value: str | None = None) -> dict:
    report = collect_domain_intelligence(value if value is not None else input())
    print(f"Domain Intelligence: {report['domain']}")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return report
