"""Shared dependencies for plugin-builder composition slices."""
# ruff: noqa: F401

import os
import random
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme

from .plugin_code_editor import LuaCodeEditor
from .plugin_snippet_dialog import SnippetInsertDialog
from .plugin_snippets import CODE_SNIPPETS, LUA_TIPS
from .plugin_syntax_check import check_lua_syntax
from .plugin_syntax_highlighter import LuaSyntaxHighlighter
from .plugin_template import generate_plugin_template

__all__ = [name for name in globals() if not name.startswith("__")]
