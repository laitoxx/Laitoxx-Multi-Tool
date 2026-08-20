"""Public web archive discovery providers."""

from __future__ import annotations

import json

from laitoxx.core.settings.network_manager import get_session
from laitoxx.features.osint.intelligence.cache import cache

from .. import provider_common as _common
from ..models import Entity, ProviderResult, Relation, TimelineEvent
from ..quota import ledger

USER_AGENT = _common.USER_AGENT
_cached_json = _common._cached_json
_entity_id = _common._entity_id
_now = _common._now
_run = _common._run


def wayback(domain: str) -> ProviderResult:
    def load():
        data, hit = _cached_json(
            "wayback",
            domain,
            "https://web.archive.org/cdx/search/cdx",
            params={
                "url": f"{domain}/*",
                "output": "json",
                "filter": "statuscode:200",
                "collapse": "urlkey",
                "limit": 200,
            },
            ttl=43200,
        )
        rows = data[1:] if isinstance(data, list) and data else []
        events = []
        for row in rows:
            if len(row) > 2:
                stamp = str(row[1])
                iso = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]}Z"
                events.append(TimelineEvent(iso, _now(), "Wayback CDX", "archived", domain, str(row[2]), "high"))
        entities, relations = [], []
        root = _entity_id("domain", domain)
        for row in rows[:200]:
            if len(row) > 2:
                url = str(row[2])
                entities.append(Entity("url", url))
                relations.append(Relation(root, _entity_id("url", url), "archived_url", "Wayback CDX", "high", False))
        return ProviderResult(
            "Wayback CDX", "cached" if hit else "ok", {"captures": rows[:200]}, entities, relations, events
        )

    return _run("Wayback CDX", load)


def commoncrawl(domain: str) -> ProviderResult:
    def load():
        index, hit1 = _cached_json(
            "commoncrawl_index", "current", "https://index.commoncrawl.org/collinfo.json", ttl=86400
        )
        index_id = index[0]["id"]

        def fetch_records():
            event_id = ledger.acquire("commoncrawl")
            response = get_session().get(
                f"https://index.commoncrawl.org/{index_id}-index",
                params={"url": f"{domain}/*", "output": "json", "pageSize": 100},
                headers={"User-Agent": USER_AGENT},
                timeout=25,
            )
            ledger.record_response(event_id, "commoncrawl", response.status_code, response.headers)
            response.raise_for_status()
            records = []
            for line in response.text.splitlines():
                if not line.strip().startswith("{"):
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return records[:200]

        data, hit2 = cache.get_or_set("advanced_web_scanner:commoncrawl", domain, fetch_records, 43200)
        entities, relations, events = [], [], []
        root = _entity_id("domain", domain)
        for record in data:
            url = str(record.get("url", ""))
            if not url:
                continue
            entities.append(Entity("url", url))
            relations.append(Relation(root, _entity_id("url", url), "crawled_url", "Common Crawl", "medium", False))
            stamp = str(record.get("timestamp", ""))
            if len(stamp) >= 14:
                iso = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]}Z"
                events.append(TimelineEvent(iso, _now(), "Common Crawl", "crawled", domain, url, "medium"))
        return ProviderResult(
            "Common Crawl",
            "cached" if hit1 and hit2 else "ok",
            {"index": index_id, "records": data},
            entities,
            relations,
            events,
        )

    return _run("Common Crawl", load)
