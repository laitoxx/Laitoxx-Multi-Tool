"""
username_osint_window.py - Modern Username OSINT dialog for LAITOXX.

Layout:
  ┌──────────────────────────────────────────┐
  │  [ @username _______________]  [SEARCH]  │  ← hero input
  │  first ___  last ___   [Nicks] [Graph]   │
  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░  42/382 | Found: 7 │  ← progress
  ├────────┬─────────────────────────────────┤
  │ FILTER │  live results / dashboard       │
  │ cats▼  │  ┌──────────────────────┐       │
  │ status │  │ card  card  card     │       │
  │        │  │ card  card  card     │       │
  │ NICKS  │  └──────────────────────┘       │
  │  list  │            ── OR ──             │
  │        │  PORTRAIT (after search done)   │
  └────────┴─────────────────────────────────┘

Design tokens reused from graph_editor.py for visual consistency.
"""

from __future__ import annotations

import json
import os

from PyQt6.QtCore import (
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.osint.intelligence.identity import AccountProfile, avatar_fingerprint, correlate_many
from laitoxx.features.osint.username_osint.avatar_downloader import AvatarDownloader
from laitoxx.features.osint.username_osint.models import (
    CATEGORY_ICONS,
    SITE_CATEGORIES,
    CheckResult,
)
from laitoxx.features.osint.username_osint.nickname_generator import NicknameGenerator
from laitoxx.features.osint.username_osint.portrait_generator import DigitalPortrait
from laitoxx.features.osint.username_osint.site_db import SiteDB
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.username_osint_worker import CheckWorker as _CheckWorker
from laitoxx.interfaces.gui.worker import stop_and_detach_thread

_ACCENT = "#c084fc"

_ACCENT2 = "#f472b6"

_ACCENT_DIM = "#7c3aed"

_BG_DEEP = "#0d0d1a"

_BG_PANEL = "rgba(15, 12, 30, {a})"

_BG_ITEM = "rgba(255, 255, 255, 0.03)"

_BG_ITEM_HOV = "rgba(255, 255, 255, 0.06)"

_BORDER = "rgba(192, 132, 252, 0.2)"

_BORDER_FOCUS = "rgba(192, 132, 252, 0.6)"

_TEXT_PRI = "#f1f0ff"

_TEXT_SEC = "#a99fc0"

_TEXT_DIM = "#6b6580"

_GREEN = "#00b894"

_RED = "#e74c3c"

_ORANGE = "#f39c12"

_BLUE = "#74b9ff"

_STATUS_COLORS = {
    "found": _GREEN,
    "confirmed": _GREEN,
    "probable": _BLUE,
    "not_found": "#555",
    "error": _ORANGE,
    "timeout": _ORANGE,
    "rate_limited": _ORANGE,
    "waf_blocked": "#e17055",
    "login_required": _BLUE,
    "network_error": _ORANGE,
    "unsupported": _TEXT_DIM,
}


def _t(key: str, fallback: str = "") -> str:
    return translator.get(key) or fallback or key


def _panel_bg(alpha: float = 0.55) -> str:
    return _BG_PANEL.format(a=alpha)


__all__ = [
    "AccountProfile",
    "AvatarDownloader",
    "CATEGORY_ICONS",
    "CheckResult",
    "DigitalPortrait",
    "NicknameGenerator",
    "QButtonGroup",
    "QCheckBox",
    "QComboBox",
    "QDesktopServices",
    "QDialog",
    "QFileDialog",
    "QFont",
    "QFrame",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QMessageBox",
    "QProgressBar",
    "QPushButton",
    "QRadioButton",
    "QScrollArea",
    "QSplitter",
    "QTextEdit",
    "QThread",
    "QTimer",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "SITE_CATEGORIES",
    "SiteDB",
    "_ACCENT",
    "_ACCENT2",
    "_ACCENT_DIM",
    "_BG_DEEP",
    "_BG_ITEM",
    "_BG_ITEM_HOV",
    "_BG_PANEL",
    "_BLUE",
    "_BORDER",
    "_BORDER_FOCUS",
    "_CheckWorker",
    "_GREEN",
    "_ORANGE",
    "_RED",
    "_STATUS_COLORS",
    "_TEXT_DIM",
    "_TEXT_PRI",
    "_TEXT_SEC",
    "_panel_bg",
    "_t",
    "avatar_fingerprint",
    "build_workspace_qss",
    "correlate_many",
    "json",
    "os",
    "pyqtSignal",
    "resolved_theme",
    "stop_and_detach_thread",
    "translator",
]
