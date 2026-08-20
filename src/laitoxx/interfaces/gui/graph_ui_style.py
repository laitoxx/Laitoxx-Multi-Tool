"""Shared visual tokens for graph editor widgets."""

from laitoxx.core.localization.i18n import translator


def _t(key: str, **kwargs) -> str:
    return translator.get(key, **kwargs)


# ===========================================================================
# Design tokens
# ===========================================================================

# Accent colors
_ACCENT = "#c084fc"  # purple
_ACCENT2 = "#f472b6"  # pink
_ACCENT_DIM = "#7c3aed"

# Backgrounds
_BG_DEEP = "#0d0d1a"
_BG_PANEL = "rgba(15, 12, 30, {a})"  # panel with variable alpha
_BG_ITEM = "rgba(255, 255, 255, 0.04)"
_BG_ITEM_SEL = "rgba(192, 132, 252, 0.18)"
_BG_ITEM_HOV = "rgba(255, 255, 255, 0.07)"

# Borders
_BORDER = "rgba(192, 132, 252, 0.25)"
_BORDER_FOCUS = "rgba(192, 132, 252, 0.7)"

# Text
_TEXT_PRI = "#f1f0ff"
_TEXT_SEC = "#a99fc0"
_TEXT_DIM = "#6b6580"

# Toolbar gradient button variants
_BTN_FILE = ("rgba(124,58,237,0.55)", "rgba(139,92,246,0.75)", "#7c3aed")
_BTN_EDIT = ("rgba(14,165,233,0.45)", "rgba(56,189,248,0.65)", "#0ea5e9")
_BTN_DANGER = ("rgba(220,38,38,0.45)", "rgba(239,68,68,0.65)", "#dc2626")
_BTN_EXPORT = ("rgba(5,150,105,0.45)", "rgba(16,185,129,0.65)", "#059669")


def _panel_bg(alpha: float) -> str:
    return _BG_PANEL.format(a=alpha)


__all__ = [
    "_ACCENT",
    "_ACCENT2",
    "_ACCENT_DIM",
    "_BG_DEEP",
    "_BG_ITEM",
    "_BG_ITEM_HOV",
    "_BG_ITEM_SEL",
    "_BG_PANEL",
    "_BORDER",
    "_BORDER_FOCUS",
    "_BTN_DANGER",
    "_BTN_EDIT",
    "_BTN_EXPORT",
    "_BTN_FILE",
    "_TEXT_DIM",
    "_TEXT_PRI",
    "_TEXT_SEC",
    "_panel_bg",
    "_t",
]
