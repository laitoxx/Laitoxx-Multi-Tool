"""
Lua Plugin Builder - code editor with syntax highlighting, code snippets,
syntax checking, and OS-dependent template generation.
"""

from PyQt6.QtGui import (
    QFont,
)
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme

# ============================================================================
# Lua Syntax Highlighter
# ============================================================================
from .plugin_snippets import CODE_SNIPPETS


class SnippetInsertDialog(QDialog):
    """Dialog to configure and insert a code snippet."""

    def __init__(self, parent, snippet_key: str):
        super().__init__(parent)
        snippet = CODE_SNIPPETS[snippet_key]
        self.snippet = snippet
        self.setWindowTitle(snippet["label"])
        self.setMinimumWidth(450)
        self._theme = resolved_theme(getattr(parent, "_theme", {}))
        self.setStyleSheet(
            build_workspace_qss(self._theme) + f"QDialog {{ background: {self._theme['surface_base_color']}; }}"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(snippet["description"]))

        self._field_widgets = {}
        if snippet["fields"]:
            form = QFormLayout()
            for field in snippet["fields"]:
                w = QLineEdit()
                w.setPlaceholderText(field.get("placeholder", ""))
                form.addRow(field["label"] + ":", w)
                self._field_widgets[field["key"]] = w
            layout.addLayout(form)

        # Preview
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 10))
        self.preview.setMaximumHeight(200)
        self.preview.setStyleSheet(
            f"background: {self._theme['surface_work_color']}; color: {self._theme['text_primary_color']};"
            f"border: 1px solid {self._theme['border_subtle_color']};"
        )
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.preview)

        # Update preview on field changes
        for w in self._field_widgets.values():
            w.textChanged.connect(self._update_preview)
        self._update_preview()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_preview(self):
        self.preview.setText(self.get_code())

    def get_code(self) -> str:
        code = self.snippet["template"]
        for key, widget in self._field_widgets.items():
            value = widget.text() or widget.placeholderText()
            code = code.replace(f"{{{key}}}", value)
        return code
