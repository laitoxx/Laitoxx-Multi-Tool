"""Bounded, de-duplicated graph data safe for WebEngine renderers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import Entity, Relation, ScanReport


@dataclass(frozen=True)
class GraphProjection:
    entities: list[Entity]
    relations: list[Relation]
    omitted_entities: int = 0
    omitted_relations: int = 0


_KIND_PRIORITY = {
    "cve": 90,
    "finding": 88,
    "ip": 80,
    "domain": 75,
    "url": 72,
    "organization": 68,
    "infrastructure_provider": 67,
    "asn": 65,
    "rpki_status": 64,
    "prefix": 60,
    "dns_policy": 58,
    "service": 55,
    "cpe": 50,
    "web_artifact": 45,
    "web_fingerprint": 44,
}
_CONFIDENCE_PRIORITY = {"high": 30, "medium": 18, "low": 8}


def project_for_graph(
    report: ScanReport,
    *,
    max_entities: int = 90,
    max_relations: int = 150,
) -> GraphProjection:
    """Keep the most useful connected evidence while bounding renderer input."""
    unique_entities: dict[str, Entity] = {}
    for entity in report.entities:
        existing = unique_entities.get(entity.id)
        if existing is None:
            unique_entities[entity.id] = entity
        else:
            existing.metadata.update(entity.metadata)

    unique_relations: dict[tuple[str, str, str], Relation] = {}
    for relation in report.relations:
        if relation.source == relation.target:
            continue
        if relation.source not in unique_entities or relation.target not in unique_entities:
            continue
        key = (relation.source, relation.target, relation.relation)
        current = unique_relations.get(key)
        if current is None or _relation_score(relation) > _relation_score(current):
            unique_relations[key] = relation

    relations = list(unique_relations.values())
    degree = Counter(endpoint for relation in relations for endpoint in (relation.source, relation.target))
    root_id = f"{report.target.kind}:{report.target.value.casefold()}"
    selected_ids = {root_id} if root_id in unique_entities else set()

    ranked_relations = sorted(
        relations,
        key=lambda relation: (
            _relation_score(relation),
            degree[relation.source] + degree[relation.target],
            relation.source,
            relation.target,
            relation.relation,
        ),
        reverse=True,
    )
    direct_relations = [relation for relation in ranked_relations if root_id in {relation.source, relation.target}]
    for relation in direct_relations:
        endpoints = {relation.source, relation.target}
        if len(selected_ids | endpoints) <= max_entities:
            selected_ids.update(endpoints)
        if len(selected_ids) >= max_entities:
            break

    for relation in ranked_relations:
        endpoints = {relation.source, relation.target}
        if not (endpoints & selected_ids):
            continue
        if len(selected_ids | endpoints) <= max_entities:
            selected_ids.update(endpoints)
        if len(selected_ids) >= max_entities:
            break

    for relation in ranked_relations:
        endpoints = {relation.source, relation.target}
        if len(selected_ids | endpoints) <= max_entities:
            selected_ids.update(endpoints)
        if len(selected_ids) >= max_entities:
            break

    ranked_entities = sorted(
        unique_entities.values(),
        key=lambda entity: (_entity_score(entity, degree[entity.id]), entity.value.casefold()),
        reverse=True,
    )
    for entity in ranked_entities:
        if len(selected_ids) >= max_entities:
            break
        selected_ids.add(entity.id)

    selected_entities = [unique_entities[entity_id] for entity_id in selected_ids if entity_id in unique_entities]
    selected_relations = [
        relation for relation in ranked_relations if relation.source in selected_ids and relation.target in selected_ids
    ][:max_relations]
    return GraphProjection(
        entities=selected_entities,
        relations=selected_relations,
        omitted_entities=max(0, len(unique_entities) - len(selected_entities)),
        omitted_relations=max(0, len(relations) - len(selected_relations)),
    )


def _entity_score(entity: Entity, degree: int) -> int:
    score = _KIND_PRIORITY.get(entity.kind, 25) + min(degree, 20) * 2
    if entity.metadata.get("pivot_suppressed"):
        score -= 20
    return score


def _relation_score(relation: Relation) -> int:
    return _CONFIDENCE_PRIORITY.get(relation.confidence, 0) + (12 if relation.current else 0)
