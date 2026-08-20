"""Composition root for ThemeEditorDialog."""
# ruff: noqa: F405

from .theme_editor_context import *  # noqa: F403
from .theme_editor_part1 import ThemeEditorDialogMixin1
from .theme_editor_part2 import ThemeEditorDialogMixin2
from .theme_editor_part3 import ThemeEditorDialogMixin3
from .theme_editor_part4 import ThemeEditorDialogMixin4


class ThemeEditorDialog(
    ThemeEditorDialogMixin1, ThemeEditorDialogMixin2, ThemeEditorDialogMixin3, ThemeEditorDialogMixin4, QDialog
):
    def __init__(self, parent, current_theme: dict):
        super().__init__(parent)
        self.setWindowTitle(translator.get("theme_editor_title"))
        self.setMinimumSize(960, 600)
        self.resize(1100, 680)

        self.theme_data = current_theme.copy()
        self.original_theme = current_theme.copy()
        self._current_key: str | None = None
        self._updating_hex = False
        self._last_palette: list[QColor] = []
        self._colorblind_mode: str = "none"
        self._preview_dark: bool = True
        self._eyedropper: _EyedropperOverlay | None = None

        # build flat ordered list  key → display label
        catalogs = translator.translations
        english_map = catalogs.get("en", {}).get("theme_map", {})
        local_map = catalogs.get(translator.lang, {}).get("theme_map", {})
        self._theme_map: dict[str, str] = dict(english_map) if isinstance(english_map, dict) else {}
        if isinstance(local_map, dict):
            self._theme_map.update(local_map)

        # Update module tokens so _populate_list uses correct accent colour
        import laitoxx.interfaces.gui.theme_editor as _self_mod

        semantic_theme = resolved_theme(current_theme)
        _self_mod._ACCENT = semantic_theme.get("accent_color", _ACCENT)
        _self_mod._TEXT = semantic_theme.get("text_primary_color", _TEXT)
        _self_mod._TEXT_DIM = semantic_theme.get("text_secondary_color", _TEXT_DIM)
        _self_mod._BORDER = current_theme.get("border_color", current_theme.get("button_border_color", _BORDER))

        self._build_ui()
        resolved = resolved_theme(current_theme)
        self.setStyleSheet(_build_dialog_ss(resolved) + build_workspace_qss(resolved))
        self._restyle_panels(current_theme)
        self._populate_list()
        self._populate_library()
        # select first item
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
