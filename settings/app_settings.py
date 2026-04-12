"""Central application settings — persisted as a single JSON file.

Paths for theme_path and background_path are stored as paths relative to the
project root so the settings file remains portable when the archive is shared.
Absolute paths that point outside the project tree (e.g. from a previous
user's machine) are silently replaced with the appropriate default.
"""
from __future__ import annotations

import json
import os

from .paths import (
    APP_SETTINGS_FILE, DEFAULT_THEME_FILE, DEFAULT_BG_FILE,
    LEGACY_BG_CONFIG, LEGACY_THEME_CONFIG,
)

# Project root — same anchor used by paths.py
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _to_relative(path: str) -> str:
    """Convert *path* to a path relative to the project root.

    If the path is already relative, it is returned unchanged.
    If it is absolute but points inside the project tree, it is made relative.
    """
    if not os.path.isabs(path):
        return path
    try:
        return os.path.relpath(path, _ROOT)
    except ValueError:
        # On Windows relpath raises ValueError across drives
        return path


def _to_absolute(path: str) -> str:
    """Resolve *path* to an absolute path anchored at the project root."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(_ROOT, path))


def _is_inside_project(path: str) -> bool:
    """Return True if *path* resolves to somewhere inside the project tree."""
    abs_path = _to_absolute(path)
    try:
        rel = os.path.relpath(abs_path, _ROOT)
        # relpath starts with '..' when the path escapes the project root
        return not rel.startswith("..")
    except ValueError:
        # ValueError on Windows means different drives — definitely outside
        return False


_DEFAULTS: dict = {
    "open_website_on_startup": True,
    "performance_mode": False,
    "language": "en",
    "theme_path": _to_relative(DEFAULT_THEME_FILE),
    "background_path": _to_relative(DEFAULT_BG_FILE),
    "proxy": {
        "enabled": False,
        "type": "http",      # "http", "https", "socks5"
        "host": "",
        "port": "",
        "username": "",
        "password": "",
    },
}


class AppSettings:
    """Singleton-style settings object. Call ``load()`` once at startup."""

    def __init__(self):
        self._data: dict = {}
        self.load()

    # ── Persistence ────────────────────────────────────────────────────────────

    def load(self):
        """Load from disk, migrating legacy files when needed."""
        if os.path.exists(APP_SETTINGS_FILE):
            try:
                with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    on_disk = json.load(f)
            except (json.JSONDecodeError, IOError):
                on_disk = {}
        else:
            on_disk = self._migrate_from_legacy()

        # Merge with defaults so new keys appear automatically
        self._data = _deep_merge(_DEFAULTS, on_disk)

        # Validate resource paths — replace stale absolute paths from another
        # machine with the project-relative defaults.
        for key, default in (("theme_path", DEFAULT_THEME_FILE),
                             ("background_path", DEFAULT_BG_FILE)):
            raw = self._data.get(key, "")
            if raw and not _is_inside_project(raw):
                self._data[key] = _to_relative(default)

        # Normalise to relative storage format
        for key in ("theme_path", "background_path"):
            if self._data.get(key):
                self._data[key] = _to_relative(self._data[key])

        self.save()

    def save(self):
        """Persist settings. Paths are stored as project-relative strings."""
        os.makedirs(os.path.dirname(APP_SETTINGS_FILE), exist_ok=True)
        # Store a serialisable copy with relative paths
        data_to_write = dict(self._data)
        for key in ("theme_path", "background_path"):
            if data_to_write.get(key):
                data_to_write[key] = _to_relative(data_to_write[key])
        with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_write, f, indent=4, ensure_ascii=False)

    # ── Accessors ──────────────────────────────────────────────────────────────

    @property
    def open_website_on_startup(self) -> bool:
        return bool(self._data.get("open_website_on_startup", True))

    @open_website_on_startup.setter
    def open_website_on_startup(self, value: bool):
        self._data["open_website_on_startup"] = value
        self.save()

    @property
    def performance_mode(self) -> bool:
        return bool(self._data.get("performance_mode", False))

    @performance_mode.setter
    def performance_mode(self, value: bool):
        self._data["performance_mode"] = bool(value)
        self.save()

    @property
    def language(self) -> str:
        return self._data.get("language", "en")

    @language.setter
    def language(self, value: str):
        self._data["language"] = value
        self.save()

    @property
    def theme_path(self) -> str:
        """Absolute path to the active theme file."""
        raw = self._data.get("theme_path", "")
        return _to_absolute(raw) if raw else DEFAULT_THEME_FILE

    @theme_path.setter
    def theme_path(self, value: str):
        self._data["theme_path"] = _to_relative(value)
        self.save()

    @property
    def background_path(self) -> str:
        """Absolute path to the active background file."""
        raw = self._data.get("background_path", "")
        return _to_absolute(raw) if raw else ""

    @background_path.setter
    def background_path(self, value: str):
        self._data["background_path"] = _to_relative(value) if value else ""
        self.save()

    @property
    def proxy(self) -> dict:
        return dict(self._data.get("proxy", {}))

    @proxy.setter
    def proxy(self, value: dict):
        self._data["proxy"] = value
        self.save()

    # ── Migration ──────────────────────────────────────────────────────────────

    def _migrate_from_legacy(self) -> dict:
        """Build initial settings from old scattered config files."""
        migrated: dict = {}

        # last_theme.txt
        if os.path.exists(LEGACY_THEME_CONFIG):
            with open(LEGACY_THEME_CONFIG, "r", encoding="utf-8") as f:
                p = f.read().strip()
            if p:
                migrated["theme_path"] = p

        # background_config.txt
        if os.path.exists(LEGACY_BG_CONFIG):
            with open(LEGACY_BG_CONFIG, "r", encoding="utf-8") as f:
                p = f.read().strip()
            if p:
                migrated["background_path"] = p

        return migrated


# ── Helpers ────────────────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# Global instance
settings = AppSettings()
