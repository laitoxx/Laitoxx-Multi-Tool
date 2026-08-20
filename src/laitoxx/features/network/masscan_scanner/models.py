"""Domain models for the Masscan workspace."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MasscanOptions:
    ports: str = "1-1024,3306,3389,5432,6379,8080,8443,9200,27017"
    rate: int = 500
    banners: bool = True
    wait_seconds: int = 2


@dataclass(slots=True)
class FingerprintMatch:
    service: str
    product: str = ""
    version: str = ""
    info: str = ""
    device_type: str = ""
    operating_system: str = ""
    cpes: list[str] = field(default_factory=list)
    source: str = ""
    confidence: float = 0.0
    pattern_type: str = ""


@dataclass(slots=True)
class ServiceObservation:
    ip: str
    port: int
    protocol: str = "tcp"
    state: str = "open"
    reason: str = ""
    ttl: int | None = None
    service: str = "unknown"
    banner: str = ""
    fingerprint: FingerprintMatch | None = None


@dataclass(slots=True)
class MasscanReport:
    target: str
    resolved_target: str
    options: MasscanOptions
    observations: list[ServiceObservation] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    duration_ms: int = 0
    scanner_version: str = ""
    warnings: list[str] = field(default_factory=list)
    raw_records: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
