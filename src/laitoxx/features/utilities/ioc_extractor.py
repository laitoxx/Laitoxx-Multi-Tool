"""Pure IOC/entity extraction shared by GUI workflows and the tool registry."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    kind: str
    value: str

    @property
    def graph_type(self) -> str:
        return {
            "ip": "IP",
            "domain": "Website",
            "url": "Website",
            "email": "Email",
            "phone": "Phone",
            "username": "Username",
            "hash": "Document",
            "jwt": "Document",
        }.get(self.kind, "Custom")


PATTERNS = {
    "url": re.compile(r"https?://[^\s<>\"']+", re.I),
    "email": re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.I),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    "hash": re.compile(r"(?<![A-Fa-f0-9])(?:[A-Fa-f0-9]{64}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{32})(?![A-Fa-f0-9])"),
    "ip": re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    "phone": re.compile(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)"),
    "username": re.compile(r"(?<![\w@])@[A-Za-z0-9_]{3,32}\b"),
    "domain": re.compile(r"(?<![@\w.-])(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\b", re.I),
}


TOOL_BY_KIND = {
    "ip": "Check IP",
    "domain": "Domain Intelligence",
    "url": "Domain Intelligence",
    "email": "Email OSINT",
    "username": "Search Nick",
    "hash": "Hash Identifier",
    "jwt": "JWT Analyzer",
}


def extract_entities(text: str) -> list[Entity]:
    found: list[tuple[int, Entity]] = []
    occupied: list[tuple[int, int]] = []
    for kind in ("url", "email", "jwt", "hash", "ip", "phone", "username", "domain"):
        for match in PATTERNS[kind].finditer(text or ""):
            if any(match.start() < end and match.end() > start for start, end in occupied):
                continue
            value = match.group(0).rstrip(".,;:!?)]") if kind == "url" else match.group(0)
            if kind == "ip":
                try:
                    ipaddress.ip_address(value)
                except ValueError:
                    continue
            if kind == "phone":
                value = re.sub(r"[^\d+]", "", value)
            found.append((match.start(), Entity(kind, value)))
            occupied.append((match.start(), match.end()))
    result: list[Entity] = []
    seen = set()
    for _, entity in sorted(found, key=lambda item: item[0]):
        key = (entity.kind, entity.value.lower())
        if key not in seen:
            seen.add(key)
            result.append(entity)
    return result


def ioc_extractor_tool(text: str | None = None):
    if text is None:
        text = input()
    entities = extract_entities(text)
    if not entities:
        print("No indicators found.")
        return []
    for entity in entities:
        print(f"[{entity.kind.upper()}] {entity.value}")
    return entities
