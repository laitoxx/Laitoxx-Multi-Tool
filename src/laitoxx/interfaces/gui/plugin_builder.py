"""Composition root and public API for the Lua plugin builder."""
# ruff: noqa: F405

from laitoxx.core.localization.i18n import translator as default_translator

from .plugin_builder_context import *  # noqa: F403
from .plugin_builder_part1 import PluginBuilderMixin1
from .plugin_builder_part2 import PluginBuilderMixin2
from .plugin_code_editor import LineNumberArea as LineNumberArea
from .plugin_code_editor import LuaCodeEditor as LuaCodeEditor
from .plugin_snippet_dialog import SnippetInsertDialog as SnippetInsertDialog
from .plugin_syntax_check import check_lua_syntax as check_lua_syntax
from .plugin_syntax_highlighter import LuaSyntaxHighlighter as LuaSyntaxHighlighter
from .plugin_template import generate_plugin_template as generate_plugin_template


class PluginBuilderWindow(PluginBuilderMixin1, PluginBuilderMixin2, QDialog):
    def __init__(self, parent=None, plugin_path=None, translator=None):
        super().__init__(parent)
        self.translator = translator or default_translator
        self.plugin_path = plugin_path  # path to existing .lua file for editing
        self._theme = resolved_theme(getattr(parent, "theme_data", {}))
        self.setMinimumSize(1000, 700)
        self.setWindowOpacity(0.92)

        self.stacked_widget = QStackedWidget(self)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stacked_widget)

        self._create_meta_page()
        self._create_editor_page()
        self.update_theme(self._theme)
        self.retranslate_ui()

        if self.plugin_path and os.path.exists(self.plugin_path):
            self._load_existing_plugin()
        else:
            self.stacked_widget.setCurrentIndex(0)
