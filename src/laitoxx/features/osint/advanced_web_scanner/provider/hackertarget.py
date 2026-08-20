"""HackerTarget host and reverse-IP discovery provider."""

from __future__ import annotations

import ipaddress
import re

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.osint.intelligence.cache import cache

from .. import provider_common as _common
from ..configuration import auth_mode, credential
from ..models import Entity, ProviderResult, Relation
from ..quota import QuotaExceeded, ledger

USER_AGENT = _common.USER_AGENT
_entity_id = _common._entity_id
_run = _common._run


def hackertarget(kind: str, value: str) -> ProviderResult:
    endpoint = "reverseiplookup" if kind == "ip" else "hostsearch"
    name = "HackerTarget Reverse IP" if kind == "ip" else "HackerTarget Host Search"

    def load():
        def fetch_text():
            event_id = ledger.acquire("hackertarget")
            key = credential("hackertarget") if auth_mode("hackertarget") == "key" else ""
            headers = {"User-Agent": USER_AGENT}
            if key:
                headers["X-API-Key"] = key
            response = get_session().get(
                f"https://api.hackertarget.com/{endpoint}/", params={"q": value}, headers=headers, timeout=20
            )
            ledger.record_response(event_id, "hackertarget", response.status_code, response.headers)
            response.raise_for_status()
            return {"text": response.text}

        data, hit = cache.get_or_set(f"advanced_web_scanner:hackertarget:{endpoint}", value, fetch_text, 21600)
        text = data.get("text", "")
        lowered = text.casefold()
        if "api count exceeded" in lowered or "quota exceeded" in lowered or "rate limit" in lowered:
            raise QuotaExceeded("HackerTarget Reverse IP: server-reported quota exhausted")
        no_data = any(
            message in lowered
            for message in (
                "no dns a records found",
                "no records found",
                "no results found",
            )
        )
        entities, relations = [], []
        root = _entity_id(kind, value)
        for line in text.splitlines():
            parts = [part.strip() for part in line.split(",")]
            for part in parts:
                try:
                    peer_kind, peer = "ip", str(ipaddress.ip_address(part))
                except ValueError:
                    if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", part, re.I):
                        continue
                    peer_kind, peer = "domain", part.lower().rstrip(".")
                if not (peer_kind == kind and peer == value):
                    metadata = {}
                    relation_name = "observed_with"
                    evidence = ""
                    if kind == "ip" and peer_kind == "domain":
                        metadata = {
                            "discovery": "reverse_ip",
                            "evidence_kind": "a_record_database",
                            "ownership_proven": False,
                        }
                        relation_name = "reverse_ip_association"
                        evidence = "Host observed with this IP in HackerTarget's A-record database; shared hosting is possible."
                    entities.append(Entity(peer_kind, peer, metadata=metadata))
                    relations.append(
                        Relation(
                            root,
                            _entity_id(peer_kind, peer),
                            relation_name,
                            name,
                            "low",
                            None,
                            evidence,
                        )
                    )
        status = "cached" if hit else "ok"
        if no_data or not entities:
            status = "no_data"
        return ProviderResult(name, status, data, entities, relations)

    return _run(name, load)


def hackertarget_reverse_ip(ip: str) -> ProviderResult:
    return hackertarget("ip", str(ipaddress.ip_address(ip)))
