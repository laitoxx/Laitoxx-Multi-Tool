"""Theme helpers: scan resources/themes, load, save."""
from __future__ import annotations

import json
import os

from .paths import THEMES_DIR, DEFAULT_THEME_FILE


DEFAULT_THEME: dict = {
    "button_bg_color": "rgba(255, 0, 0, 0.1)",
    "button_hover_bg_color": "rgba(255, 0, 0, 0.2)",
    "button_pressed_bg_color": "rgba(255, 0, 0, 0.3)",
    "button_border_color": "rgba(255, 255, 255, 0.2)",
    "button_text_color": "white",
    "text_area_bg_color": "rgba(0, 0, 0, 0.5)",
    "text_area_border_color": "rgba(255, 255, 255, 0.2)",
    "text_area_text_color": "white",
    "sidebar_bg_color": "rgba(0, 0, 0, 0.2)",
    "title_text_color": "white",
    "scrollbar_handle_color": "rgba(255, 255, 255, 0.4)",
    "scrollbar_handle_hover_color": "rgba(255, 255, 255, 0.6)",
    "plugin_canvas_bg_color": "#2d3436",
    # ── Windows (Terminal, Graph Editor, Nick Search) ──────────────────────
    "accent_color": "#ff4444",
    "accent_dim_color": "#cc2222",
    "window_bg_color": "rgba(10, 5, 5, 0.92)",
    "panel_bg_color": "rgba(20, 8, 8, 0.80)",
    "border_color": "rgba(255, 68, 68, 0.30)",
    "text_secondary_color": "#cc9999",
}


def list_themes() -> list[tuple[str, str]]:
    """Return [(display_name, filepath), ...] for all themes in THEMES_DIR."""
    os.makedirs(THEMES_DIR, exist_ok=True)
    themes = []
    for fname in sorted(os.listdir(THEMES_DIR)):
        if fname.lower().endswith(".json"):
            name = os.path.splitext(fname)[0].replace("_", " ").title()
            themes.append((name, os.path.join(THEMES_DIR, fname)))
    return themes


def load_theme(filepath: str) -> dict | None:
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return None


def save_theme(filepath: str, theme_data: dict):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(theme_data, f, indent=4)


def save_theme_to_resources(name: str, theme_data: dict) -> str:
    """Save a theme JSON into resources/themes/ and return its path."""
    os.makedirs(THEMES_DIR, exist_ok=True)
    safe_name = name.strip().replace(" ", "_").lower() or "custom"
    filepath = os.path.join(THEMES_DIR, f"{safe_name}.json")
    save_theme(filepath, theme_data)
    return filepath


def load_default_theme() -> dict:
    data = load_theme(DEFAULT_THEME_FILE)
    base = DEFAULT_THEME.copy()
    if data:
        base.update(data)
    return base
