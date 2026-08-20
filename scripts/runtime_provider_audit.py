"""Offline runtime checks for provider parsing and transport failures."""

from __future__ import annotations

from requests import HTTPError, Response, Timeout

from laitoxx.features.osint.advanced_web_scanner import provider_common
from laitoxx.features.osint.advanced_web_scanner.configuration import (
    configuration_errors,
    default_configuration,
    provider_enabled,
)
from laitoxx.features.osint.advanced_web_scanner.models import Target
from laitoxx.features.osint.advanced_web_scanner.provider import certificates, dns, reverse_lookup


def transport_classification() -> None:
    unavailable = provider_common._run("offline", lambda: (_ for _ in ()).throw(Timeout("timed out")))
    assert unavailable.status == "unavailable" and "timed out" in unavailable.error

    response = Response()
    response.status_code = 429
    response._content = b'{"error":"slow down"}'
    response.url = "https://example.invalid/?api_key=secret"
    error = HTTPError("request failed", response=response)
    limited = provider_common._run("limited", lambda: (_ for _ in ()).throw(error))
    assert limited.status == "rate_limited" and "slow down" in limited.error

    redacted = provider_common._run(
        "redacted",
        lambda: (_ for _ in ()).throw(ValueError("https://x.invalid/?token=secret&x=1")),
    )
    assert redacted.status == "error" and "secret" not in redacted.error and "<redacted>" in redacted.error
    assert provider_common.skipped("x", "no key").status == "skipped"


def configuration_boundaries() -> None:
    config = default_configuration()
    assert config["configured"] is False
    assert configuration_errors(config)
    for provider_id, item in config["providers"].items():
        assert provider_enabled(provider_id, config) is bool(item["enabled"])


def certificate_payloads() -> None:
    original = certificates._cached_json
    try:
        certificates._cached_json = lambda *_args, **_kwargs: (
            [
                {
                    "id": "cert-1",
                    "name_value": "example.com\n*.sub.example.com\nunrelated.test",
                    "issuer_name": "Demo CA",
                    "entry_timestamp": "2025-01-01T00:00:00Z",
                }
            ],
            False,
        )
        result = certificates.crtsh("example.com")
        assert result.status == "ok"
        assert result.data["names"] == ["example.com", "sub.example.com"]
        assert result.data["related_names"] == ["unrelated.test"]

        certificates._cached_json = lambda *_args, **_kwargs: (
            [
                {
                    "cert_sha256": "abc",
                    "dns_names": ["example.com", "*.sub.example.com", "bad host"],
                    "issuer": {"name": "Demo CA"},
                    "not_before": "2025-01-01T00:00:00Z",
                }
            ],
            True,
        )
        result = certificates.certspotter("example.com")
        assert result.status == "cached" and result.data["count"] == 1
        assert {entity.value for entity in result.entities if entity.kind == "domain"} == {
            "example.com",
            "sub.example.com",
        }
    finally:
        certificates._cached_json = original


def dns_payloads_and_skips() -> None:
    original = dns._doh_answers

    def answers(_domain: str, record_type: str, *, consensus: bool = True):
        del consensus
        payloads = {
            "A": [
                {"type": 5, "data": "alias.example.com.", "resolver": "one"},
                {"type": 1, "data": "192.0.2.10", "resolver": "one"},
                {"type": 1, "data": "not-an-ip", "resolver": "one"},
            ],
            "MX": [{"type": 15, "data": "10 mail.example.com.", "resolver": "one"}],
        }
        return payloads.get(record_type, []), {"one": {"status": 0}}, False

    try:
        dns._doh_answers = answers
        result = dns.dns(Target("domain", "example.com", "example.com"))
        assert result.status == "ok"
        values = {(entity.kind, entity.value) for entity in result.entities}
        assert ("ip", "192.0.2.10") in values
        assert ("domain", "alias.example.com") in values
        assert ("domain", "mail.example.com") in values
        assert all(entity.value != "not-an-ip" for entity in result.entities)
    finally:
        dns._doh_answers = original

    original_credential = reverse_lookup.credential
    original_cached_json = reverse_lookup._cached_json
    try:
        reverse_lookup.credential = lambda _provider: ""
        assert reverse_lookup.whoisjson_reverse_whois("192.0.2.1").status == "skipped"
        reverse_lookup._cached_json = lambda *_args, **_kwargs: (_ for _ in ()).throw(Timeout("offline"))
        assert reverse_lookup.botoi_reverse_dns("192.0.2.1").status == "unavailable"
    finally:
        reverse_lookup.credential = original_credential
        reverse_lookup._cached_json = original_cached_json


def main() -> int:
    cases = (transport_classification, configuration_boundaries, certificate_payloads, dns_payloads_and_skips)
    for case in cases:
        case()
        print(f"PASS {case.__name__}")
    print(f"cases={len(cases)} failed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
