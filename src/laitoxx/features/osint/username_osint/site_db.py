"""Validated site database and search profile selection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from laitoxx.core.settings.paths import PROJECT_ROOT

from .health import ProviderHealthStore
from .models import SITE_CATEGORIES, SiteEntry
from .provider_adapters import apply_public_api_adapter

_DEFAULT_DB_PATH = PROJECT_ROOT / "bd" / "sites_db.json"


@dataclass(frozen=True)
class SiteValidationIssue:
    """One site definition rejected during database validation."""

    site: str
    message: str


class SiteDB:
    """Load, validate, rank and filter username provider definitions."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or _DEFAULT_DB_PATH).resolve()
        self.sites: list[SiteEntry] = []
        self.meta: dict = {}
        self.issues: list[SiteValidationIssue] = []
        self.health = ProviderHealthStore()

    @staticmethod
    def _validation_error(site: SiteEntry) -> str:
        if "{username}" not in site.url_template:
            return "URL template does not contain {username}"
        parsed = urlsplit(site.url_template.replace("{username}", "validation_user"))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "URL template is not an HTTP endpoint"
        if site.url_probe:
            probe = urlsplit(site.url_probe.replace("{username}", "validation_user"))
            if probe.scheme not in {"http", "https"} or not probe.hostname:
                return "Probe URL is not an HTTP endpoint"
        if site.category not in SITE_CATEGORIES:
            return f"Unknown category: {site.category}"
        if not site.valid_status or any(not isinstance(code, int) for code in site.valid_status):
            return "valid_status must contain HTTP status integers"
        if not 1 <= int(site.timeout) <= 120:
            return "Timeout must be between 1 and 120 seconds"
        if site.regex_check:
            try:
                re.compile(site.regex_check)
            except re.error as error:
                return f"Invalid username expression: {error}"
        return ""

    def load(self) -> list[SiteEntry]:
        """Load valid providers while retaining diagnostics for rejected rows."""

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("sites"), dict):
            raise ValueError("Username site database must contain a sites object")
        self.meta = raw.get("meta", {}) if isinstance(raw.get("meta"), dict) else {}
        self.sites = []
        self.issues = []
        seen_templates: dict[str, str] = {}
        for name, data in raw["sites"].items():
            if not isinstance(data, dict):
                self.issues.append(SiteValidationIssue(str(name), "Definition is not an object"))
                continue
            try:
                site = SiteEntry.from_dict(str(name), data)
                site = apply_public_api_adapter(site)
                error = self._validation_error(site)
            except Exception as exc:
                error = str(exc)
                site = None
            if error or site is None:
                self.issues.append(SiteValidationIssue(str(name), error or "Invalid definition"))
                continue
            template_key = site.url_template.casefold()
            duplicate = seen_templates.get(template_key)
            if duplicate:
                self.issues.append(
                    SiteValidationIssue(str(name), f"Duplicate URL template already used by {duplicate}")
                )
                continue
            seen_templates[template_key] = site.name
            self.sites.append(site)
        return self.sites

    def filter_by_category(self, categories: list[str]) -> list[SiteEntry]:
        selected = {category.casefold() for category in categories}
        return [site for site in self.sites if site.category.casefold() in selected]

    def filter_by_tags(self, tags: list[str]) -> list[SiteEntry]:
        selected = {tag.casefold() for tag in tags}
        return [site for site in self.sites if selected.intersection(tag.casefold() for tag in site.tags)]

    @staticmethod
    def _quality_score(site: SiteEntry) -> tuple[int, str]:
        score = 0
        score += 4 if site.url_probe else 0
        score += 3 if site.absence_strs else 0
        score += 3 if site.presense_strs else 0
        score += 2 if site.regex_check else 0
        score += 1 if site.avatar_url else 0
        score += 1 if site.category != "other" else 0
        score -= 10 if site.disabled else 0
        return score, site.name.casefold()

    def select(self, mode: str = "standard", categories: list[str] | None = None) -> list[SiteEntry]:
        """Select a ranked quick, standard, full or custom provider set."""

        candidates = [site for site in self.sites if not site.disabled]
        if categories:
            selected = {category.casefold() for category in categories}
            candidates = [site for site in candidates if site.category.casefold() in selected]
        if mode in {"quick", "standard"}:
            candidates = [site for site in candidates if not self.health.is_degraded(site.name)]
        candidates.sort(key=lambda site: (-self._quality_score(site)[0], self._quality_score(site)[1]))
        limits = {"quick": 120, "standard": 500, "full": len(candidates), "custom": len(candidates)}
        if mode not in limits:
            raise ValueError(f"Unknown username search mode: {mode}")
        return candidates[: limits[mode]]

    def get_categories(self) -> list[str]:
        return sorted({site.category for site in self.sites})

    def count(self) -> int:
        return len(self.sites)

    def health_summary(self) -> dict:
        """Return database validation and provider tier statistics."""

        enabled = [site for site in self.sites if not site.disabled]
        stable = [site for site in enabled if self._quality_score(site)[0] >= 4]
        return {
            "database_version": self.meta.get("version", ""),
            "last_updated": self.meta.get("last_updated", ""),
            "loaded": len(self.sites),
            "enabled": len(enabled),
            "stable": len(stable),
            "experimental": len(enabled) - len(stable),
            "disabled": len(self.sites) - len(enabled),
            "invalid": len(self.issues),
        }
