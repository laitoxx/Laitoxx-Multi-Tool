"""Shared pytest fixtures."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_themes_dir(tmp_path: Path) -> Path:
    """Temporary directory that looks like THEMES_DIR."""
    d = tmp_path / "themes"
    d.mkdir()
    return d


@pytest.fixture()
def sample_theme() -> dict:
    """Minimal valid theme dict."""
    return {
        "accent_color": "#ff4444",
        "button_bg_color": "rgba(255,0,0,0.1)",
        "border_radius": 10,
    }


@pytest.fixture()
def tmp_theme_file(tmp_path: Path, sample_theme: dict) -> Path:
    """A theme JSON file on disk."""
    f = tmp_path / "my_theme.json"
    f.write_text(json.dumps(sample_theme), encoding="utf-8")
    return f
