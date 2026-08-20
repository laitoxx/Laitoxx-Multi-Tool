"""Focused behavior slice for TongueWindow."""
# ruff: noqa: F405

from .tongue_window_context import *  # noqa: F403


class TongueWindowMixin4:
    def _export_json(self):
        if not self.report:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, _t("tongue_export_json", "Export JSON"), "tongue-report.json", "JSON (*.json)"
        )
        if path:
            Path(path).write_text(json.dumps(self.report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _open_report(self):
        path = str(((self.report or {}).get("artifacts") or {}).get("html") or "")
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_folder(self):
        artifacts = (self.report or {}).get("artifacts") or {}
        first = next(iter(artifacts.values()), "")
        if first:
            folder = Path(first).parent
        else:
            from laitoxx.features.osint.tongue.service import default_output_dir

            folder = default_output_dir()
            folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def update_theme(self, theme_data):
        self.theme_data = theme_data or {}
        theme = resolved_theme(self.theme_data)
        custom = f"""
QDialog#TongueWindow {{ background: {theme["surface_base_color"]}; }}
QScrollArea#TongueSidebarScroll, QWidget#TongueSidebarViewport {{
    background: transparent; border: none;
}}
QWidget#TongueSidebar {{
    background: {theme["surface_raised_color"]};
    border: 1px solid {theme["border_subtle_color"]};
    border-radius: 12px;
}}
QFrame#ChainStatusCard {{
    background: {theme["surface_raised_color"]};
    border: 1px solid {theme["border_subtle_color"]}; border-radius: 12px;
}}
QFrame#ChainStatusCard[chainState="exported"] {{ border-left: 4px solid {theme["success_color"]}; }}
QFrame#ChainStatusCard[chainState="not_exported"] {{ border-left: 4px solid {theme["warning_color"]}; }}
QFrame#ChainStatusCard[chainState="index_pending"] {{ border-left: 4px solid {theme["accent_color"]}; }}
QFrame#ChainStatusCard[chainState="source_error"] {{ border-left: 4px solid {theme["danger_color"]}; }}
QFrame#ChainStatusCard[chainState="telegram_only"] {{ border-left: 4px solid #2AABEE; }}
QScrollArea {{ background: transparent; border: none; }}
QToolButton[spinControl="true"] {{
    background: {theme["surface_input_color"]}; color: {theme["text_secondary_color"]};
    border: 1px solid {theme["border_strong_color"]}; border-radius: 5px;
    padding: 0; margin: 0;
}}
QToolButton[spinControl="true"]:hover {{
    background: {theme["accent_soft_color"]}; border-color: {theme["accent_color"]};
}}
QToolButton[spinControl="true"]:pressed {{ background: {theme["surface_pressed_color"]}; }}
"""
        self.setStyleSheet(build_workspace_qss(self.theme_data) + custom)
        if hasattr(self, "depth_up"):
            icon_color = theme["text_secondary_color"]
            self.depth_up.setIcon(_chevron_icon(icon_color, True))
            self.depth_down.setIcon(_chevron_icon(icon_color, False))
        if hasattr(self, "graph_editor"):
            self.graph_editor.update_theme(self.theme_data)

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._close_pending = True
            self._cancel()
            self.status.setText(_t("tongue_close_wait", "Stopping the investigation before closing…"))
            event.ignore()
            return
        super().closeEvent(event)
