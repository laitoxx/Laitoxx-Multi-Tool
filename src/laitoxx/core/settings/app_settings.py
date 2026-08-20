"""Central application settings - persisted as a single JSON file.

Paths for theme_path and background_path are stored as paths relative to the
project root so the settings file remains portable when the archive is shared.
Absolute paths that point outside the project tree (e.g. from a previous
user's machine) are silently replaced with the appropriate default.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy

from .app_settings_schema import _DEFAULTS, _is_allowed_asset_path, _to_absolute, _to_relative
from .paths import (
    APP_SETTINGS_FILE,
    DEFAULT_BG_FILE,
    DEFAULT_THEME_FILE,
)


class AppSettings:
    """Singleton-style settings object. Call ``load()`` once at startup."""

    def __init__(self):
        self._data: dict = {}
        self.load()

    # ── Persistence ────────────────────────────────────────────────────────────

    def load(self):
        """Load settings from the application data directory."""
        if os.path.exists(APP_SETTINGS_FILE):
            try:
                with open(APP_SETTINGS_FILE, encoding="utf-8") as f:
                    on_disk = json.load(f)
            except (OSError, json.JSONDecodeError):
                on_disk = {}
        else:
            on_disk = {}

        # Merge with defaults so new keys appear automatically
        self._data = _deep_merge(_DEFAULTS, on_disk)

        # Validate resource paths - replace stale absolute paths from another
        # machine with the project-relative defaults.
        for key, default in (
            ("theme_path", DEFAULT_THEME_FILE),
            ("background_path", DEFAULT_BG_FILE),
        ):
            raw = self._data.get(key, "")
            if raw and not _is_allowed_asset_path(raw):
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

    def reset_to_defaults(self) -> list[str]:
        """Replace persisted settings with a clean defaults copy."""
        self._data = deepcopy(_DEFAULTS)
        self.save()
        return []

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

    @property
    def favorite_themes(self) -> list:
        return list(self._data.get("favorite_themes", []))

    @favorite_themes.setter
    def favorite_themes(self, value: list):
        self._data["favorite_themes"] = list(value)
        self.save()

    @property
    def auto_theme_schedule(self) -> bool:
        return bool(self._data.get("auto_theme_schedule", False))

    @auto_theme_schedule.setter
    def auto_theme_schedule(self, value: bool):
        self._data["auto_theme_schedule"] = bool(value)
        self.save()

    @property
    def day_theme(self) -> str:
        return self._data.get("day_theme", "")

    @day_theme.setter
    def day_theme(self, value: str):
        self._data["day_theme"] = value
        self.save()

    @property
    def night_theme(self) -> str:
        return self._data.get("night_theme", "")

    @night_theme.setter
    def night_theme(self, value: str):
        self._data["night_theme"] = value
        self.save()

    @property
    def day_start(self) -> int:
        return int(self._data.get("day_start", 8))

    @day_start.setter
    def day_start(self, value: int):
        self._data["day_start"] = int(value)
        self.save()

    @property
    def night_start(self) -> int:
        return int(self._data.get("night_start", 20))

    @night_start.setter
    def night_start(self, value: int):
        self._data["night_start"] = int(value)
        self.save()

    @property
    def advanced_web_scanner(self) -> dict:
        return dict(self._data.get("advanced_web_scanner", {}))

    @advanced_web_scanner.setter
    def advanced_web_scanner(self, value: dict):
        self._data["advanced_web_scanner"] = dict(value)
        self.save()

    @property
    def tongue(self) -> dict:
        return dict(self._data.get("tongue", {}))

    @tongue.setter
    def tongue(self, value: dict):
        self._data["tongue"] = dict(value)
        self.save()

    @property
    def style_mode(self) -> str:
        value = self._data.get("style_mode", "glass")
        legacy = {"soft": "metallic", "contrast": "glitch"}
        value = legacy.get(value, value)
        return value if value in {"glass", "metallic", "glitch", "solid"} else "glass"

    @style_mode.setter
    def style_mode(self, value: str):
        self._data["style_mode"] = value
        self.save()

    @property
    def font_family(self) -> str:
        return str(self._data.get("font_family", "Segoe UI"))

    @font_family.setter
    def font_family(self, value: str):
        self._data["font_family"] = value or "Segoe UI"
        self.save()

    @property
    def font_size(self) -> int:
        return max(10, min(18, int(self._data.get("font_size", 13))))

    @font_size.setter
    def font_size(self, value: int):
        self._data["font_size"] = max(10, min(18, int(value)))
        self.save()

    @property
    def code_font_family(self) -> str:
        return str(self._data.get("code_font_family", "Cascadia Mono"))

    @code_font_family.setter
    def code_font_family(self, value: str):
        self._data["code_font_family"] = value or "Cascadia Mono"
        self.save()


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*."""
    result = deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


settings = AppSettings()
