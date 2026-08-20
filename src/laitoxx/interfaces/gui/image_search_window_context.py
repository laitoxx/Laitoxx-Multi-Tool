"""Shared imports and dependencies for the image search workspace slices."""

from __future__ import annotations

import hashlib
import json
import os
import random
from typing import Any

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.theme import DEFAULT_THEME, load_default_theme
from laitoxx.features.osint.intelligence.identity import avatar_fingerprint, compare_avatars
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.worker import stop_and_detach_thread

from ._image_workers import (
    HAS_PIL,
    HAS_REQUESTS,
    ForensicsWorker,
    HashWorker,
    SearchWorker,
    pil_to_qpixmap,
)
from ._style_provider import (
    ACCENT,
    ACCENT2,
    ACCENT_DIM,
    BG_CARD,
    BG_DEEP,
    BG_PANEL,
    BORDER,
    GREEN,
    ORANGE,
    RED,
    TEXT_DIM,
    TEXT_PRI,
    TEXT_SEC,
    build_base_style,
    engine_pill_style,
    hline_style,
    make_button,
    section_label_style,
    tool_btn_style,
)
from .image_models import (
    _DEFAULT_ENGINES_ON,
    _ENGINE_GROUP_FALLBACKS,
    _ENGINE_GROUPS,
    _FORENSICS_CHECK_FALLBACKS,
    _FORENSICS_CHECKS,
    _HASH_ORDER,
    _SLIDER_DEFS,
)
from .image_widgets import ScalableImageLabel as _ScalableImageLabel

try:
    from PIL import Image as Image
    from PIL import ImageEnhance as ImageEnhance
    from PIL import ImageFilter as ImageFilter
except ImportError:
    pass


def _t(key: str, fallback: str = "", **kwargs) -> str:
    raw = translator.get(key)
    if not raw or raw == key:
        raw = fallback or key
    if kwargs:
        try:
            return raw.format(**kwargs)
        except (KeyError, IndexError):
            return raw
    return raw


def _section_label(text: str, text_dim: str = TEXT_DIM) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(section_label_style(text_dim))
    return lbl


def _hline(border: str = BORDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(hline_style(border))
    return f


__all__ = [
    "ACCENT",
    "ACCENT2",
    "ACCENT_DIM",
    "Any",
    "BG_CARD",
    "BG_DEEP",
    "BG_PANEL",
    "BORDER",
    "DEFAULT_THEME",
    "ForensicsWorker",
    "GREEN",
    "HAS_PIL",
    "HAS_REQUESTS",
    "HashWorker",
    "ORANGE",
    "QApplication",
    "QCheckBox",
    "QDesktopServices",
    "QDialog",
    "QFileDialog",
    "QFrame",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QMessageBox",
    "QProgressBar",
    "QPushButton",
    "QScrollArea",
    "QSizePolicy",
    "QSlider",
    "QSplitter",
    "QTextEdit",
    "QThread",
    "QTimer",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "RED",
    "SearchWorker",
    "TEXT_DIM",
    "TEXT_PRI",
    "TEXT_SEC",
    "_DEFAULT_ENGINES_ON",
    "_ENGINE_GROUPS",
    "_ENGINE_GROUP_FALLBACKS",
    "_FORENSICS_CHECKS",
    "_FORENSICS_CHECK_FALLBACKS",
    "_HASH_ORDER",
    "_SLIDER_DEFS",
    "_ScalableImageLabel",
    "_hline",
    "_section_label",
    "_t",
    "avatar_fingerprint",
    "build_base_style",
    "build_workspace_qss",
    "compare_avatars",
    "engine_pill_style",
    "hashlib",
    "hline_style",
    "json",
    "load_default_theme",
    "make_button",
    "os",
    "pil_to_qpixmap",
    "random",
    "resolved_theme",
    "section_label_style",
    "stop_and_detach_thread",
    "tool_btn_style",
    "translator",
]
__all__ += ["Image", "ImageEnhance", "ImageFilter"]
