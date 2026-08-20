from __future__ import annotations

import ipaddress
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
ASN_RE = re.compile(r"^(?:AS)?(\d{1,10})$", re.IGNORECASE)
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$", re.I)


@dataclass(frozen=True)
class Target:
    kind: str
    value: str
    original: str


@dataclass
class Entity:
    kind: str
    value: str
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.value.casefold()}"


@dataclass
class Relation:
    source: str
    target: str
    relation: str
    source_name: str
    confidence: str = "medium"
    current: bool | None = None
    evidence: str = ""
    # Evidence lifecycle fields are deliberately optional so reports produced
    # before the evidence broker was introduced remain loadable.
    observed_at: str = ""
    checked_at: str = ""
    expires_at: str = ""
    state: str = ""  # historical | candidate | live | confirmed | rejected
    supporting_sources: list[str] = field(default_factory=list)


@dataclass
class TimelineEvent:
    event_time: str
    observed_at: str
    source: str
    relation: str
    subject: str
    object: str = ""
    confidence: str = "medium"


@dataclass
class ProviderResult:
    name: str
    status: str = "ok"  # ok | cached | skipped | rate_limited | no_data | unavailable | restricted | auth_error | error
    data: dict[str, Any] = field(default_factory=dict)
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    error: str = ""
    duration_ms: int = 0
    checked_at: str = ""


@dataclass
class RiskFactor:
    label: str
    points: float
    evidence: str


@dataclass
class ScanReport:
    target: Target
    providers: list[ProviderResult] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    risk_score: float = 0.0
    risk_level: str = "unknown"
    risk_factors: list[RiskFactor] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_target(raw: str) -> Target:
    value = raw.strip()
    if not value:
        raise ValueError("Target is required")
    if CVE_RE.fullmatch(value):
        return Target("cve", value.upper(), raw)
    asn = ASN_RE.fullmatch(value)
    if asn and (value.upper().startswith("AS") or int(asn.group(1)) > 255):
        return Target("asn", f"AS{int(asn.group(1))}", raw)
    try:
        return Target("ip", str(ipaddress.ip_address(value)), raw)
    except ValueError:
        pass
    parsed = urlparse(value if "://" in value else f"//{value}")
    if "://" in value and parsed.hostname:
        host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        normalized = parsed._replace(netloc=host + (f":{parsed.port}" if parsed.port else "")).geturl()
        return Target("url", normalized, raw)
    domain = value.encode("idna").decode("ascii").lower().rstrip(".")
    if DOMAIN_RE.fullmatch(domain):
        return Target("domain", domain, raw)
    raise ValueError("Expected an IP, domain, URL, ASN or CVE")
