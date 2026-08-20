from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons


def _lua_config_entry(value) -> dict:
    """Convert one Lua config-schema row to an ordinary Python mapping."""
    if isinstance(value, dict):
        return value
    if hasattr(value, "items"):
        return {str(key): item for key, item in value.items()}
    return {}


class LuaPluginConfigDialog(QDialog):
    """Dialog to edit config values for a Lua plugin based on its config_schema."""

    def __init__(self, parent=None, plugin_meta=None):
        super().__init__(parent)
        self.plugin_meta = plugin_meta
        self.setWindowTitle(
            translator.get(
                "lua_plugin_settings_title",
                name=plugin_meta.name if plugin_meta else "Plugin",
            )
        )
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        layout.addLayout(self.form_layout)

        self._widgets = {}
        schema = []
        if plugin_meta and plugin_meta.config_schema:
            raw = plugin_meta.config_schema
            if hasattr(raw, "values"):
                # Lua table (1-based array)
                try:
                    schema = [_lua_config_entry(raw[i]) for i in range(1, 100) if raw[i] is not None]
                except (KeyError, IndexError, TypeError):
                    try:
                        from laitoxx.app.plugins.engine import _lua_table_to_python

                        schema = _lua_table_to_python(raw)
                        if not isinstance(schema, list):
                            schema = []
                    except Exception:
                        schema = []
            elif isinstance(raw, list):
                schema = raw

        for entry in schema:
            if not isinstance(entry, dict):
                continue
            key = entry.get("key", "")
            label = entry.get("label", key)
            field_type = entry.get("type", "string")
            default = entry.get("default", "")
            current = plugin_meta.config_values.get(key, default) if plugin_meta else default

            if field_type == "boolean":
                widget = QCheckBox()
                widget.setChecked(bool(current))
            elif field_type == "number":
                widget = QLineEdit(str(current))
            else:
                widget = QLineEdit(str(current) if current else "")

            self.form_layout.addRow(label + ":", widget)
            self._widgets[key] = (widget, field_type)

        if not schema:
            layout.addWidget(QLabel(translator.get("lua_no_config_schema")))

        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_config(self) -> dict:
        result = {}
        for key, (widget, field_type) in self._widgets.items():
            if field_type == "boolean":
                result[key] = widget.isChecked()
            elif field_type == "number":
                try:
                    result[key] = float(widget.text())
                except ValueError:
                    result[key] = 0
            else:
                result[key] = widget.text()
        return result
