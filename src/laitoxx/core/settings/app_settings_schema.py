"""Central application settings - persisted as a single JSON file.

Paths for theme_path and background_path are stored as paths relative to the
project root so the settings file remains portable when the archive is shared.
Absolute paths that point outside the project tree (e.g. from a previous
user's machine) are silently replaced with the appropriate default.
"""

from __future__ import annotations

import os

from .paths import (
    DATA_DIR,
    DEFAULT_BG_FILE,
    DEFAULT_THEME_FILE,
    PROJECT_ROOT,
)

_PROJECT_ROOT = str(PROJECT_ROOT)


def _to_relative(path: str) -> str:
    """Convert *path* to a path relative to the project root.

    If the path is already relative, it is returned unchanged.
    If it is absolute but points inside the project tree, it is made relative.
    """
    if not os.path.isabs(path):
        return path
    try:
        return os.path.relpath(path, _PROJECT_ROOT)
    except ValueError:
        # On Windows relpath raises ValueError across drives
        return path


def _to_absolute(path: str) -> str:
    """Resolve *path* to an absolute path anchored at the project root."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(_PROJECT_ROOT, path))


def _is_allowed_asset_path(path: str) -> bool:
    """Allow packaged assets and application-owned user assets."""
    abs_path = _to_absolute(path)
    for root in (_PROJECT_ROOT, str(DATA_DIR)):
        try:
            if not os.path.relpath(abs_path, root).startswith(".."):
                return True
        except ValueError:
            continue
    return False


_DEFAULTS: dict = {
    "open_website_on_startup": True,
    "performance_mode": False,
    "language": "en",
    "theme_path": _to_relative(DEFAULT_THEME_FILE),
    "background_path": _to_relative(DEFAULT_BG_FILE),
    "proxy": {
        "enabled": False,
        "type": "http",  # "http", "https", "socks5"
        "host": "",
        "port": "",
        "username": "",
        "password": "",
    },
    "favorite_themes": [],
    "auto_theme_schedule": False,
    "day_theme": "",
    "night_theme": "",
    "day_start": 8,
    "night_start": 20,
    "advanced_web_scanner": {},
    "tongue": {},
    "style_mode": "glass",
    "font_family": "Segoe UI",
    "code_font_family": "Cascadia Mono",
    "font_size": 13,
}
