"""Unit tests for theme.py — load/save/list operations."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from laitoxx.core.settings.theme import (
    DEFAULT_THEME,
    load_theme,
    save_theme,
    save_theme_to_resources,
)


class TestDefaultTheme:
    def test_has_required_keys(self):
        required = {
            "accent_color", "button_bg_color", "button_text_color",
            "text_area_bg_color", "window_bg_color", "border_radius",
        }
        assert required.issubset(DEFAULT_THEME.keys())

    def test_border_radius_is_int(self):
        assert isinstance(DEFAULT_THEME["border_radius"], int)

    def test_border_radius_sensible(self):
        assert 0 <= DEFAULT_THEME["border_radius"] <= 50

    def test_accent_color_is_string(self):
        assert isinstance(DEFAULT_THEME["accent_color"], str)

    def test_no_none_values(self):
        for k, v in DEFAULT_THEME.items():
            assert v is not None, f"DEFAULT_THEME['{k}'] is None"


class TestLoadTheme:
    def test_load_valid_file(self, tmp_theme_file: Path, sample_theme: dict):
        result = load_theme(str(tmp_theme_file))
        assert result == sample_theme

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        result = load_theme(str(tmp_path / "ghost.json"))
        assert result is None

    def test_load_invalid_json_returns_none(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not valid json }", encoding="utf-8")
        assert load_theme(str(bad)) is None

    def test_load_empty_file_returns_none(self, tmp_path: Path):
        empty = tmp_path / "empty.json"
        empty.write_text("", encoding="utf-8")
        assert load_theme(str(empty)) is None

    def test_loaded_data_is_dict(self, tmp_theme_file: Path):
        result = load_theme(str(tmp_theme_file))
        assert isinstance(result, dict)


class TestSaveTheme:
    def test_save_creates_file(self, tmp_path: Path, sample_theme: dict):
        path = str(tmp_path / "out.json")
        save_theme(path, sample_theme)
        assert os.path.exists(path)

    def test_save_roundtrip(self, tmp_path: Path, sample_theme: dict):
        path = str(tmp_path / "out.json")
        save_theme(path, sample_theme)
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        assert loaded == sample_theme

    def test_save_creates_intermediate_dirs(self, tmp_path: Path, sample_theme: dict):
        path = str(tmp_path / "a" / "b" / "theme.json")
        save_theme(path, sample_theme)
        assert os.path.exists(path)

    def test_save_overwrites_existing(self, tmp_theme_file: Path):
        new_data = {"accent_color": "#00ff00", "border_radius": 5}
        save_theme(str(tmp_theme_file), new_data)
        loaded = load_theme(str(tmp_theme_file))
        assert loaded == new_data


class TestSaveThemeToResources:
    def test_saves_and_returns_path(self, tmp_path: Path, sample_theme: dict):
        with patch("laitoxx.core.settings.theme.THEMES_DIR", str(tmp_path)):
            path = save_theme_to_resources("My Theme", sample_theme)
        assert os.path.exists(path)
        assert path.endswith(".json")

    def test_name_normalisation(self, tmp_path: Path, sample_theme: dict):
        with patch("laitoxx.core.settings.theme.THEMES_DIR", str(tmp_path)):
            path = save_theme_to_resources("My Cool Theme", sample_theme)
        assert "my_cool_theme" in os.path.basename(path)

    def test_empty_name_uses_custom(self, tmp_path: Path, sample_theme: dict):
        with patch("laitoxx.core.settings.theme.THEMES_DIR", str(tmp_path)):
            path = save_theme_to_resources("", sample_theme)
        assert "custom" in os.path.basename(path)

    def test_content_is_correct(self, tmp_path: Path, sample_theme: dict):
        with patch("laitoxx.core.settings.theme.THEMES_DIR", str(tmp_path)):
            path = save_theme_to_resources("test", sample_theme)
        loaded = load_theme(path)
        assert loaded == sample_theme
