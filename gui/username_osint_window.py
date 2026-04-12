"""
username_osint_window.py — Modern Username OSINT dialog for LAITOXX.

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

import os
import json
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QProgressBar, QSplitter, QScrollArea,
    QCheckBox, QFrame, QRadioButton, QButtonGroup,
    QSizePolicy, QMessageBox, QFileDialog, QGridLayout,
)
from PyQt6.QtGui import QFont, QPixmap, QDesktopServices, QColor, QPainter, QPen, QBrush
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, pyqtSlot, QObject, QUrl, QTimer, QRectF,
)

from gui.translator import translator

from script.tools.username_osint.models import (
    CheckResult, SITE_CATEGORIES, CATEGORY_ICONS,
)
from script.tools.username_osint.site_db import SiteDB
from script.tools.username_osint.checker import UsernameChecker
from script.tools.username_osint.nickname_generator import NicknameGenerator
from script.tools.username_osint.portrait_generator import DigitalPortrait
from script.tools.username_osint.avatar_downloader import AvatarDownloader


# ═══════════════════════════════════════════════════════════════════════
# Design tokens (shared language with graph_editor)
# ═══════════════════════════════════════════════════════════════════════

_ACCENT       = "#c084fc"
_ACCENT2      = "#f472b6"
_ACCENT_DIM   = "#7c3aed"

_BG_DEEP      = "#0d0d1a"
_BG_PANEL     = "rgba(15, 12, 30, {a})"
_BG_ITEM      = "rgba(255, 255, 255, 0.03)"
_BG_ITEM_HOV  = "rgba(255, 255, 255, 0.06)"

_BORDER       = "rgba(192, 132, 252, 0.2)"
_BORDER_FOCUS = "rgba(192, 132, 252, 0.6)"

_TEXT_PRI     = "#f1f0ff"
_TEXT_SEC     = "#a99fc0"
_TEXT_DIM     = "#6b6580"

_GREEN  = "#00b894"
_RED    = "#e74c3c"
_ORANGE = "#f39c12"
_BLUE   = "#74b9ff"

_STATUS_COLORS = {
    "found": _GREEN, "not_found": "#555", "error": _ORANGE,
    "timeout": _ORANGE, "rate_limited": _ORANGE, "waf_blocked": "#e17055",
}


def _t(key: str, fallback: str = "") -> str:
    return translator.get(key) or fallback or key


def _panel_bg(alpha: float = 0.55) -> str:
    return _BG_PANEL.format(a=alpha)


# ═══════════════════════════════════════════════════════════════════════
# Reusable styled widgets
# ═══════════════════════════════════════════════════════════════════════

class _GlassPanel(QFrame):
    """Semi-transparent panel matching graph editor."""
    def __init__(self, alpha: float = 0.55, radius: int = 12, parent=None):
        super().__init__(parent)
        self._alpha = alpha
        self._radius = radius
        self._border_color = _BORDER
        self._bg_base = "15, 10, 30"
        self._refresh()

    def set_theme(self, border_color: str, bg_color: str = ""):
        """Update border and optional background tint from theme data."""
        self._border_color = border_color
        if bg_color:
            import re as _re
            m = _re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", bg_color)
            if m:
                self._bg_base = f"{m[1]}, {m[2]}, {m[3]}"
        self._refresh()

    def _refresh(self):
        bg = f"rgba({self._bg_base}, {self._alpha:.2f})"
        self.setStyleSheet(f"""
            _GlassPanel {{
                background: {bg};
                border: 1px solid {self._border_color};
                border-radius: {self._radius}px;
            }}
        """)


class _AccentButton(QPushButton):
    """Primary action button with gradient."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(124,58,237,0.7), stop:1 rgba(192,132,252,0.7));
                border: 1px solid {_ACCENT_DIM};
                border-radius: 8px;
                color: white;
                font-size: 13px;
                font-weight: 700;
                padding: 0 20px;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(192,132,252,0.8), stop:1 rgba(244,114,182,0.7));
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{
                background: rgba(124,58,237,0.9);
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: rgba(60,50,80,0.3);
                border-color: rgba(255,255,255,0.06);
                color: {_TEXT_DIM};
            }}
        """)


class _GhostButton(QPushButton):
    """Secondary action — transparent with border."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(192,132,252,0.06);
                border: 1px solid {_BORDER};
                border-radius: 7px;
                color: {_TEXT_SEC};
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: rgba(192,132,252,0.15);
                color: {_TEXT_PRI};
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{ background: rgba(192,132,252,0.25); }}
            QPushButton:disabled {{
                background: rgba(50,50,50,0.15);
                color: {_TEXT_DIM};
                border-color: rgba(255,255,255,0.05);
            }}
        """)


class _SectionLabel(QLabel):
    """Small uppercase section header."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(22)
        self.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.setStyleSheet(f"""
            QLabel {{
                color: {_ACCENT};
                background: rgba(192,132,252,0.06);
                border-bottom: 1px solid {_BORDER};
                padding: 2px 8px;
                letter-spacing: 1.2px;
            }}
        """)


class _StatCard(QFrame):
    """Small stat card: icon + value + label."""
    def __init__(self, icon: str, value: str, label: str, color: str = _ACCENT, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            _StatCard {{
                background: {_BG_ITEM};
                border: 1px solid {_BORDER};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(4)
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 14px; color: {color}; background: transparent;")
        top.addWidget(icon_lbl)
        self._value = QLabel(value)
        self._value.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {color}; background: transparent;"
        )
        top.addWidget(self._value)
        top.addStretch()
        layout.addLayout(top)

        self._label = QLabel(label)
        self._label.setStyleSheet(f"font-size: 10px; color: {_TEXT_DIM}; background: transparent;")
        layout.addWidget(self._label)

    def set_value(self, v: str):
        self._value.setText(v)


# ═══════════════════════════════════════════════════════════════════════
# Worker thread
# ═══════════════════════════════════════════════════════════════════════

class _CheckWorker(QObject):
    progress = pyqtSignal(int, int, object)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, sites, username, max_workers=50):
        super().__init__()
        self.sites = sites
        self.username = username
        self.max_workers = max_workers
        self._cancelled = False
        self._checker: Optional[UsernameChecker] = None

    def cancel(self):
        self._cancelled = True
        if self._checker:
            self._checker.cancel()

    @pyqtSlot()
    def run(self):
        try:
            self._checker = UsernameChecker(
                self.sites, max_workers=self.max_workers,
                progress_callback=self._on_progress,
            )
            results = self._checker.check_username(self.username)
            if not self._cancelled:
                self.finished.emit(results)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def _on_progress(self, checked, total, result):
        if not self._cancelled:
            self.progress.emit(checked, total, result)


# ═══════════════════════════════════════════════════════════════════════
# Result card — compact row
# ═══════════════════════════════════════════════════════════════════════

class _ResultRow(QFrame):
    def __init__(self, result: CheckResult, parent=None):
        super().__init__(parent)
        self.result = result
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor if result.is_found else Qt.CursorShape.ArrowCursor)
        color = _STATUS_COLORS.get(result.status, _ORANGE)

        self.setStyleSheet(f"""
            _ResultRow {{
                background: {_BG_ITEM};
                border-left: 3px solid {color};
                border-radius: 4px;
                margin: 1px 0;
            }}
            _ResultRow:hover {{
                background: {_BG_ITEM_HOV};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # Status indicator
        dot = QLabel("\u25cf")
        dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
        dot.setFixedWidth(12)
        layout.addWidget(dot)

        # Site name (bold)
        name = QLabel(result.site_name)
        name.setStyleSheet(f"color: {_TEXT_PRI}; font-size: 12px; font-weight: 600; background: transparent;")
        name.setFixedWidth(130)
        layout.addWidget(name)

        # Category icon
        cat_icon = CATEGORY_ICONS.get(result.category, "")
        cat = QLabel(cat_icon)
        cat.setFixedWidth(18)
        cat.setToolTip(result.category.capitalize())
        cat.setStyleSheet("background: transparent;")
        layout.addWidget(cat)

        # URL or status
        if result.is_found:
            url_btn = QPushButton(result.url[:50])
            url_btn.setFlat(True)
            url_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            url_btn.setStyleSheet(
                f"color: {_BLUE}; font-size: 11px; background: transparent;"
                f" border: none; text-align: left; padding: 0; text-decoration: none;"
            )
            url_btn.clicked.connect(lambda _, u=result.url: QDesktopServices.openUrl(QUrl(u)))
            layout.addWidget(url_btn, 1)
        else:
            msg = result.status.replace("_", " ")
            if result.error_message:
                msg += f" · {result.error_message[:30]}"
            s_lbl = QLabel(msg)
            s_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; background: transparent;")
            layout.addWidget(s_lbl, 1)

        # Confidence
        if result.is_found and result.confidence > 0:
            pct = result.confidence_pct
            c = _GREEN if pct >= 70 else (_ORANGE if pct >= 40 else _RED)
            cl = QLabel(f"{pct}%")
            cl.setStyleSheet(
                f"color: {c}; font-size: 10px; font-weight: 700;"
                f" background: rgba(0,0,0,0.15); border-radius: 3px; padding: 0 3px;"
            )
            cl.setFixedWidth(30)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(cl)

        # WAF
        if result.waf_detected:
            w = QLabel("\U0001f6e1")
            w.setFixedWidth(14)
            w.setToolTip("WAF")
            w.setStyleSheet("background: transparent; font-size: 10px;")
            layout.addWidget(w)

        # Time
        t = QLabel(f"{result.response_time_ms:.0f}ms")
        t.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 9px; background: transparent;")
        t.setFixedWidth(38)
        t.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(t)


# ═══════════════════════════════════════════════════════════════════════
# Main dialog
# ═══════════════════════════════════════════════════════════════════════

class UsernameOsintWindow(QDialog):
    graph_requested = pyqtSignal(str, list)

    def __init__(self, parent=None, theme_data=None, lua_plugins=None):
        super().__init__(parent)
        self.theme_data = theme_data or {}
        self._theme = self.theme_data
        self.lua_plugins = lua_plugins or []
        self._results: list[CheckResult] = []
        self._nickname_variants: list[str] = []
        self._thread: Optional[QThread] = None
        self._worker: Optional[_CheckWorker] = None
        self._avatar_downloader = AvatarDownloader()
        self._db = SiteDB()
        self._db.load()
        self._is_searching = False

        self.setWindowTitle(_t("uo_title", "Username OSINT"))
        self.setMinimumSize(820, 520)
        self.resize(1060, 660)

        self._build_ui()
        self._apply_global_style()
        self._restyle_widgets(self._theme)

    # ══════════════════════════════════════════════════════════════
    # BUILD UI
    # ══════════════════════════════════════════════════════════════

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(8)

        # ── Hero input row ──
        hero = QHBoxLayout()
        hero.setSpacing(8)

        self._at_label = QLabel("@")
        self._at_label.setStyleSheet(
            f"color: {_ACCENT}; font-size: 22px; font-weight: 700; background: transparent;"
        )
        self._at_label.setFixedWidth(20)
        hero.addWidget(self._at_label)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText(_t("uo_enter_username", "Enter username..."))
        self._username_input.setMinimumHeight(40)
        self._username_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {_BORDER};
                border-radius: 10px;
                color: {_TEXT_PRI};
                padding: 6px 14px;
                font-size: 16px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border-color: {_ACCENT};
                background: rgba(255,255,255,0.06);
            }}
        """)
        self._username_input.returnPressed.connect(self._on_search_clicked)
        hero.addWidget(self._username_input, 1)

        self._btn_search = _AccentButton(_t("uo_search", "SEARCH"))
        self._btn_search.setMinimumWidth(110)
        self._btn_search.setMinimumHeight(40)
        self._btn_search.clicked.connect(self._on_search_clicked)
        hero.addWidget(self._btn_search)

        root.addLayout(hero)

        # ── Secondary controls row ──
        sec = QHBoxLayout()
        sec.setSpacing(6)

        self._first_name = QLineEdit()
        self._first_name.setPlaceholderText(_t("uo_first_name", "First name"))
        self._first_name.setMaximumWidth(130)
        self._first_name.setFixedHeight(28)
        sec.addWidget(self._first_name)

        self._last_name = QLineEdit()
        self._last_name.setPlaceholderText(_t("uo_last_name", "Last name"))
        self._last_name.setMaximumWidth(130)
        self._last_name.setFixedHeight(28)
        sec.addWidget(self._last_name)

        sec.addStretch()

        self._btn_nicks = _GhostButton(_t("uo_generate_nicks", "Variants"))
        self._btn_nicks.clicked.connect(self._generate_nicknames)
        sec.addWidget(self._btn_nicks)

        self._btn_graph = _GhostButton(_t("uo_send_to_graph", "To Graph"))
        self._btn_graph.clicked.connect(self._send_to_graph)
        self._btn_graph.setEnabled(False)
        sec.addWidget(self._btn_graph)

        self._btn_export = _GhostButton(_t("uo_export_results", "Export"))
        self._btn_export.clicked.connect(self._export_results)
        self._btn_export.setEnabled(False)
        sec.addWidget(self._btn_export)

        root.addLayout(sec)

        # ── Progress bar ──
        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        self._progress.setFormat(_t("uo_ready", "Ready to search"))
        self._progress.setValue(0)
        self._progress.setFixedHeight(18)
        root.addWidget(self._progress)

        # ── Dashboard stats row ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_found = _StatCard("\u2714", "0", _t("uo_found", "Found"), _GREEN)
        self._stat_total = _StatCard("\u2630", "0", _t("uo_total", "Checked"), _ACCENT)
        self._stat_errors = _StatCard("\u26A0", "0", _t("uo_errors", "Errors"), _ORANGE)
        self._stat_conf = _StatCard("\u272A", "—", _t("uo_confidence", "Confidence"), _BLUE)
        for card in (self._stat_found, self._stat_total, self._stat_errors, self._stat_conf):
            stats_row.addWidget(card)
        root.addLayout(stats_row)

        # ── Main content area (splitter) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # ── Left sidebar ──
        left = _GlassPanel(alpha=0.35, radius=10)
        self._left_panel = left
        left.setMaximumWidth(210)
        left.setMinimumWidth(160)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(4)

        # Categories section
        left_layout.addWidget(_SectionLabel(_t("uo_categories", "CATEGORIES").upper()))

        # Select/deselect row
        sel_row = QHBoxLayout()
        sel_row.setSpacing(4)
        btn_all = QPushButton(_t("uo_select_all", "All"))
        btn_all.setFixedHeight(20)
        btn_all.setStyleSheet(self._mini_btn_css())
        btn_all.clicked.connect(lambda: self._set_all_categories(True))
        sel_row.addWidget(btn_all)
        btn_none = QPushButton(_t("uo_deselect_all", "None"))
        btn_none.setFixedHeight(20)
        btn_none.setStyleSheet(self._mini_btn_css())
        btn_none.clicked.connect(lambda: self._set_all_categories(False))
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        left_layout.addLayout(sel_row)

        # Category checks (scrollable)
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        cat_inner = QWidget()
        cat_inner.setStyleSheet("background: transparent;")
        cat_inner_layout = QVBoxLayout(cat_inner)
        cat_inner_layout.setContentsMargins(0, 0, 0, 0)
        cat_inner_layout.setSpacing(0)

        self._category_checks: dict[str, QCheckBox] = {}
        for cat in SITE_CATEGORIES:
            icon = CATEGORY_ICONS.get(cat, "")
            count = sum(1 for s in self._db.sites if s.category == cat)
            cb = QCheckBox(f"{icon} {cat.capitalize()} · {count}")
            cb.setChecked(True)
            cb.stateChanged.connect(self._filter_results)
            self._category_checks[cat] = cb
            cat_inner_layout.addWidget(cb)
        cat_inner_layout.addStretch()
        cat_scroll.setWidget(cat_inner)
        left_layout.addWidget(cat_scroll, 1)

        # Status filter
        left_layout.addWidget(_SectionLabel(_t("uo_status_filter", "STATUS").upper()))
        self._status_group = QButtonGroup(self)
        for i, (label, value) in enumerate([
            (_t("uo_all", "All"), "all"),
            (_t("uo_found_only", "Found"), "found"),
            (_t("uo_not_found", "Not found"), "not_found"),
            (_t("uo_errors", "Errors"), "error"),
        ]):
            rb = QRadioButton(label)
            rb.setProperty("filter_value", value)
            if i == 0:
                rb.setChecked(True)
            self._status_group.addButton(rb)
            left_layout.addWidget(rb)
        self._status_group.buttonClicked.connect(self._filter_results)

        # Nickname variants
        left_layout.addWidget(_SectionLabel(_t("uo_nickname_variants", "VARIANTS").upper()))
        self._nick_list = QTextEdit()
        self._nick_list.setReadOnly(True)
        self._nick_list.setMaximumHeight(120)
        self._nick_list.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(0,0,0,0.15);
                border: 1px solid rgba(192,132,252,0.1);
                border-radius: 6px;
                color: {_TEXT_SEC};
                font-size: 10px;
                font-family: 'Consolas', monospace;
            }}
        """)
        left_layout.addWidget(self._nick_list)

        # Phonetic
        self._phonetic_text = QLabel("")
        self._phonetic_text.setWordWrap(True)
        self._phonetic_text.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 9px; background: transparent;")
        left_layout.addWidget(self._phonetic_text)

        splitter.addWidget(left)

        # ── Center: results stream ──
        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(4, 0, 0, 0)
        center_layout.setSpacing(0)

        # Results scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._results_container = QWidget()
        self._results_container.setStyleSheet("background: transparent;")
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(1)
        self._results_layout.addStretch()
        self._scroll.setWidget(self._results_container)
        center_layout.addWidget(self._scroll, 1)

        # Portrait text (shown after search)
        self._portrait_text = QTextEdit()
        self._portrait_text.setReadOnly(True)
        self._portrait_text.setMaximumHeight(160)
        self._portrait_text.setVisible(False)
        self._portrait_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(0,0,0,0.2);
                border: 1px solid {_BORDER};
                border-radius: 8px;
                color: {_TEXT_SEC};
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }}
        """)
        center_layout.addWidget(self._portrait_text)

        splitter.addWidget(center)
        splitter.setSizes([200, 800])
        root.addWidget(splitter, 1)

    # ══════════════════════════════════════════════════════════════
    # GLOBAL STYLE
    # ══════════════════════════════════════════════════════════════

    def update_theme(self, theme_data: dict):
        """Called from MainWindow when user changes the theme."""
        self._theme = theme_data
        self._apply_global_style()
        self._restyle_widgets(theme_data)

    def _restyle_widgets(self, td: dict):
        """Re-apply inline styles on every widget that has a hardcoded stylesheet."""
        accent   = td.get("accent_color",        _ACCENT)
        dim      = td.get("accent_dim_color",     _ACCENT_DIM)
        bdr      = td.get("border_color",         td.get("button_border_color", _BORDER))
        txt_pri  = td.get("text_area_text_color", _TEXT_PRI)
        txt_sec  = td.get("text_secondary_color", _TEXT_SEC)
        btn_bg   = td.get("button_bg_color",      "rgba(124,58,237,0.5)")
        btn_hov  = td.get("button_hover_bg_color","rgba(139,92,246,0.7)")
        bg_win   = td.get("window_bg_color",      td.get("text_area_bg_color", _BG_DEEP))
        panel_bg = td.get("panel_bg_color",       bg_win)

        # Glass panel (left sidebar)
        if hasattr(self, "_left_panel"):
            self._left_panel.set_theme(bdr, panel_bg)

        # Hero @ label
        if hasattr(self, "_at_label"):
            self._at_label.setStyleSheet(
                f"color: {accent}; font-size: 22px; font-weight: 700; background: transparent;"
            )

        # Username input (big hero field)
        if hasattr(self, "_username_input"):
            self._username_input.setStyleSheet(f"""
                QLineEdit {{
                    background: rgba(255,255,255,0.04);
                    border: 1px solid {bdr};
                    border-radius: 10px;
                    color: {txt_pri};
                    padding: 6px 14px;
                    font-size: 16px;
                    font-weight: 500;
                }}
                QLineEdit:focus {{
                    border-color: {accent};
                    background: rgba(255,255,255,0.06);
                }}
            """)

        # Search button (_AccentButton)
        if hasattr(self, "_btn_search"):
            self._btn_search.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {dim}, stop:1 {accent});
                    border: 1px solid {dim};
                    border-radius: 8px;
                    color: white;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0 20px;
                    letter-spacing: 0.5px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {accent}, stop:1 {btn_hov});
                    border-color: {accent};
                }}
                QPushButton:pressed {{ background: {dim}; padding-top: 2px; }}
                QPushButton:disabled {{
                    background: rgba(60,50,80,0.3);
                    border-color: rgba(255,255,255,0.06);
                    color: {_TEXT_DIM};
                }}
            """)

        # Ghost buttons (Variants / Graph / Export)
        ghost_ss = f"""
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {bdr};
                border-radius: 7px;
                color: {txt_sec};
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {btn_hov};
                color: {txt_pri};
                border-color: {accent};
            }}
            QPushButton:pressed {{ background: {btn_hov}; }}
            QPushButton:disabled {{
                background: rgba(50,50,50,0.15);
                color: {_TEXT_DIM};
                border-color: rgba(255,255,255,0.05);
            }}
        """
        for btn_name in ("_btn_nicks", "_btn_graph", "_btn_export"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setStyleSheet(ghost_ss)

        # Portrait / phonetic text
        if hasattr(self, "_portrait_text"):
            self._portrait_text.setStyleSheet(f"""
                QTextEdit {{
                    background: rgba(0,0,0,0.2);
                    border: 1px solid {bdr};
                    border-radius: 8px;
                    color: {txt_sec};
                    font-size: 11px;
                    font-family: 'Consolas', monospace;
                }}
            """)
        if hasattr(self, "_phonetic_text"):
            self._phonetic_text.setStyleSheet(
                f"color: {txt_sec}; font-size: 9px; background: transparent;"
            )

        # Nick list widget (QTextEdit)
        if hasattr(self, "_nick_list"):
            self._nick_list.setStyleSheet(f"""
                QTextEdit {{
                    background: rgba(255,255,255,0.03);
                    border: 1px solid {bdr};
                    border-radius: 6px;
                    color: {txt_pri};
                    font-size: 10px;
                    font-family: 'Consolas', monospace;
                }}
            """)

        # Re-style mini buttons (All/None in categories row)
        mini_css = self._mini_btn_css()
        if hasattr(self, "_left_panel"):
            from PyQt6.QtWidgets import QPushButton as _QPushButton
            for btn in self._left_panel.findChildren(_QPushButton):
                btn.setStyleSheet(mini_css)

        from PyQt6.QtWidgets import QLabel as _QLabel
        import re as _re
        _bg_re = _re.compile(r"background\s*:\s*rgba\(\s*192\s*,\s*132\s*,\s*252\s*,\s*[\d.]+\s*\)")

        # Re-colour all QLabel children that have hardcoded purple token colours.
        _ACCENT_VALS = {"#c084fc", "#f472b6", "#7c3aed"}
        _SEC_VALS    = {"#a99fc0"}
        _DIM_VALS    = {"#6b6580"}
        _PRI_VALS    = {"#f1f0ff"}
        _simple_color_re = _re.compile(r"color\s*:\s*([^;\"'\n]+)")
        for lbl in self.findChildren(_QLabel):
            ss = lbl.styleSheet()
            if not ss:
                continue
            changed = False
            # Fix purple rgba backgrounds in section labels
            if "rgba(192,132,252" in ss or "rgba(192, 132, 252" in ss:
                ss = _bg_re.sub(f"background: {btn_bg}", ss)
                changed = True
            if "color" in ss:
                m = _simple_color_re.search(ss)
                if m:
                    cur = m.group(1).strip().lower()
                    if cur in {v.lower() for v in _ACCENT_VALS}:
                        ss = _simple_color_re.sub(f"color: {accent}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _SEC_VALS}:
                        ss = _simple_color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _DIM_VALS}:
                        ss = _simple_color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _PRI_VALS}:
                        ss = _simple_color_re.sub(f"color: {txt_pri}", ss)
                        changed = True
            if changed:
                lbl.setStyleSheet(ss)

    def _apply_global_style(self):
        td = self._theme if hasattr(self, '_theme') and self._theme else {}
        bg_color   = td.get("window_bg_color",       td.get("text_area_bg_color",   _BG_DEEP))
        text_color = td.get("text_area_text_color",  _TEXT_PRI)
        btn_bg     = td.get("button_bg_color",       "rgba(124,58,237,0.5)")
        btn_hover  = td.get("button_hover_bg_color", "rgba(139,92,246,0.7)")
        btn_border = td.get("border_color",          td.get("button_border_color",  _BORDER))
        btn_text   = td.get("button_text_color",     "white")
        accent     = td.get("accent_color",          _ACCENT)
        txt_sec    = td.get("text_secondary_color",  _TEXT_SEC)
        sb_hand    = td.get("scrollbar_handle_color", btn_border)
        sb_hov     = td.get("scrollbar_handle_hover_color", btn_hover)

        # Update module-level tokens so newly created widgets pick them up
        import gui.username_osint_window as _self_mod
        _self_mod._ACCENT      = accent
        _self_mod._ACCENT_DIM  = td.get("accent_dim_color", _ACCENT_DIM)
        _self_mod._BORDER      = btn_border
        _self_mod._BORDER_FOCUS = accent
        _self_mod._TEXT_PRI    = text_color
        _self_mod._TEXT_SEC    = txt_sec
        _self_mod._TEXT_DIM    = txt_sec  # dim ≈ sec for better readability

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg_color};
            }}
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 7px;
                color: {btn_text};
                padding: 4px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {btn_hover};
            }}
            QLineEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {btn_border};
                border-radius: 6px;
                color: {text_color};
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QCheckBox {{
                color: {txt_sec};
                font-size: 11px;
                spacing: 4px;
                background: transparent;
                padding: 2px 0;
            }}
            QCheckBox::indicator {{
                width: 12px; height: 12px;
                border: 1px solid {btn_border};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border-color: {accent};
            }}
            QRadioButton {{
                color: {txt_sec};
                font-size: 11px;
                background: transparent;
                padding: 1px 0;
            }}
            QRadioButton::indicator {{
                width: 11px; height: 11px;
            }}
            QProgressBar {{
                background: rgba(255,255,255,0.03);
                border: 1px solid {btn_border};
                border-radius: 4px;
                color: {txt_sec};
                font-size: 10px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {btn_bg}, stop:1 {btn_hover});
                border-radius: 3px;
            }}
            QScrollBar:vertical {{
                border: none; background: transparent; width: 5px;
                margin: 0; border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {btn_border};
                min-height: 20px; border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {btn_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            QLabel {{
                background: transparent;
                color: {text_color};
            }}
        """)

    def _mini_btn_css(self) -> str:
        td = getattr(self, "_theme", {})
        btn_bg  = td.get("button_bg_color",       "rgba(192,132,252,0.08)")
        btn_hov = td.get("button_hover_bg_color",  "rgba(192,132,252,0.2)")
        bdr     = td.get("border_color", td.get("button_border_color", _BORDER))
        txt_dim = td.get("text_secondary_color",   _TEXT_DIM)
        txt_pri = td.get("text_area_text_color",   _TEXT_PRI)
        return f"""
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {bdr};
                border-radius: 4px;
                color: {txt_dim};
                font-size: 9px;
                padding: 0 6px;
            }}
            QPushButton:hover {{
                background: {btn_hov};
                color: {txt_pri};
            }}
        """

    # ══════════════════════════════════════════════════════════════
    # SEARCH LOGIC
    # ══════════════════════════════════════════════════════════════

    def _on_search_clicked(self):
        if self._is_searching:
            self._stop_search()
            self._finish_ui()
        else:
            self._start_search()

    def _start_search(self):
        username = self._username_input.text().strip()
        if not username:
            return

        self._stop_search()
        self._results.clear()
        self._clear_results_ui()
        self._btn_graph.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._portrait_text.setVisible(False)
        self._is_searching = True
        self._btn_search.setText(_t("uo_stop", "STOP"))

        selected_cats = [c for c, cb in self._category_checks.items() if cb.isChecked()]
        sites = self._db.filter_by_category(selected_cats) if selected_cats else self._db.sites

        self._progress.setMaximum(len(sites))
        self._progress.setValue(0)
        self._progress.setFormat(f"0 / {len(sites)}")

        self._thread = QThread()
        self._worker = _CheckWorker(sites, username)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _stop_search(self):
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(5000):
                self._thread.terminate()
                self._thread.wait(2000)

    def _cleanup_thread(self):
        self._worker = None
        self._thread = None

    def _finish_ui(self):
        self._is_searching = False
        self._btn_search.setText(_t("uo_search", "SEARCH"))
        self._btn_graph.setEnabled(bool(self._results))
        self._btn_export.setEnabled(bool(self._results))
        self._update_stats()

    def _on_progress(self, checked, total, result: CheckResult):
        self._results.append(result)
        self._progress.setValue(checked)
        found_count = sum(1 for r in self._results if r.is_found)
        self._progress.setFormat(f"{checked}/{total}  ·  {_t('uo_found','Found')}: {found_count}")

        if self._should_show(result):
            self._add_result_card(result)
        self._update_stats()

    def _on_finished(self, results: list[CheckResult]):
        self._results = results
        self._finish_ui()

        found = [r for r in results if r.is_found]
        self._progress.setFormat(
            f"{_t('uo_done','Done')}  ·  {_t('uo_found','Found')}: {len(found)}/{len(results)}"
        )

        # Portrait
        username = self._username_input.text().strip()
        portrait = DigitalPortrait(username, results)
        self._portrait_text.setPlainText(portrait.to_text())
        self._portrait_text.setVisible(True)

        self._try_load_avatar(results)
        self._generate_nicknames()

    def _on_error(self, msg: str):
        self._finish_ui()
        self._progress.setFormat(f"Error: {msg[:60]}")

    # ══════════════════════════════════════════════════════════════
    # UI HELPERS
    # ══════════════════════════════════════════════════════════════

    def _clear_results_ui(self):
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_result_card(self, result: CheckResult):
        card = _ResultRow(result, self._results_container)
        self._results_layout.insertWidget(self._results_layout.count() - 1, card)

    def _should_show(self, result: CheckResult) -> bool:
        cat_cb = self._category_checks.get(result.category)
        if cat_cb and not cat_cb.isChecked():
            return False
        checked_btn = self._status_group.checkedButton()
        if checked_btn:
            fval = checked_btn.property("filter_value")
            if fval == "found" and result.status != "found":
                return False
            if fval == "not_found" and result.status != "not_found":
                return False
            if fval == "error" and result.status not in ("error", "timeout", "rate_limited", "waf_blocked"):
                return False
        return True

    def _filter_results(self):
        self._clear_results_ui()
        for r in self._results:
            if self._should_show(r):
                self._add_result_card(r)
        self._update_stats()

    def _set_all_categories(self, checked: bool):
        for cb in self._category_checks.values():
            cb.setChecked(checked)

    def _update_stats(self):
        total = len(self._results)
        found = sum(1 for r in self._results if r.is_found)
        errors = sum(1 for r in self._results if r.status in ("error", "timeout"))
        waf = sum(1 for r in self._results if r.status == "waf_blocked")
        confs = [r.confidence for r in self._results if r.is_found and r.confidence > 0]
        avg = f"{int(sum(confs)/len(confs)*100)}%" if confs else "—"

        self._stat_found.set_value(str(found))
        self._stat_total.set_value(str(total))
        self._stat_errors.set_value(str(errors + waf))
        self._stat_conf.set_value(avg)

    def _try_load_avatar(self, results: list[CheckResult]):
        for r in results:
            if r.avatar_url:
                username = self._username_input.text().strip()
                path = self._avatar_downloader.download(r.avatar_url, username, r.site_name)
                if path and os.path.exists(path):
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        return  # avatar downloaded, could show somewhere

    # ══════════════════════════════════════════════════════════════
    # NICKNAME GENERATION
    # ══════════════════════════════════════════════════════════════

    def _generate_nicknames(self):
        username = self._username_input.text().strip()
        if not username:
            return
        first = self._first_name.text().strip()
        last = self._last_name.text().strip()

        gen = NicknameGenerator(username, max_variants=200)
        self._nickname_variants = gen.generate_all(first_name=first, last_name=last)

        sx, mp = gen.phonetic_group()
        self._phonetic_text.setText(
            f"Soundex: {sx}  ·  Metaphone: {mp}"
        )

        lines = []
        for v in self._nickname_variants:
            marker = " \u25c0" if v.lower() == username.lower() else ""
            lines.append(f"{v}{marker}")
        self._nick_list.setPlainText("\n".join(lines))

    # ══════════════════════════════════════════════════════════════
    # EXPORT
    # ══════════════════════════════════════════════════════════════

    def _export_results(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, _t("uo_export_results", "Export"), "",
            "JSON (*.json);;CSV (*.csv);;Text (*.txt)",
        )
        if not path:
            return
        found = [r for r in self._results if r.is_found]
        username = self._username_input.text().strip()
        try:
            with open(path, "w", encoding="utf-8") as f:
                if path.endswith(".json"):
                    data = {
                        "username": username,
                        "found": len(found),
                        "total": len(self._results),
                        "results": [
                            {"site": r.site_name, "url": r.url, "category": r.category,
                             "status": r.status, "confidence": r.confidence_pct,
                             "response_ms": round(r.response_time_ms)}
                            for r in self._results
                        ],
                    }
                    json.dump(data, f, indent=2, ensure_ascii=False)
                elif path.endswith(".csv"):
                    f.write("site,url,category,status,confidence,response_ms\n")
                    for r in self._results:
                        f.write(f"{r.site_name},{r.url},{r.category},{r.status},"
                                f"{r.confidence_pct},{r.response_time_ms:.0f}\n")
                else:
                    f.write(f"Username OSINT: @{username}\n")
                    f.write(f"Found: {len(found)} / {len(self._results)}\n\n")
                    for r in found:
                        f.write(f"[{r.category}] {r.site_name}: {r.url}\n")
                    f.write("\n")
                    portrait = DigitalPortrait(username, self._results)
                    f.write(portrait.to_text())
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # ══════════════════════════════════════════════════════════════
    # GRAPH INTEGRATION
    # ══════════════════════════════════════════════════════════════

    def _send_to_graph(self):
        from gui.graph_model import Graph, Node, Edge

        username = self._username_input.text().strip()
        found = [r for r in self._results if r.is_found]
        if not found:
            QMessageBox.information(
                self, "Info", _t("uo_no_found", "No accounts found to graph.")
            )
            return

        graph = Graph(name=f"OSINT: @{username}", direction="LR")
        central = Node.from_type(f"@{username}", "Username")
        central.description = f"Target: {username}"
        graph.add_node(central)

        cat_nodes: dict[str, Node] = {}
        for r in found:
            cat = r.category
            if cat not in cat_nodes:
                cn = Node.from_type(f"{CATEGORY_ICONS.get(cat,'')} {cat.capitalize()}", "Category")
                cn.description = f"Category: {cat}"
                graph.add_node(cn)
                graph.add_edge(Edge(central.id, cn.id, label=cat,
                                    edge_type="BelongsToCategory", mermaid_line="-->"))
                cat_nodes[cat] = cn

            sn = Node.from_type(r.site_name, "SocialAccount")
            sn.description = r.url
            sn.metadata = {
                "url": r.url,
                "confidence": f"{r.confidence_pct}%",
                "response_ms": f"{r.response_time_ms:.0f}",
            }
            graph.add_node(sn)
            graph.add_edge(Edge(cat_nodes[cat].id, sn.id, label="registered",
                                edge_type="RegisteredOn", mermaid_line="-->"))

        for v in self._nickname_variants[:10]:
            if v.lower() != username.lower():
                an = Node.from_type(f"@{v}", "AltAccount")
                an.description = f"Possible alt: {v}"
                graph.add_node(an)
                graph.add_edge(Edge(central.id, an.id, label="alt",
                                    edge_type="AltAccountOf", mermaid_line="-.->"))

        try:
            from gui.graph_editor import GraphEditorWindow
            editor = GraphEditorWindow(self, theme_data=self.theme_data,
                                       lua_plugins=self.lua_plugins)
            editor._graph = graph
            editor._graph_name_edit.setText(graph.name)
            idx = editor._dir_combo.findText(graph.direction)
            if idx >= 0:
                editor._dir_combo.setCurrentIndex(idx)
            # Defer refresh so WebEngine has time to initialize after show()
            QTimer.singleShot(150, editor._refresh_all)
            editor.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # ══════════════════════════════════════════════════════════════
    # CLEANUP
    # ══════════════════════════════════════════════════════════════

    def closeEvent(self, event):
        self._stop_search()
        super().closeEvent(event)
