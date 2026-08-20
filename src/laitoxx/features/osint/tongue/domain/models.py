"""Stable domain models for TON investigations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .primitives import utc_now_iso


@dataclass(slots=True)
class GiftIdentity:
    slug: str
    source_url: str
    title: str | None = None
    number: int | None = None
    collection_slug: str | None = None
    model: str | None = None
    backdrop: str | None = None
    symbol: str | None = None
    public_profiles: list[str] = field(default_factory=list)
    ton_address_candidates: list[dict[str, str]] = field(default_factory=list)
    fragment_links: list[str] = field(default_factory=list)
    image_url: str | None = None
    description: str | None = None
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    fetched_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class NftGiftMatch:
    nft_address: str
    owner_address: str | None
    collection_address: str | None
    confidence: float
    status: str
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NftHistoryEvent:
    event_id: str
    nft_address: str
    event_type: str
    old_owner: str | None
    new_owner: str | None
    transaction_lt: int
    transaction_time: str | None
    transaction_hash: str | None
    trace_id: str | None
    success: bool
    price_ton: float | None = None
    confidence: float = 1.0
    evidence: list[str] = field(default_factory=list)


@dataclass(order=True, slots=True)
class DiscoveryTask:
    sort_key: tuple[int, int, str] = field(init=False, repr=False)
    priority: int = field(compare=False)
    depth: int = field(compare=False)
    entity_type: str = field(compare=False)
    entity_id: str = field(compare=False)
    parent_id: str | None = field(default=None, compare=False)
    relation: str | None = field(default=None, compare=False)
    confidence: float = field(default=1.0, compare=False)

    def __post_init__(self) -> None:
        self.sort_key = (-self.priority, self.depth, f"{self.entity_type}:{self.entity_id}")


@dataclass(slots=True)
class AddressIdentity:
    input: str
    raw: str
    bounceable: str | None = None
    non_bounceable: str | None = None


@dataclass(slots=True)
class Movement:
    movement_id: str
    direction: str
    source: str
    destination: str
    amount_ton: float
    created_at: str | None
    tx_hash: str
    tx_lt: int
    trace_id: str | None
    message_hash: str | None
    opcode: int | None
    decoded_opcode: str | None
    comment: str
    success: bool
    classification: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GraphNode:
    id: str
    type: str
    label: str
    weight: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphEdge:
    source: str
    target: str
    kind: str
    label: str
    count: int = 1
    weight: float = 1.0
    total_ton: float = 0.0
    confidence: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SQLite evidence store and checkpoints
# ---------------------------------------------------------------------------
