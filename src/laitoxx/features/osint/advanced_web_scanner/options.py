"""Immutable scan configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from .configuration import load_configuration


@dataclass(frozen=True)
class ScanOptions:
    profile: str = "minimum"
    dns_mode: str = "doh"
    max_ip_pivots: int = 8
    max_cve_pivots: int = 10
    max_depth: int = 2
    max_domain_pivots: int = 12
    max_recursive_ip_pivots: int = 12
    max_hostname_verifications: int = 48
    clean_shared_infrastructure: bool = True
    dns_security_posture: bool = True
    routing_enrichment: bool = True
    archive_enrichment: bool = True
    active_scanning: bool = False
    active_rate_limit: int = 5
    active_port_rate: int = 25
    active_timeout: int = 90
    active_max_targets: int = 8
    max_technology_pivots: int = 4
    max_shodan_filter_pivots: int = 8
    workers: int = 6
    provider_config: dict = field(default_factory=load_configuration)
