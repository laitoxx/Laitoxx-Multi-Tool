"""Live TLS certificate extraction provider."""

from __future__ import annotations

import socket
import ssl

from laitoxx.core.settings.network_manager import NetworkManager

from .. import provider_common as _common
from ..models import Entity, ProviderResult, Relation, TimelineEvent

_entity_id = _common._entity_id
_now = _common._now
_run = _common._run
skipped = _common.skipped


def tls_certificate(host: str, port: int = 443) -> ProviderResult:
    if NetworkManager.is_active():
        return skipped("Local TLS", "Raw TLS is disabled while proxy protection is active")

    def load():
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                certificate = tls.getpeercert()
                der = tls.getpeercert(binary_form=True)
        sans = [value for kind, value in certificate.get("subjectAltName", []) if kind == "DNS"]
        fingerprint = __import__("hashlib").sha256(der).hexdigest()
        entities, relations = [], []
        root = _entity_id("domain", host)
        certificate_entity = Entity(
            "certificate",
            fingerprint,
            label=fingerprint[:16],
            metadata={
                "fingerprint_sha256": fingerprint,
                "subject": certificate.get("subject"),
                "issuer": certificate.get("issuer"),
                "not_before": certificate.get("notBefore"),
                "not_after": certificate.get("notAfter"),
                "source": "Local TLS",
                "evidence_state": "live",
            },
        )
        entities.append(certificate_entity)
        relations.append(
            Relation(
                root,
                certificate_entity.id,
                "deploys_certificate",
                "Local TLS",
                "high",
                True,
                f"Certificate observed in a live TLS handshake on port {port}",
                checked_at=_now(),
                state="confirmed",
                supporting_sources=["Local TLS"],
            )
        )
        for name in sans:
            normalized = name.lower().removeprefix("*.")
            entities.append(Entity("domain", normalized))
            relations.append(
                Relation(
                    certificate_entity.id,
                    _entity_id("domain", normalized),
                    "certificate_contains",
                    "Local TLS",
                    "high",
                    True,
                    "Subject Alternative Name in the live certificate",
                    checked_at=_now(),
                    state="live",
                )
            )
        data = {
            "subject": certificate.get("subject"),
            "issuer": certificate.get("issuer"),
            "sans": sans,
            "sha256": fingerprint,
            "not_before": certificate.get("notBefore"),
            "not_after": certificate.get("notAfter"),
        }
        events = []
        for field, relation_name in (("notBefore", "certificate_valid_from"), ("notAfter", "certificate_valid_until")):
            if certificate.get(field):
                events.append(
                    TimelineEvent(
                        str(certificate[field]), _now(), "Local TLS", relation_name, host, fingerprint, "high"
                    )
                )
        return ProviderResult("Local TLS", "ok", data, entities, relations, events)

    return _run("Local TLS", load)
