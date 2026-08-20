from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons


class LuaPluginInputDialog(QDialog):
    """Dialog to collect input for a Lua plugin execution."""

    def __init__(self, parent=None, plugin_meta=None):
        super().__init__(parent)
        self.plugin_meta = plugin_meta
        self.setWindowTitle(plugin_meta.name if plugin_meta else "Lua Plugin")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        if plugin_meta:
            info = QLabel(
                f"{plugin_meta.name} v{plugin_meta.version}\nby {plugin_meta.author}\n\n{plugin_meta.description}"
            )
            info.setWordWrap(True)
            layout.addWidget(info)

        form = QFormLayout()
        self.query_input = QLineEdit()
        prompt_map = {
            "search": "Enter search query:",
            "processor": "Paste text to process:",
            "formatter": "Paste data to format:",
            "passive_scanner": "Enter target:",
        }
        ptype = plugin_meta.plugin_type if plugin_meta else "search"
        prompt = prompt_map.get(ptype, "Enter input:")
        self.query_input.setPlaceholderText(prompt)
        form.addRow(prompt, self.query_input)
        layout.addLayout(form)

        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_query(self):
        return self.query_input.text().strip()
