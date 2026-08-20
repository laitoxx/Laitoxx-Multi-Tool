"""DNS discovery and mail/security posture providers."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from requests import HTTPError, RequestException, Timeout

from laitoxx.core.settings.network_manager import NetworkManager

from .. import provider_common as _common
from ..models import DOMAIN_RE, Entity, ProviderResult, Relation, Target
from ..quota import QuotaExceeded

_DNS_RECORD_TYPE_BY_CODE = _common._DNS_RECORD_TYPE_BY_CODE
_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run
_safe_error = _common._safe_error


def _doh_answers(domain: str, record_type: str, *, consensus: bool = True) -> tuple[list[dict], dict, bool]:
    """Resolve through independent DoH services with transport failover.

    A successful NXDOMAIN/NODATA response is evidence, not a transport error.
    SERVFAIL and REFUSED are eligible for fallback.  A second resolver is
    queried for address/CNAME records to expose GeoDNS and disagreement.
    """
    resolvers = (
        ("Cloudflare", "dns", "https://cloudflare-dns.com/dns-query", {"Accept": "application/dns-json"}),
        ("Google", "dns_google", "https://dns.google/resolve", {}),
    )
    answers: list[dict] = []
    statuses: dict[str, dict] = {}
    all_cached = True
    first_succeeded = False
    last_error: Exception | None = None
    for index, (resolver, namespace, url, headers) in enumerate(resolvers):
        if index and first_succeeded and not (consensus and record_type in {"A", "AAAA", "CNAME"}):
            break
        try:
            data, hit = _cached_json(
                namespace,
                f"{domain}:{record_type}",
                url,
                params={"name": domain, "type": record_type},
                headers=headers,
                ttl=900,
            )
            all_cached &= hit
            status = int(data.get("Status", 0) or 0)
            statuses[resolver] = {"status": status, "cached": hit}
            if status in {2, 5}:  # SERVFAIL / REFUSED: try the next transport.
                raise RequestException(f"{resolver} DNS status {status}")
            first_succeeded = True
            for answer in data.get("Answer", []) or []:
                enriched = dict(answer)
                enriched["resolver"] = resolver
                answers.append(enriched)
        except (RequestException, HTTPError, Timeout, QuotaExceeded) as exc:
            statuses[resolver] = {"error": _safe_error(exc)}
            last_error = exc
            continue
    if not first_succeeded and last_error:
        raise last_error
    return answers, statuses, all_cached


def dns(target: Target, mode: str = "doh", *, consensus: bool = True) -> ProviderResult:
    def load():
        domain = urlparse(target.value).hostname if target.kind == "url" else target.value
        if target.kind == "ip":
            domain = ipaddress.ip_address(target.value).reverse_pointer
            record_types = ("PTR",)
        else:
            record_types = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "CAA")
        records: dict[str, list[str]] = {}
        record_sources: dict[str, dict[str, list[str]]] = {}
        resolver_status: dict[str, dict] = {}
        was_cached = True
        if mode == "system" and not NetworkManager.is_active():
            if target.kind == "ip":
                records["PTR"] = [socket.gethostbyaddr(target.value)[0]]
            else:
                addresses = socket.getaddrinfo(domain, None)
                records["A/AAAA"] = sorted({item[4][0] for item in addresses})
            was_cached = False
        else:
            for record_type in record_types:
                try:
                    answers, statuses, hit = _doh_answers(domain, record_type, consensus=consensus)
                except (RequestException, HTTPError, Timeout, QuotaExceeded) as exc:
                    if NetworkManager.is_active():
                        raise
                    answers, statuses, hit = [], {"System DNS": {"fallback_after": _safe_error(exc)}}, False
                    if record_type in {"A", "AAAA"}:
                        version = 4 if record_type == "A" else 6
                        for address in sorted({item[4][0] for item in socket.getaddrinfo(domain, None)}):
                            try:
                                parsed_address = ipaddress.ip_address(address)
                            except ValueError:
                                continue
                            if parsed_address.version == version:
                                answers.append(
                                    {
                                        "type": 1 if version == 4 else 28,
                                        "data": str(parsed_address),
                                        "resolver": "System DNS",
                                    }
                                )
                        statuses["System DNS"]["status"] = 0
                    elif record_type == "PTR":
                        answers.append(
                            {"type": 12, "data": socket.gethostbyaddr(target.value)[0], "resolver": "System DNS"}
                        )
                        statuses["System DNS"]["status"] = 0
                resolver_status[record_type] = statuses
                was_cached &= hit
                # A DoH Answer section can contain a CNAME followed by the
                # requested A/AAAA record.  Classifying every item as the
                # requested type turns hostnames such as *.akamaiedge.net into
                # fake IP entities.  Honour each answer's actual DNS type.
                for answer in answers:
                    raw_value = str(answer.get("data", "")).strip('"')
                    if not raw_value:
                        continue
                    try:
                        type_code = int(answer.get("type"))
                    except (TypeError, ValueError):
                        type_code = 0
                    actual_type = _DNS_RECORD_TYPE_BY_CODE.get(type_code, record_type)
                    bucket = records.setdefault(actual_type, [])
                    if raw_value not in bucket:
                        bucket.append(raw_value)
                    sources = record_sources.setdefault(actual_type, {}).setdefault(raw_value, [])
                    resolver = str(answer.get("resolver") or "DoH")
                    if resolver not in sources:
                        sources.append(resolver)
        entities, relations = [], []
        root_kind = "domain" if target.kind == "url" else target.kind
        root_value = domain if target.kind == "url" else target.value
        root = _entity_id(root_kind, root_value)
        for record_type, values in records.items():
            for raw in values:
                value = raw.rstrip(".")
                kind = "ip" if record_type in {"A", "AAAA", "A/AAAA"} else "domain"
                if record_type == "MX":
                    value = value.split()[-1].rstrip(".")
                elif record_type == "SOA":
                    value = value.split()[0].rstrip(".")
                if record_type == "TXT":
                    kind = "dns_record"
                sources = record_sources.get(record_type, {}).get(raw, [])
                metadata = {
                    "record_type": record_type,
                    "dns_sources": sources,
                    "dns_consensus": len(sources) >= 2,
                }
                if kind == "ip":
                    try:
                        value = str(ipaddress.ip_address(value))
                    except ValueError:
                        # Defensive fallback for malformed/non-standard DoH
                        # responses.  Never let an unparseable value enter the
                        # IP enrichment pipeline.
                        if DOMAIN_RE.fullmatch(value):
                            kind = "domain"
                            metadata["type_mismatch"] = True
                        else:
                            continue
                entities.append(Entity(kind, value, metadata=metadata))
                confidence = "high" if len(sources) >= 2 or mode == "system" else "medium"
                relations.append(
                    Relation(
                        root,
                        _entity_id(kind, value),
                        "dns_record",
                        "DNS",
                        confidence,
                        True,
                        record_type,
                        checked_at=_now(),
                        state="live",
                        supporting_sources=sources or ["System DNS"],
                    )
                )
        disagreements = {}
        for record_type, value_sources in record_sources.items():
            by_resolver: dict[str, set[str]] = {}
            for resolver, status in resolver_status.get(record_type, {}).items():
                if "status" in status:
                    by_resolver.setdefault(resolver, set())
            for value, sources in value_sources.items():
                for source in sources:
                    by_resolver.setdefault(source, set()).add(value)
            if len(by_resolver) >= 2 and len({tuple(sorted(values)) for values in by_resolver.values()}) > 1:
                disagreements[record_type] = {resolver: sorted(values) for resolver, values in by_resolver.items()}
        return ProviderResult(
            "DNS",
            "cached" if was_cached else "ok",
            {
                "records": records,
                "record_sources": record_sources,
                "resolver_status": resolver_status,
                "resolver_disagreements": disagreements,
            },
            entities,
            relations,
        )

    return _run("DNS", load)
