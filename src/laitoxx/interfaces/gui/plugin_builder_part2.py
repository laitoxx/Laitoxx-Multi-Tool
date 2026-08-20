# ruff: noqa: F405
from .plugin_builder_context import *  # noqa: F403


class PluginBuilderMixin2:
    def _save_plugin(self):
        source = self.editor.toPlainText()

        # Run syntax check first
        issues = check_lua_syntax(source)
        errors = [i for i in issues if i["severity"] == "error"]
        if errors:
            self._check_syntax()
            reply = QMessageBox.question(
                self,
                "Syntax Errors",
                f"Found {len(errors)} error(s). Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Determine save path
        lua_dir = "lua_plugins"
        os.makedirs(lua_dir, exist_ok=True)

        if self.plugin_path and os.path.exists(self.plugin_path):
            save_path = self.plugin_path
        else:
            save_path = os.path.join(lua_dir, self._current_filename)

        filepath, _ = QFileDialog.getSaveFileName(self, "Save Lua Plugin", save_path, "Lua Files (*.lua)")
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(source)
            self.plugin_path = filepath
            self._current_filename = os.path.basename(filepath)
            self.setWindowTitle(f"Plugin Builder - {self._current_filename}")
            self.issues_area.setHtml(f'<span style="color: #98c379;">&#10004; Saved to {filepath}</span>')
            self.accept()
        except Exception as e:
            self.issues_area.setHtml(f'<span style="color: #e06c75;">&#10006; Error saving: {e}</span>')

    def _show_random_tip(self):
        tip = random.choice(LUA_TIPS)
        self.tip_label.setText(f"Tip: {tip}")
