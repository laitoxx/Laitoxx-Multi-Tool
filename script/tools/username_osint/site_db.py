"""
site_db.py — Load and query the site database (bd/sites_db.json).
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .models import SiteEntry

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "bd", "sites_db.json"
)


class SiteDB:
    """Loads, validates and queries the site database."""

    def __init__(self, path: Optional[str] = None):
        self.path = os.path.abspath(path or _DEFAULT_DB_PATH)
        self.sites: list[SiteEntry] = []
        self.meta: dict = {}

    def load(self) -> list[SiteEntry]:
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.meta = raw.get("meta", {})
        sites_raw = raw.get("sites", {})

        self.sites = []
        for name, data in sites_raw.items():
            try:
                self.sites.append(SiteEntry.from_dict(name, data))
            except Exception:
                continue
        return self.sites

    def filter_by_category(self, categories: list[str]) -> list[SiteEntry]:
        cats = set(c.lower() for c in categories)
        return [s for s in self.sites if s.category.lower() in cats]

    def filter_by_tags(self, tags: list[str]) -> list[SiteEntry]:
        tag_set = set(t.lower() for t in tags)
        return [s for s in self.sites if tag_set & set(t.lower() for t in s.tags)]

    def get_categories(self) -> list[str]:
        return sorted(set(s.category for s in self.sites))

    def count(self) -> int:
        return len(self.sites)
