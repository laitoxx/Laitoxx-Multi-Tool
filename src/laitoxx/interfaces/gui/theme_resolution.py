"""Shared semantic QSS for the Laitoxx desktop workspace."""

from __future__ import annotations

import re

from laitoxx.core.settings.theme import DEFAULT_THEME

STYLE_MODES = {
    "glass": "Glass",
    "metallic": "Metallic",
    "glitch": "Glitch",
    "solid": "Solid",
}


def _rgb(value: str, fallback=(24, 24, 24)) -> tuple[int, int, int]:
    """Read the colour formats used by legacy theme JSON files."""
    value = str(value or "").strip()
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) in {3, 4}:
            raw = "".join(ch * 2 for ch in raw[:3])
        if len(raw) >= 6:
            try:
                return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                pass
    values = re.findall(r"[\d.]+", value)
    if len(values) >= 3:
        return tuple(max(0, min(255, int(float(part)))) for part in values[:3])
    return fallback


def _mix(first: str, second: str, amount: float, alpha: float = 1.0) -> str:
    a, b = _rgb(first), _rgb(second)
    rgb = tuple(round(a[i] * (1.0 - amount) + b[i] * amount) for i in range(3))
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha:.3f})"


def _contrast_text(background: str) -> str:
    r, g, b = _rgb(background)
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return "#171a1c" if luminance > 0.58 else "#f0f2f3"


def _derive_semantic_tokens(data: dict) -> None:
    """Map every legacy colour theme onto the shared semantic vocabulary.

    Existing theme JSON files predate semantic tokens.  Deriving these values
    here prevents the design system's fallback palette from leaking into a
    user-selected theme.
    """
    window = data.get("window_bg_color", data.get("text_area_bg_color", "rgba(10,10,10,0.96)"))
    panel = data.get("panel_bg_color", data.get("sidebar_bg_color", window))
    field = data.get("text_area_bg_color", window)
    accent = data.get("accent_color", data.get("title_text_color", "#ffffff"))
    neutral = _contrast_text(window)
    primary = data.get("semantic_text_primary_color", neutral)
    secondary = data.get("semantic_text_secondary_color", _mix(window, primary, 0.72))
    muted = data.get("semantic_text_muted_color", _mix(window, primary, 0.50))

    defaults = dict(
        surface_base_color=window,
        surface_glass_color=data.get("sidebar_bg_color", panel),
        surface_raised_color=panel,
        surface_input_color=field,
        # Terminals, tables, lists and code editors use the translucent text
        # surface. Graph/map canvases keep their explicit opaque colours.
        surface_work_color=field,
        surface_overlay_color=window,
        surface_hover_color=data.get("button_hover_bg_color", panel),
        surface_pressed_color=data.get("button_pressed_bg_color", panel),
        text_primary_color=primary,
        text_secondary_color=secondary,
        text_muted_color=muted,
        border_subtle_color=_mix(window, primary, 0.18, 0.72),
        border_strong_color=_mix(window, primary, 0.30, 0.82),
        accent_soft_color=_mix(panel, accent, 0.18, 0.92),
        accent_hover_color=data.get("button_hover_bg_color", accent),
        accent_text_color=_contrast_text(accent),
        success_color=data.get("success_color", accent),
        warning_color=data.get("warning_color", accent),
        danger_color=data.get("danger_color", accent),
    )
    # Explicit semantic values in newer themes always win. Legacy colour keys
    # remain untouched, so opening and saving an old theme is lossless.
    for key, value in defaults.items():
        data.setdefault(key, value)
    # This legacy key is also the modern selector name; normalize it unless a
    # dedicated semantic override was supplied by the theme.
    data["text_secondary_color"] = secondary


def _apply_style_mode(data: dict) -> None:
    mode = data.get("style_mode", "glass")
    # These tokens alter material and geometry, while all palette colours stay
    # owned by the selected colour theme.
    profiles = {
        "glass": dict(radius_delta=0, edge_width=1, edge_style="solid", material="glass"),
        "metallic": dict(radius_delta=-5, edge_width=1, edge_style="solid", material="metallic"),
        "glitch": dict(radius_delta=-8, edge_width=2, edge_style="solid", material="glitch"),
        "solid": dict(radius_delta=-3, edge_width=1, edge_style="solid", material="solid"),
    }
    data.update(profiles.get(mode, profiles["glass"]))


def resolved_theme(theme: dict | None = None) -> dict:
    """Return a complete theme, including tokens absent from legacy JSON files."""
    data = DEFAULT_THEME.copy()
    data.update(theme or {})
    _derive_semantic_tokens(data)
    _apply_style_mode(data)
    return data
