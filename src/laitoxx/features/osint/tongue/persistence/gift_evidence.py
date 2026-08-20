"""Persist public gift identities and correlation observations."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from ..domain.models import GiftIdentity
from ..domain.primitives import jsonable, stable_id, utc_now_iso


class GiftEvidenceMixin:
    def save_gift(self, gift: GiftIdentity) -> None:
        now = utc_now_iso()
        payload = json.dumps(jsonable(asdict(gift)), ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO gifts(
                slug, title, gift_number, collection_slug, public_profiles_json,
                ton_candidates_json, payload_json, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title=COALESCE(excluded.title, gifts.title),
                gift_number=COALESCE(excluded.gift_number, gifts.gift_number),
                collection_slug=COALESCE(excluded.collection_slug, gifts.collection_slug),
                public_profiles_json=excluded.public_profiles_json,
                ton_candidates_json=excluded.ton_candidates_json,
                payload_json=excluded.payload_json,
                last_seen=excluded.last_seen
            """,
            (
                gift.slug,
                gift.title,
                gift.number,
                gift.collection_slug,
                json.dumps(gift.public_profiles, ensure_ascii=False),
                json.dumps(gift.ton_address_candidates, ensure_ascii=False),
                payload,
                now,
                now,
            ),
        )
        self.conn.commit()

    def save_gift_resolution(
        self,
        gift_slug: str,
        relation: str,
        confidence: float,
        source: str,
        evidence: Sequence[str],
        nft_address: str | None = None,
        ton_owner: str | None = None,
        telegram_profile: str | None = None,
    ) -> None:
        key = stable_id(gift_slug, relation, nft_address or "", ton_owner or "", telegram_profile or "", source)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO gift_resolutions(
                id, gift_slug, nft_address, ton_owner, telegram_profile,
                relation, confidence, source, evidence_json, observed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                gift_slug,
                nft_address,
                ton_owner,
                telegram_profile,
                relation,
                float(confidence),
                source,
                json.dumps(list(evidence), ensure_ascii=False),
                utc_now_iso(),
            ),
        )
        self.conn.commit()

    def observe_collectible_identity(
        self,
        *,
        collectible_id: str,
        collectible_kind: str,
        nft_address: str | None,
        chain_owner: str | None,
        public_identity: str,
        source: str,
        evidence: Sequence[str],
    ) -> dict[str, Any] | None:
        """Persist a public identity state and return the superseded state."""
        if not collectible_id or not public_identity:
            return None
        now = utc_now_iso()
        previous = self.conn.execute(
            """
            SELECT * FROM collectible_identity_observations
            WHERE collectible_id=? AND valid_to IS NULL
            ORDER BY last_seen DESC LIMIT 1
            """,
            (collectible_id,),
        ).fetchone()
        if previous and (
            str(previous["chain_owner"] or "") == str(chain_owner or "")
            and str(previous["public_identity"]) == public_identity
        ):
            self.conn.execute(
                "UPDATE collectible_identity_observations SET last_seen=? WHERE id=?",
                (now, previous["id"]),
            )
            self.conn.commit()
            return None
        previous_data = dict(previous) if previous else None
        if previous:
            self.conn.execute(
                "UPDATE collectible_identity_observations SET valid_to=? WHERE id=?",
                (now, previous["id"]),
            )
        observation_id = stable_id(
            collectible_id,
            collectible_kind,
            nft_address or "",
            chain_owner or "",
            public_identity,
            now,
        )
        self.conn.execute(
            """
            INSERT INTO collectible_identity_observations(
                id, collectible_id, collectible_kind, nft_address, chain_owner,
                public_identity, source, evidence_json, first_seen, last_seen, valid_to
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                observation_id,
                collectible_id,
                collectible_kind,
                nft_address,
                chain_owner,
                public_identity,
                source,
                json.dumps(list(evidence), ensure_ascii=False),
                now,
                now,
            ),
        )
        self.conn.commit()
        return previous_data
