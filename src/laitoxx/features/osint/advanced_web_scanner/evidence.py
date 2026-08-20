"""Evidence lifecycle, source corroboration and freshness handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .models import Relation, ScanReport

_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
_STATE_RANK = {"rejected": 0, "historical": 1, "candidate": 2, "live": 3, "confirmed": 4}
_HISTORICAL_RELATIONS = {
    "historical_resolves_to",
    "historical_or_observed",
    "archived_url",
    "reverse_ip_association",
    "reverse_whois_association",
}
_CONFIRMED_RELATIONS = {"validated_vulnerability", "current_resolves_to"}
_LIVE_RELATIONS = {"dns_record", "ptr_record", "exposes", "responds_with", "live_service"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def relation_state(relation: Relation) -> str:
    if relation.state in _STATE_RANK:
        return relation.state
    if relation.relation in _CONFIRMED_RELATIONS:
        return "confirmed"
    if relation.relation in _HISTORICAL_RELATIONS or relation.current is False:
        return "historical"
    if relation.current is True or relation.relation in _LIVE_RELATIONS:
        return "live"
    return "candidate"


def annotate_report(report: ScanReport, *, checked_at: str | None = None) -> None:
    """Attach a stable lifecycle to every claim and propagate it to entities."""
    checked = checked_at or utc_now()
    entity_by_id = {entity.id: entity for entity in report.entities}
    incoming: dict[str, list[Relation]] = {}
    for relation in report.relations:
        relation.state = relation_state(relation)
        relation.checked_at = relation.checked_at or checked
        relation.observed_at = relation.observed_at or _relation_observed_at(relation, entity_by_id)
        relation.supporting_sources = sorted({*relation.supporting_sources, relation.source_name})
        if not relation.expires_at:
            ttl = _ttl_for(relation)
            try:
                relation.expires_at = (datetime.fromisoformat(relation.checked_at) + ttl).isoformat()
            except ValueError:
                relation.expires_at = ""
        incoming.setdefault(relation.target, []).append(relation)

    for entity in report.entities:
        claims = incoming.get(entity.id, [])
        if not claims:
            continue
        best = max(
            claims, key=lambda item: (_STATE_RANK[relation_state(item)], _CONFIDENCE_RANK.get(item.confidence, 0))
        )
        states = {relation_state(item) for item in claims}
        sources = sorted({source for item in claims for source in item.supporting_sources})
        entity.metadata.setdefault("evidence_state", relation_state(best))
        entity.metadata["evidence_states"] = sorted(states, key=lambda state: _STATE_RANK[state], reverse=True)
        entity.metadata["evidence_sources"] = sources
        entity.metadata["checked_at"] = max((item.checked_at for item in claims if item.checked_at), default=checked)
        observed = [item.observed_at for item in claims if item.observed_at]
        if observed:
            entity.metadata.setdefault("first_seen", min(observed))
            entity.metadata["last_seen"] = max(observed)


def add_corroborated_relations(report: ScanReport) -> None:
    """Add one aggregate claim when independent sources report the same edge."""
    groups: dict[tuple[str, str, str], list[Relation]] = {}
    for relation in report.relations:
        if relation.source_name in {"Correlation", "Evidence Broker"}:
            continue
        groups.setdefault((relation.source, relation.target, relation.relation), []).append(relation)
    for (source, target, name), relations in groups.items():
        sources = sorted({relation.source_name for relation in relations})
        if len(sources) < 2:
            continue
        confidence = (
            "high"
            if len(sources) >= 2
            else max((relation.confidence for relation in relations), key=lambda value: _CONFIDENCE_RANK.get(value, 0))
        )
        state = max((relation_state(relation) for relation in relations), key=_STATE_RANK.__getitem__)
        current_values = {relation.current for relation in relations}
        current = True if True in current_values else False if current_values == {False} else None
        report.relations.append(
            Relation(
                source,
                target,
                name,
                "Evidence Broker",
                confidence,
                current,
                "Independent sources: " + ", ".join(sources),
                observed_at=max((relation.observed_at for relation in relations if relation.observed_at), default=""),
                checked_at=max((relation.checked_at for relation in relations if relation.checked_at), default=""),
                state=state,
                supporting_sources=sources,
            )
        )


def _relation_observed_at(relation: Relation, entity_by_id: dict) -> str:
    target = entity_by_id.get(relation.target)
    if target:
        for key in ("observed_at", "last_seen", "timestamp", "time"):
            value = str(target.metadata.get(key) or "").strip()
            if value:
                return value
    return relation.checked_at


def _ttl_for(relation: Relation) -> timedelta:
    if relation.state == "confirmed":
        return timedelta(hours=24)
    if relation.state == "live":
        return timedelta(hours=6)
    if relation.state == "candidate":
        return timedelta(hours=1)
    return timedelta(days=3650)
