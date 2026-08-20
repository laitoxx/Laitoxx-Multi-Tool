"""Central definitions for immutable assets and writable runtime data."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _default_data_dir() -> Path:
    override = os.getenv("LAITOXX_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "Laitoxx"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Laitoxx"
    return Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "laitoxx"


DATA_DIR = _default_data_dir()
SETTINGS_DIR = DATA_DIR / "settings"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"
REPORTS_DIR = DATA_DIR / "reports"
GRAPHS_DIR = DATA_DIR / "graphs"
THEMES_DIR = DATA_DIR / "themes"
BACKGROUND_DIR = DATA_DIR / "backgrounds"
TOOLS_DIR = DATA_DIR / "tools"
APP_SETTINGS_FILE = SETTINGS_DIR / "app_settings.json"
TOS_FILE = SETTINGS_DIR / "tos_accepted.txt"
LUA_PLUGIN_SETTINGS_FILE = SETTINGS_DIR / "lua_plugins.json"
OSINT_CACHE_FILE = CACHE_DIR / "osint.sqlite"

# Immutable packaged assets remain inside the installation tree.
RESOURCES_DIR = PROJECT_ROOT / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
BUNDLED_THEMES_DIR = RESOURCES_DIR / "themes"
BUNDLED_BACKGROUND_DIR = RESOURCES_DIR / "background"
DEFAULT_THEME_FILE = BUNDLED_THEMES_DIR / "default.json"
DEFAULT_BG_FILE = BUNDLED_BACKGROUND_DIR / "background0.gif"


def ensure_runtime_dirs() -> None:
    """Create every application-owned writable directory."""
    for directory in (
        SETTINGS_DIR,
        CACHE_DIR,
        LOGS_DIR,
        REPORTS_DIR,
        GRAPHS_DIR,
        THEMES_DIR,
        BACKGROUND_DIR,
        TOOLS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
