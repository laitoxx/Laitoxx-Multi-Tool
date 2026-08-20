"""Pure aggregation helpers for wallet and graph reports."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from .primitives import short


def dedupe_dicts(rows: Iterable[dict[str, Any]], key_func) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = str(key_func(row))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def get_token_info(metadata: Mapping[str, Any], address: str) -> dict[str, Any] | None:
    entry = metadata.get(address) if isinstance(metadata, Mapping) else None
    if not isinstance(entry, Mapping):
        return None
    infos = entry.get("token_info") or []
    if not isinstance(infos, list) or not infos:
        return None
    valid = [x for x in infos if isinstance(x, Mapping) and x.get("valid") is not False]
    return dict((valid or infos)[0]) if isinstance((valid or infos)[0], Mapping) else None


def address_label(address: str, address_book: Mapping[str, Any], known_labels: Mapping[str, Any]) -> str:
    local = known_labels.get(address)
    if isinstance(local, str):
        return local
    if isinstance(local, Mapping):
        return str(local.get("label") or local.get("name") or short(address))
    entry = address_book.get(address) if isinstance(address_book, Mapping) else None
    if isinstance(entry, Mapping):
        domain = entry.get("domain")
        friendly = entry.get("user_friendly")
        interfaces = entry.get("interfaces")
        if domain:
            return str(domain)
        if friendly and friendly != address:
            return short(str(friendly), 9, 6)
        if interfaces:
            return f"{short(address)} [{','.join(map(str, interfaces[:2]))}]"
    return short(address)


def summarize_traces(traces: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    action_types: Counter[str] = Counter()
    accounts: Counter[str] = Counter()
    successful = 0
    failed = 0
    for trace in traces:
        actions = trace.get("actions") or []
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, Mapping):
                continue
            details = action.get("details")
            action_type = "unknown"
            if isinstance(details, Mapping):
                action_type = str(details.get("type") or details.get("action_type") or "unknown")
            elif details is not None:
                action_type = type(details).__name__
            action_types[action_type] += 1
            for account in action.get("accounts") or []:
                accounts[str(account)] += 1
            if action.get("success") is False:
                failed += 1
            else:
                successful += 1
    return {
        "actions_total": successful + failed,
        "actions_successful": successful,
        "actions_failed": failed,
        "action_types": dict(action_types.most_common()),
        "most_involved_accounts": accounts.most_common(25),
    }
