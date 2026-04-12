"""Background file helpers: scan resources/background, copy files in."""
from __future__ import annotations

import os
import shutil

from .paths import BACKGROUND_DIR, DEFAULT_BG_FILE

SUPPORTED_EXT = {".gif", ".mp4", ".avi"}


def list_backgrounds() -> list[tuple[str, str]]:
    """Return [(display_name, filepath), ...] for all backgrounds in BACKGROUND_DIR."""
    os.makedirs(BACKGROUND_DIR, exist_ok=True)
    items = []
    for fname in sorted(os.listdir(BACKGROUND_DIR)):
        _, ext = os.path.splitext(fname.lower())
        if ext in SUPPORTED_EXT:
            name = os.path.splitext(fname)[0].replace("_", " ").title()
            items.append((name, os.path.join(BACKGROUND_DIR, fname)))
    return items


def import_background(src_path: str) -> str:
    """Copy *src_path* into resources/background/ and return the new path.

    If a file with the same name already exists, it is overwritten.
    """
    os.makedirs(BACKGROUND_DIR, exist_ok=True)
    fname = os.path.basename(src_path)
    dest = os.path.join(BACKGROUND_DIR, fname)
    shutil.copy2(src_path, dest)
    return dest


def default_background() -> str:
    return DEFAULT_BG_FILE
