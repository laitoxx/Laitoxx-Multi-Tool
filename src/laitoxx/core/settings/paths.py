"""Central path definitions for all settings and resource files."""

import os

from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent.parent)


def _rel(*parts) -> str:
    return os.path.join(_ROOT, *parts)


# ── Settings files ────────────────────────────────────────────────────────────
SETTINGS_DIR = _rel("settings")
APP_SETTINGS_FILE = _rel("settings", "app_settings.json")

# ── Resources ─────────────────────────────────────────────────────────────────
RESOURCES_DIR = _rel("resources")
ICONS_DIR = _rel("resources", "icons")
THEMES_DIR = _rel("resources", "themes")
BACKGROUND_DIR = _rel("resources", "background")

# ── Legacy config files (kept for migration / compatibility) ──────────────────
LEGACY_BG_CONFIG = _rel("background_config.txt")
LEGACY_THEME_CONFIG = _rel("last_theme.txt")
LEGACY_AGREEMENT = _rel("user_agreement_accepted.txt")
LEGACY_LUA_SETTINGS = _rel("lua_plugin_settings.json")
TOS_FILE = _rel("settings", "tos_accepted.txt")

# ── Default files ─────────────────────────────────────────────────────────────
DEFAULT_THEME_FILE = _rel("resources", "themes", "default.json")
DEFAULT_BG_FILE = _rel("resources", "background", "background0.gif")


def ensure_resource_dirs():
    """Create resource directories if they don't exist."""
    for d in (THEMES_DIR, BACKGROUND_DIR, ICONS_DIR):
        os.makedirs(d, exist_ok=True)
