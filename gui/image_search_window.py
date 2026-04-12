"""
image_search_window.py — Workspace-архитектура поиска изображений для LAITOXX.

Макет:
  Левая панель (тулбар, ~52px) | Центр (превью + результаты) | Правая панель (контекст, ~280px)

Инструменты: Поиск | Редактор | Хэши | Форензика

Зависимости вынесены в отдельные модули:
  - _style_provider.py  — все QSS-строки и фабрика кнопок
  - _image_workers.py   — QObject-воркеры для фоновых потоков
"""
from __future__ import annotations

import hashlib
import os
import random
from typing import Any

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QPixmap
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

from gui.translator import translator
from settings.theme import DEFAULT_THEME, load_default_theme
from ._image_workers import (
    ForensicsWorker,
    HashWorker,
    HAS_PIL,
    HAS_REQUESTS,
    SearchWorker,
    pil_to_qpixmap,
)
from ._style_provider import (
    ACCENT, ACCENT2, ACCENT_DIM, BG_CARD, BG_DEEP, BG_PANEL,
    BORDER, GREEN, ORANGE, RED, TEXT_DIM, TEXT_PRI, TEXT_SEC,
    build_base_style,
    engine_pill_style,
    hline_style,
    make_button,
    section_label_style,
    tool_btn_style,
)

try:
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Translation helper
# ---------------------------------------------------------------------------

def _t(key: str, fallback: str = "", **kwargs) -> str:
    raw = (
        translator.translations.get(translator.lang, {}).get(key, "")
        or fallback
        or key
    )
    if kwargs:
        try:
            return raw.format(**kwargs)
        except (KeyError, IndexError):
            return raw
    return raw


# ---------------------------------------------------------------------------
# Small reusable UI helpers
# ---------------------------------------------------------------------------

def _section_label(text: str, text_dim: str = TEXT_DIM) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(section_label_style(text_dim))
    return lbl


def _hline(border: str = BORDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(hline_style(border))
    return f


# ---------------------------------------------------------------------------
# ScalableImageLabel — превью с масштабированием и drag-and-drop
# ---------------------------------------------------------------------------

class _ScalableImageLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap_orig: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_colors(BG_CARD, BORDER, TEXT_DIM)
        self.setAcceptDrops(True)

    def _apply_colors(self, bg_card: str, border: str, text_dim: str) -> None:
        self.setStyleSheet(f"""
            background: {bg_card};
            border: 2px dashed {border};
            border-radius: 12px;
            color: {text_dim};
            font-size: 14px;
        """)
        if not self._pixmap_orig:
            self.setText(_t("is_drag_hint", "Drag image here\nor select file via 📂"))

    def set_pixmap(self, px: QPixmap) -> None:
        self._pixmap_orig = px
        self._rescale()

    def clear_image(self) -> None:
        self._pixmap_orig = None
        self.setPixmap(QPixmap())
        self.setText(_t("is_drag_hint", "Drag image here\nor select file via 📂"))

    def _rescale(self) -> None:
        if self._pixmap_orig is None or self._pixmap_orig.isNull():
            return
        scaled = self._pixmap_orig.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setText("")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale()

    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            w = self.window()
            if hasattr(w, "_load_file"):
                w._load_file(path)


# ---------------------------------------------------------------------------
# Engine groups (shared between search panel and result rendering)
# ---------------------------------------------------------------------------

_ENGINE_GROUPS: list[tuple[str, list[str]]] = [
    ("is_group_general", ["Yandex", "Google Lens", "Bing"]),
    ("is_group_anime",   ["SauceNao", "IQDB", "Ascii2D", "TraceMoe"]),
    ("is_group_asian",   ["Baidu", "Sogou"]),
    ("is_group_other",   ["TinEye"]),
]

_ENGINE_GROUP_FALLBACKS: dict[str, str] = {
    "is_group_general": "General",
    "is_group_anime":   "Anime / Art",
    "is_group_asian":   "Asian",
    "is_group_other":   "Other",
}

_DEFAULT_ENGINES_ON = {"Yandex", "Google Lens", "SauceNao", "IQDB"}

_SLIDER_DEFS: list[tuple[str, str, int, int]] = [
    ("brightness",  "is_slider_brightness",  -100, 100),
    ("contrast",    "is_slider_contrast",    -100, 100),
    ("saturation",  "is_slider_saturation",  -100, 100),
    ("exposure",    "is_slider_exposure",    -100, 100),
    ("shadows",     "is_slider_shadows",     -100, 100),
    ("highlights",  "is_slider_highlights",  -100, 100),
    ("warmth",      "is_slider_warmth",      -100, 100),
    ("sharpness",   "is_slider_sharpness",   -100, 100),
    ("blur",        "is_slider_blur",            0, 100),
    ("grain",       "is_slider_grain",           0, 100),
    ("noise",       "is_slider_noise",           0, 100),
    ("fade",        "is_slider_fade",            0, 100),
]

_HASH_ORDER = [
    "MD5", "SHA-1", "SHA-256", "SHA-512", "BLAKE2b",
    "pHash", "aHash", "dHash", "wHash",
]

_FORENSICS_CHECKS: list[tuple[str, str]] = [
    ("exif",  "is_check_exif"),
    ("ela",   "is_check_ela"),
    ("clone", "is_check_clone"),
    ("noise", "is_check_noise"),
    ("color", "is_check_color"),
]

_FORENSICS_CHECK_FALLBACKS: dict[str, str] = {
    "is_check_exif":  "EXIF / Metadata",
    "is_check_ela":   "ELA (Error Level Analysis)",
    "is_check_clone": "Clone Detection",
    "is_check_noise": "Noise Analysis",
    "is_check_color": "Color & White Balance",
}


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class ImageSearchWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_t("is_title", "LAITOXX — Image Analysis"))
        self.setMinimumSize(520, 420)
        self.resize(980, 680)

        self._theme: dict[str, Any] = {}
        self._load_theme_from_parent()
        self._apply_style()

        # State
        self._file_path: str | None = None
        self._pil_original: "Image.Image | None" = None
        self._pil_edited:   "Image.Image | None" = None
        self._current_tool: str = "search"
        self._hashes: dict[str, str] = {}
        self._search_urls: dict[str, str] = {}
        self._show_original = False
        self._search_btn: QPushButton | None = None

        # Background threads
        self._search_thread: QThread | None = None
        self._hash_thread:   QThread | None = None
        self._forensics_thread: QThread | None = None

        # Debounce timer for editor sliders
        self._edit_timer = QTimer()
        self._edit_timer.setSingleShot(True)
        self._edit_timer.setInterval(120)
        self._edit_timer.timeout.connect(self._apply_edits)

        self._build_ui()

    # =========================================================================
    # Theme
    # =========================================================================

    def _load_theme_from_parent(self) -> None:
        td = None
        p = self.parent()
        if p and hasattr(p, "theme_data"):
            td = p.theme_data
        if not td:
            td = load_default_theme()
        self._theme = dict(DEFAULT_THEME)
        self._theme.update(td or {})

    def _tc(self) -> dict[str, str]:
        """Возвращает актуальные цветовые значения из темы."""
        td = self._theme
        return {
            "accent":     td.get("accent_color",         ACCENT),
            "accent2":    td.get("accent_color",         ACCENT2),
            "accent_dim": td.get("accent_dim_color",     ACCENT_DIM),
            "bg_deep":    td.get("window_bg_color",      td.get("text_area_bg_color", BG_DEEP)),
            "bg_card":    td.get("panel_bg_color",       BG_CARD),
            "bg_panel":   td.get("panel_bg_color",       BG_PANEL),
            "text_pri":   td.get("text_area_text_color", TEXT_PRI),
            "text_sec":   td.get("text_secondary_color", TEXT_SEC),
            "text_dim":   td.get("text_secondary_color", TEXT_DIM),
            "border":     td.get("border_color",         td.get("button_border_color", BORDER)),
        }

    def _apply_style(self) -> None:
        c = self._tc()
        self.setStyleSheet(build_base_style(
            c["accent"], c["accent_dim"], c["bg_deep"],
            c["bg_card"], c["text_pri"], c["border"],
        ))

    def update_theme(self, theme_data: dict) -> None:
        """Вызывается из MainWindow при смене темы."""
        self._theme = dict(DEFAULT_THEME)
        self._theme.update(theme_data)
        self._apply_style()
        self._restyle_all()

    def _restyle_all(self) -> None:
        """Переприменяет инлайн-стили всем элементам."""
        c = self._tc()
        ac, acd, ac2 = c["accent"], c["accent_dim"], c["accent2"]
        bd = c["border"]
        tp, ts, td = c["text_pri"], c["text_sec"], c["text_dim"]

        if hasattr(self, "_toolbar_widget"):
            self._toolbar_widget.setStyleSheet(f"background: {c['bg_panel']};")
        if hasattr(self, "_center_widget"):
            self._center_widget.setStyleSheet(f"background: {c['bg_deep']};")
        if hasattr(self, "_context_panel"):
            self._context_panel.setStyleSheet(f"background: {c['bg_panel']};")

        splitter_style = f"QSplitter::handle {{ background: {bd}; }}"
        for attr in ("_h_splitter", "_v_splitter"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(splitter_style)

        for attr, style in [
            ("_hdr_filename", f"color: {tp}; font-weight: 600;"),
            ("_hdr_size",     f"color: {ts}; font-size: 12px;"),
            ("_hdr_dims",     f"color: {ts}; font-size: 12px;"),
            ("_hdr_status",   f"color: {td}; font-size: 12px;"),
        ]:
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(style)

        if hasattr(self, "_tool_buttons"):
            self._highlight_tool(self._current_tool)

        if hasattr(self, "_preview_label"):
            self._preview_label._apply_colors(c["bg_card"], bd, td)

        if hasattr(self, "_toggle_preview_btn"):
            btn = self._toggle_preview_btn
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {ts};
                    border: 1px solid {bd}; border-radius: 6px; padding: 5px 10px;
                }}
                QPushButton:hover {{ border-color: {ac}; color: {ac}; }}
            """)

        if hasattr(self, "_forensics_btn"):
            self._forensics_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {acd}, stop:1 {ac});
                    color: white; border: none; border-radius: 8px;
                    padding: 8px 16px; font-weight: 600; font-size: 13px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {ac}, stop:1 {ac2});
                }}
            """)

        if hasattr(self, "_engine_buttons"):
            for btn in self._engine_buttons.values():
                btn.setStyleSheet(self._engine_pill_style(btn.isChecked()))

        if hasattr(self, "_hashes_placeholder"):
            self._hashes_placeholder.setStyleSheet(
                f"color: {td}; font-size: 12px; padding: 20px;")

        if hasattr(self, "_hash_row_widgets"):
            for edit in self._hash_row_widgets.values():
                edit.setStyleSheet(f"""
                    QLineEdit {{
                        background: rgba(255,255,255,0.04);
                        border: 1px solid {bd};
                        border-radius: 5px;
                        color: {tp};
                        font-family: 'Consolas', 'Courier New', monospace;
                        font-size: 10px;
                        padding: 3px 6px;
                    }}
                """)

        if hasattr(self, "_slider_labels"):
            for lbl in self._slider_labels.values():
                lbl.setStyleSheet(f"color: {ac}; font-size: 11px; font-family: monospace;")

        if hasattr(self, "_editor_btn_area"):
            self._editor_btn_area.setStyleSheet(
                f"background: {c['bg_panel']}; border-top: 1px solid {bd};")

        if hasattr(self, "_hashes_btn_area"):
            self._hashes_btn_area.setStyleSheet(
                f"background: {c['bg_panel']}; border-top: 1px solid {bd};")

    # =========================================================================
    # UI build
    # =========================================================================

    def _build_ui(self) -> None:
        c = self._tc()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {c['border']};")
        root.addWidget(sep)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._toolbar_widget = self._build_toolbar()
        body.addWidget(self._toolbar_widget)

        vsep = QFrame()
        vsep.setFixedWidth(1)
        vsep.setStyleSheet(f"background: {c['border']};")
        body.addWidget(vsep)

        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._h_splitter.setHandleWidth(1)
        self._h_splitter.setStyleSheet(f"QSplitter::handle {{ background: {c['border']}; }}")

        self._center_widget = self._build_center()
        self._h_splitter.addWidget(self._center_widget)

        self._context_panel = self._build_context_panel()
        self._h_splitter.addWidget(self._context_panel)

        self._h_splitter.setStretchFactor(0, 1)
        self._h_splitter.setStretchFactor(1, 0)
        self._h_splitter.setSizes([700, 240])

        body.addWidget(self._h_splitter, stretch=1)
        root.addLayout(body, stretch=1)

        self._restyle_all()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setFixedHeight(44)
        w.setStyleSheet(f"background: {c['bg_panel']};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(16)

        icon = QLabel("🖼")
        icon.setStyleSheet("font-size: 18px;")
        lay.addWidget(icon)

        self._hdr_filename = QLabel(_t("is_no_file", "No file selected"))
        self._hdr_filename.setStyleSheet(f"color: {c['text_pri']}; font-weight: 600;")
        lay.addWidget(self._hdr_filename)

        self._hdr_size = QLabel("")
        self._hdr_size.setStyleSheet(f"color: {c['text_sec']}; font-size: 12px;")
        lay.addWidget(self._hdr_size)

        self._hdr_dims = QLabel("")
        self._hdr_dims.setStyleSheet(f"color: {c['text_sec']}; font-size: 12px;")
        lay.addWidget(self._hdr_dims)

        lay.addStretch()

        self._hdr_status = QLabel("")
        self._hdr_status.setStyleSheet(f"color: {c['text_dim']}; font-size: 12px;")
        lay.addWidget(self._hdr_status)

        return w

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setFixedWidth(52)
        w.setStyleSheet(f"background: {c['bg_panel']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 12, 4, 12)
        lay.setSpacing(4)

        self._tool_buttons: dict[str, QPushButton] = {}
        tools = [
            ("search",    "🔍", _t("is_tool_search",    "Search")),
            ("editor",    "✏️", _t("is_tool_editor",    "Editor")),
            ("hashes",    "#️⃣", _t("is_tool_hashes",    "Hashes")),
            ("forensics", "🔬", _t("is_tool_forensics", "Forensics")),
        ]
        for key, icon, tip in tools:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(44, 44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._tool_btn_style(False))
            btn.clicked.connect(lambda _, k=key: self._switch_tool(k))
            lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._tool_buttons[key] = btn

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {c['border']}; max-height: 1px; margin: 6px 4px;")
        lay.addWidget(sep)

        open_btn = QPushButton("📂")
        open_btn.setToolTip(_t("is_open_file_tooltip", "Open file"))
        open_btn.setFixedSize(44, 44)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(self._tool_btn_style(False))
        open_btn.clicked.connect(self._browse_file)
        lay.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        lay.addStretch()
        self._highlight_tool("search")
        return w

    def _tool_btn_style(self, active: bool) -> str:
        c = self._tc()
        return tool_btn_style(active, c["accent"], c["text_pri"], c["text_dim"])

    def _highlight_tool(self, tool: str) -> None:
        for k, btn in self._tool_buttons.items():
            btn.setStyleSheet(self._tool_btn_style(k == tool))

    # ── Center ────────────────────────────────────────────────────────────────

    def _build_center(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setStyleSheet(f"background: {c['bg_deep']};")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.setHandleWidth(4)
        self._v_splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {c['border']}; }}"
        )

        # Preview block
        preview_widget = QWidget()
        preview_widget.setStyleSheet("background: transparent;")
        preview_lay = QVBoxLayout(preview_widget)
        preview_lay.setContentsMargins(12, 12, 12, 4)
        preview_lay.setSpacing(4)

        self._preview_label = _ScalableImageLabel()
        self._preview_label.setMinimumHeight(80)
        preview_lay.addWidget(self._preview_label)

        self._toggle_preview_btn = make_button(
            _t("is_toggle_before_after", "Before / After"), ghost=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
            ts=c["text_sec"], bd=c["border"],
        )
        self._toggle_preview_btn.setVisible(False)
        self._toggle_preview_btn.clicked.connect(self._toggle_original)
        preview_lay.addWidget(
            self._toggle_preview_btn, alignment=Qt.AlignmentFlag.AlignRight
        )

        # Results block
        self._results_scroll = QScrollArea()
        self._results_scroll.setWidgetResizable(True)
        self._results_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._results_scroll.setMinimumHeight(60)
        self._results_scroll.setStyleSheet("background: transparent;")

        self._results_container = QWidget()
        self._results_container.setStyleSheet("background: transparent;")
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(12, 4, 12, 12)
        self._results_layout.setSpacing(6)
        self._results_layout.addStretch()
        self._results_scroll.setWidget(self._results_container)

        self._v_splitter.addWidget(preview_widget)
        self._v_splitter.addWidget(self._results_scroll)
        self._v_splitter.setStretchFactor(0, 3)
        self._v_splitter.setStretchFactor(1, 2)
        self._v_splitter.setSizes([340, 200])

        outer.addWidget(self._v_splitter)
        return w

    # ── Context panel ─────────────────────────────────────────────────────────

    def _build_context_panel(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setMinimumWidth(180)
        w.setMaximumWidth(400)
        w.setStyleSheet(f"background: {c['bg_panel']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._ctx_search    = self._build_ctx_search()
        self._ctx_editor    = self._build_ctx_editor()
        self._ctx_hashes    = self._build_ctx_hashes()
        self._ctx_forensics = self._build_ctx_forensics()

        for panel in (self._ctx_search, self._ctx_editor,
                      self._ctx_hashes, self._ctx_forensics):
            lay.addWidget(panel, stretch=1)
            panel.setVisible(False)

        self._ctx_search.setVisible(True)
        return w

    # ── Context: Search ───────────────────────────────────────────────────────

    def _build_ctx_search(self) -> QWidget:
        c = self._tc()
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay = QVBoxLayout(outer)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 8)
        lay.setSpacing(4)

        lay.addWidget(_section_label(
            _t("is_engines_section", "Search Engines"), c["text_dim"]
        ))

        self._engine_buttons: dict[str, QPushButton] = {}
        for key, engines in _ENGINE_GROUPS:
            grp_name = _t(key, _ENGINE_GROUP_FALLBACKS[key])
            hdr = QLabel(grp_name)
            hdr.setStyleSheet(f"""
                color: {c['text_dim']};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 0 2px 0;
            """)
            lay.addWidget(hdr)
            for eng in engines:
                checked = eng in _DEFAULT_ENGINES_ON
                btn = QPushButton(eng)
                btn.setCheckable(True)
                btn.setChecked(checked)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(self._engine_pill_style(checked))
                btn.toggled.connect(lambda ch, b=btn: b.setStyleSheet(
                    self._engine_pill_style(ch)))
                lay.addWidget(btn)
                self._engine_buttons[eng] = btn

        lay.addStretch()
        scroll.setWidget(inner)
        vlay.addWidget(scroll, stretch=1)
        return outer

    def _engine_pill_style(self, checked: bool) -> str:
        c = self._tc()
        return engine_pill_style(
            checked, c["accent"], c["text_sec"], c["border"], c["text_pri"]
        )

    # ── Context: Editor ───────────────────────────────────────────────────────

    def _build_ctx_editor(self) -> QWidget:
        c = self._tc()
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay = QVBoxLayout(outer)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        lay.addWidget(_section_label(
            _t("is_editor_section", "Image Settings"), c["text_dim"]
        ))

        self._sliders: dict[str, QSlider] = {}
        self._slider_labels: dict[str, QLabel] = {}

        for key, t_key, mn, mx in _SLIDER_DEFS:
            name = _t(t_key, key.capitalize())
            row = QHBoxLayout()
            row.setSpacing(6)

            lbl_name = QLabel(name)
            lbl_name.setFixedWidth(100)
            lbl_name.setStyleSheet(f"color: {c['text_sec']}; font-size: 11px;")
            row.addWidget(lbl_name)

            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(mn, mx)
            sl.setValue(0)
            sl.setFixedHeight(18)
            row.addWidget(sl, stretch=1)

            lbl_val = QLabel("+0")
            lbl_val.setFixedWidth(36)
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl_val.setStyleSheet(f"color: {c['accent']}; font-size: 11px; font-family: monospace;")
            row.addWidget(lbl_val)

            sl.valueChanged.connect(
                lambda v, lv=lbl_val, k=key: self._on_slider_changed(k, v, lv)
            )
            self._sliders[key] = sl
            self._slider_labels[key] = lbl_val
            lay.addLayout(row)

        lay.addStretch()
        scroll.setWidget(inner)
        vlay.addWidget(scroll, stretch=1)

        self._editor_btn_area = QWidget()
        self._editor_btn_area.setStyleSheet(
            f"background: {c['bg_panel']}; border-top: 1px solid {c['border']};")
        btn_lay = QVBoxLayout(self._editor_btn_area)
        btn_lay.setContentsMargins(12, 8, 12, 12)
        btn_lay.setSpacing(6)

        reset_btn = make_button(
            _t("is_reset_btn", "Reset All"), ghost=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
            ts=c["text_sec"], bd=c["border"],
        )
        reset_btn.clicked.connect(self._reset_sliders)
        btn_lay.addWidget(reset_btn)

        save_btn = make_button(
            _t("is_save_btn", "Save Image"), accent=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
        )
        save_btn.clicked.connect(self._save_edited)
        btn_lay.addWidget(save_btn)

        vlay.addWidget(self._editor_btn_area)
        return outer

    # ── Context: Hashes ───────────────────────────────────────────────────────

    def _build_ctx_hashes(self) -> QWidget:
        c = self._tc()
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay = QVBoxLayout(outer)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self._hashes_inner = QWidget()
        self._hashes_inner.setStyleSheet("background: transparent;")
        self._hashes_vlay = QVBoxLayout(self._hashes_inner)
        self._hashes_vlay.setContentsMargins(12, 12, 12, 12)
        self._hashes_vlay.setSpacing(8)

        self._hashes_vlay.addWidget(_section_label(
            _t("is_hashes_section", "File Hashes"), c["text_dim"]
        ))

        self._hashes_placeholder = QLabel(
            _t("is_hashes_placeholder", "Load an image\nto compute hashes")
        )
        self._hashes_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hashes_placeholder.setStyleSheet(
            f"color: {c['text_dim']}; font-size: 12px; padding: 20px;")
        self._hashes_vlay.addWidget(self._hashes_placeholder)
        self._hashes_vlay.addStretch()

        self._hash_row_widgets: dict[str, QLineEdit] = {}

        scroll.setWidget(self._hashes_inner)
        vlay.addWidget(scroll, stretch=1)

        self._hashes_btn_area = QWidget()
        self._hashes_btn_area.setStyleSheet(
            f"background: {c['bg_panel']}; border-top: 1px solid {c['border']};")
        btn_lay = QVBoxLayout(self._hashes_btn_area)
        btn_lay.setContentsMargins(12, 8, 12, 12)

        cmp_btn = make_button(
            _t("is_compare_btn", "Compare with another file"), ghost=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
            ts=c["text_sec"], bd=c["border"],
        )
        cmp_btn.clicked.connect(self._compare_images)
        btn_lay.addWidget(cmp_btn)

        vlay.addWidget(self._hashes_btn_area)
        return outer

    # ── Context: Forensics ────────────────────────────────────────────────────

    def _build_ctx_forensics(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        lay.addWidget(_section_label(
            _t("is_forensics_section", "Analysis"), c["text_dim"]
        ))

        self._forensics_checks: dict[str, QCheckBox] = {}
        for key, t_key in _FORENSICS_CHECKS:
            cb = QCheckBox(_t(t_key, _FORENSICS_CHECK_FALLBACKS[t_key]))
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {c['text_sec']};
                    font-size: 12px;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 16px; height: 16px;
                    border: 1px solid {c['border']};
                    border-radius: 4px;
                    background: rgba(255,255,255,0.04);
                }}
                QCheckBox::indicator:checked {{
                    background: {c['accent_dim']};
                    border-color: {c['accent']};
                }}
            """)
            lay.addWidget(cb)
            self._forensics_checks[key] = cb

        lay.addStretch()

        self._forensics_progress = QProgressBar()
        self._forensics_progress.setRange(0, 100)
        self._forensics_progress.setValue(0)
        self._forensics_progress.setFixedHeight(6)
        self._forensics_progress.setVisible(False)
        lay.addWidget(self._forensics_progress)

        self._forensics_btn = make_button(
            _t("is_forensics_btn", "Run Analysis"), accent=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
        )
        self._forensics_btn.clicked.connect(self._start_forensics)
        lay.addWidget(self._forensics_btn)

        return w

    # =========================================================================
    # Tool switching
    # =========================================================================

    def _switch_tool(self, tool: str) -> None:
        self._current_tool = tool
        self._highlight_tool(tool)

        panels = {
            "search":    self._ctx_search,
            "editor":    self._ctx_editor,
            "hashes":    self._ctx_hashes,
            "forensics": self._ctx_forensics,
        }
        for key, panel in panels.items():
            panel.setVisible(key == tool)

        self._toggle_preview_btn.setVisible(
            tool == "editor" and self._pil_original is not None
        )
        self._clear_results()

        placeholder_map = {
            "search":    self._show_search_placeholder,
            "editor":    self._show_editor_status,
            "hashes":    self._show_hashes_note,
            "forensics": self._show_forensics_placeholder,
        }
        placeholder_map[tool]()

    def _clear_results(self) -> None:
        self._search_btn = None
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_result_widget(self, w: QWidget) -> None:
        self._results_layout.insertWidget(self._results_layout.count() - 1, w)

    # =========================================================================
    # File loading
    # =========================================================================

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, _t("is_open_file_dialog", "Open Image"), "",
            _t("is_file_filter",
               "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.tif);;All Files (*)"),
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        if not HAS_PIL:
            QMessageBox.critical(self, _t("error", "Error"),
                                 _t("is_no_pil", "Pillow not installed."))
            return
        if not os.path.isfile(path):
            QMessageBox.warning(self, _t("error", "Error"),
                                f"{_t('file_not_found', 'File not found')}:\n{path}")
            return
        try:
            pil = Image.open(path)
            pil.load()
        except Exception as e:
            QMessageBox.critical(self, _t("error", "Error"), str(e))
            return

        self._file_path = path
        self._pil_original = pil.copy()
        self._pil_edited   = pil.copy()
        self._hashes = {}
        self._search_urls = {}

        fname = os.path.basename(path)
        fsize = os.path.getsize(path)
        w, h  = pil.size
        self._hdr_filename.setText(fname)
        self._hdr_size.setText(self._fmt_size(fsize))
        self._hdr_dims.setText(f"{w} × {h} px")
        self._hdr_status.setText(_t("is_loaded", "Loaded"))

        self._update_preview(pil)
        self._switch_tool("search")
        self._compute_hashes()

    @staticmethod
    def _fmt_size(sz: int) -> str:
        if sz < 1024:
            return f"{sz} Б"
        if sz < 1024 * 1024:
            return f"{sz / 1024:.1f} КБ"
        return f"{sz / 1024 / 1024:.2f} МБ"

    def _update_preview(self, pil_img: "Image.Image | None" = None) -> None:
        if pil_img is None:
            pil_img = self._pil_edited
        if pil_img is None:
            return
        self._preview_label.set_pixmap(pil_to_qpixmap(pil_img))

    # =========================================================================
    # Search
    # =========================================================================

    def _show_search_placeholder(self) -> None:
        c = self._tc()
        self._search_btn = make_button(
            _t("is_search_btn", "Upload & Search"), accent=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
        )
        self._search_btn.clicked.connect(self._start_search)
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wlay = QHBoxLayout(wrapper)
        wlay.setContentsMargins(0, 8, 0, 8)
        wlay.addStretch()
        wlay.addWidget(self._search_btn)
        wlay.addStretch()
        self._add_result_widget(wrapper)

    def _start_search(self) -> None:
        if not self._pil_original:
            QMessageBox.information(self, _t("error", "Error"),
                                    _t("is_no_image", "Please load an image first."))
            return
        if not HAS_REQUESTS:
            QMessageBox.warning(self, _t("error", "Error"),
                                _t("is_no_requests",
                                   "requests library not installed.\nSearch unavailable."))
            return

        selected = [eng for eng, btn in self._engine_buttons.items() if btn.isChecked()]
        if not selected:
            QMessageBox.information(self, _t("error", "Error"),
                                    _t("is_no_engines",
                                       "Select at least one search engine."))
            return

        c = self._tc()
        if self._search_btn:
            self._search_btn.setEnabled(False)
            self._search_btn.setText(_t("is_searching_btn", "Uploading..."))
        self._hdr_status.setText(_t("is_searching", "Loading image…"))
        self._clear_results()

        prog_lbl = QLabel(_t("is_upload_progress", "Uploading to server…"))
        prog_lbl.setStyleSheet(f"color: {c['text_sec']}; padding: 8px;")
        self._add_result_widget(prog_lbl)

        self._search_thread = QThread()
        self._search_worker = SearchWorker(self._pil_original, selected)
        self._search_worker.moveToThread(self._search_thread)
        self._search_thread.started.connect(self._search_worker.run)
        self._search_worker.finished.connect(self._on_search_done)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.finished.connect(self._search_thread.quit)
        self._search_worker.error.connect(self._search_thread.quit)
        self._search_thread.start()

    def _on_search_error(self, msg: str) -> None:
        if self._search_btn:
            self._search_btn.setEnabled(True)
            self._search_btn.setText(_t("is_search_btn", "Upload & Search"))
        self._hdr_status.setText(_t("is_search_error", "Search error"))
        self._clear_results()
        err = QLabel(f"{_t('error', 'Error')}: {msg}")
        err.setStyleSheet(f"color: {RED}; padding: 8px;")
        err.setWordWrap(True)
        self._add_result_widget(err)

    def _on_search_done(self, urls: dict) -> None:
        c = self._tc()
        self._search_urls = urls
        if self._search_btn:
            self._search_btn.setEnabled(True)
            self._search_btn.setText(_t("is_search_btn", "Upload & Search"))
        self._hdr_status.setText(
            _t("is_search_done", "Engines found: {count}").format(count=len(urls))
        )
        self._clear_results()

        if not urls:
            lbl = QLabel(_t("is_no_results", "No results."))
            lbl.setStyleSheet(f"color: {c['text_dim']}; padding: 8px;")
            self._add_result_widget(lbl)
            return

        for key, engines in _ENGINE_GROUPS:
            grp_name = _t(key, _ENGINE_GROUP_FALLBACKS[key])
            shown = [e for e in engines if e in urls]
            if not shown:
                continue
            hdr = QLabel(grp_name.upper())
            hdr.setStyleSheet(f"""
                color: {c['text_dim']};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.2px;
                padding: 8px 0 2px 0;
            """)
            self._add_result_widget(hdr)
            for eng in shown:
                self._add_result_widget(self._make_engine_result_card(eng, urls[eng]))

    def _make_engine_result_card(self, engine: str, url: str) -> QWidget:
        c = self._tc()
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        name_lbl = QLabel(engine)
        name_lbl.setStyleSheet(
            f"color: {c['text_pri']}; font-size: 12px; background: transparent; border: none;"
        )
        lay.addWidget(name_lbl, stretch=1)

        open_btn = make_button(
            _t("is_open_btn", "Open"), accent=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
        )
        open_btn.setFixedHeight(28)
        open_btn.setStyleSheet(open_btn.styleSheet() + "padding: 2px 10px; font-size: 11px;")
        open_btn.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
        lay.addWidget(open_btn)

        copy_btn = make_button(
            "⎘", ghost=True,
            ac=c["accent"], ac2=c["accent2"], acd=c["accent_dim"],
            ts=c["text_sec"], bd=c["border"],
        )
        copy_btn.setFixedSize(28, 28)
        copy_btn.setToolTip(_t("is_copy_link_tooltip", "Copy link"))
        copy_btn.clicked.connect(lambda _, u=url: (
            QApplication.clipboard().setText(u),
            copy_btn.setText("✓"),
            QTimer.singleShot(1500, lambda: copy_btn.setText("⎘")),
        ))
        lay.addWidget(copy_btn)
        return card

    # =========================================================================
    # Editor
    # =========================================================================

    def _show_editor_status(self) -> None:
        c = self._tc()
        self._editor_status_lbl = QLabel(_t("is_editor_hint", "Use sliders to edit"))
        self._editor_status_lbl.setStyleSheet(
            f"color: {c['text_dim']}; font-size: 12px; padding: 8px;")
        self._editor_status_lbl.setWordWrap(True)
        self._add_result_widget(self._editor_status_lbl)

    def _on_slider_changed(self, key: str, value: int, label: QLabel) -> None:
        sign = "+" if value >= 0 else ""
        label.setText(f"{sign}{value}")
        self._edit_timer.start()

    def _apply_edits(self) -> None:
        if not HAS_PIL or self._pil_original is None:
            return
        img = self._pil_original.copy()
        vals = {k: s.value() for k, s in self._sliders.items()}

        def _apply(v: int, fn):
            return fn() if v != 0 else img

        v = vals["brightness"]
        if v != 0:
            img = ImageEnhance.Brightness(img).enhance(1.0 + v / 100)
        v = vals["contrast"]
        if v != 0:
            img = ImageEnhance.Contrast(img).enhance(1.0 + v / 100)
        v = vals["saturation"]
        if v != 0:
            img = ImageEnhance.Color(img).enhance(1.0 + v / 100)
        v = vals["sharpness"]
        if v != 0:
            img = ImageEnhance.Sharpness(img).enhance(1.0 + v / 50)
        v = vals["exposure"]
        if v != 0:
            delta = int(v * 2.55)
            img = img.convert("RGB").point(lambda x: min(255, max(0, x + delta)))
        v = vals["shadows"]
        if v != 0:
            img = img.convert("RGB").point(
                lambda x, _v=v: min(255, max(0, x + int(_v * 0.8))) if x < 128 else x
            )
        v = vals["highlights"]
        if v != 0:
            img = img.convert("RGB").point(
                lambda x, _v=v: min(255, max(0, x + int(_v * 0.8))) if x >= 128 else x
            )
        v = vals["warmth"]
        if v != 0:
            r, g, b = img.convert("RGB").split()
            shift = int(abs(v) * 0.6)
            if v > 0:
                r = r.point(lambda x: min(255, x + shift))
                b = b.point(lambda x: max(0, x - shift))
            else:
                r = r.point(lambda x: max(0, x - shift))
                b = b.point(lambda x: min(255, x + shift))
            img = Image.merge("RGB", (r, g, b))
        v = vals["fade"]
        if v > 0:
            gray = Image.new("RGB", img.size, (128, 128, 128))
            img = Image.blend(img.convert("RGB"), gray, alpha=(v / 100) * 0.5)
        v = vals["grain"]
        if v > 0:
            noise_layer = Image.frombytes(
                "L", img.size,
                bytes([
                    min(255, max(0, 128 + random.randint(-v, v)))
                    for _ in range(img.size[0] * img.size[1])
                ]),
            )
            img = Image.merge("RGB", [
                Image.blend(ch, noise_layer, alpha=v / 300)
                for ch in img.convert("RGB").split()
            ])
        v = vals["noise"]
        if v > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
            img = ImageEnhance.Sharpness(img).enhance(1.0 + v / 200)
        v = vals["blur"]
        if v > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=v / 20))

        self._pil_edited = img
        if not self._show_original:
            self._update_preview(img)

        active = [
            f"{_t(t_key, key.capitalize())} {'+' if vals[key] > 0 else ''}{vals[key]}"
            for key, t_key, *_ in _SLIDER_DEFS
            if vals[key] != 0
        ]
        status = (
            _t("is_edited", "Edited: {changes}").format(changes=", ".join(active))
            if active else _t("is_no_changes", "No changes")
        )
        if hasattr(self, "_editor_status_lbl"):
            self._editor_status_lbl.setText(status)

    def _toggle_original(self) -> None:
        self._show_original = not self._show_original
        if self._show_original:
            self._toggle_preview_btn.setText(_t("is_toggle_show_result", "Show Result"))
            self._update_preview(self._pil_original)
        else:
            self._toggle_preview_btn.setText(_t("is_toggle_before_after", "Before / After"))
            self._update_preview(self._pil_edited)

    def _reset_sliders(self) -> None:
        for sl in self._sliders.values():
            sl.blockSignals(True)
            sl.setValue(0)
            sl.blockSignals(False)
        for lbl in self._slider_labels.values():
            lbl.setText("+0")
        if self._pil_original:
            self._pil_edited = self._pil_original.copy()
            self._update_preview(self._pil_edited)
        if hasattr(self, "_editor_status_lbl"):
            self._editor_status_lbl.setText(_t("is_no_changes", "No changes"))

    def _save_edited(self) -> None:
        if not self._pil_edited:
            QMessageBox.information(self, _t("error", "Error"),
                                    _t("is_no_image", "Please load an image first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, _t("is_save_file_dialog", "Save Image"), "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp)",
        )
        if path:
            try:
                self._pil_edited.convert("RGB").save(path)
                self._hdr_status.setText(_t("is_saved", "Saved"))
                QMessageBox.information(
                    self, _t("is_saved", "Saved"),
                    f"{_t('is_saved', 'Saved')}:\n{path}",
                )
            except Exception as e:
                QMessageBox.critical(self, _t("error", "Error"), str(e))

    # =========================================================================
    # Hashes
    # =========================================================================

    def _show_hashes_note(self) -> None:
        c = self._tc()
        lbl = QLabel(_t("is_hashes_note", "Hashes are shown in the right panel."))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {c['text_dim']}; font-size: 13px; padding: 20px;")
        self._add_result_widget(lbl)

    def _compute_hashes(self) -> None:
        if not self._file_path or not self._pil_original:
            return
        self._hash_thread = QThread()
        self._hash_worker = HashWorker(self._file_path, self._pil_original)
        self._hash_worker.moveToThread(self._hash_thread)
        self._hash_thread.started.connect(self._hash_worker.run)
        self._hash_worker.finished.connect(self._show_hashes)
        self._hash_worker.finished.connect(self._hash_thread.quit)
        self._hash_thread.start()
        self._hdr_status.setText(_t("is_computing_hashes", "Computing hashes…"))

    def _show_hashes(self, hashes: dict) -> None:
        self._hashes = hashes
        self._hdr_status.setText(_t("is_hashes_done", "Hashes computed"))

        while self._hashes_vlay.count() > 1:
            item = self._hashes_vlay.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self._hashes_vlay.removeItem(item)

        self._hashes_placeholder.setVisible(False)
        self._hash_row_widgets.clear()

        for key in _HASH_ORDER:
            self._add_hash_row(key, hashes.get(key, "—"))

        self._hashes_vlay.addStretch()

    def _add_hash_row(self, name: str, value: str) -> None:
        c = self._tc()
        row_w = QWidget()
        row_w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(row_w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        lbl = QLabel(name)
        lbl.setStyleSheet(
            f"color: {c['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;"
        )
        lay.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(4)

        edit = QLineEdit(value)
        edit.setReadOnly(True)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {c['border']};
                border-radius: 5px;
                color: {c['text_pri']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                padding: 3px 6px;
            }}
        """)
        row.addWidget(edit, stretch=1)
        self._hash_row_widgets[name] = edit

        copy_btn = QPushButton("⎘")
        copy_btn.setFixedSize(24, 24)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setToolTip(_t("is_copy_tooltip", "Copy"))
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05);
                border: 1px solid {c['border']};
                border-radius: 4px;
                color: {c['text_sec']};
                font-size: 12px;
            }}
            QPushButton:hover {{ background: rgba(192,132,252,0.2); color: {c['accent']}; }}
        """)
        copy_btn.clicked.connect(lambda _, v=value, b=copy_btn: (
            QApplication.clipboard().setText(v),
            b.setText("✓"),
            QTimer.singleShot(1200, lambda: b.setText("⎘")),
        ))
        row.addWidget(copy_btn)
        lay.addLayout(row)

        idx = max(0, self._hashes_vlay.count() - 1)
        self._hashes_vlay.insertWidget(idx, row_w)

    def _compare_images(self) -> None:
        if not HAS_PIL:
            QMessageBox.information(self, _t("error", "Error"),
                                    _t("is_no_pil", "Pillow not installed."))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, _t("is_compare_file_dialog", "Select file to compare"), "",
            _t("is_compare_file_filter",
               "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)"),
        )
        if not path:
            return
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            other_hashes = {
                "MD5":     hashlib.md5(data).hexdigest(),
                "SHA-1":   hashlib.sha1(data).hexdigest(),
                "SHA-256": hashlib.sha256(data).hexdigest(),
            }
        except Exception as e:
            QMessageBox.critical(self, _t("error", "Error"), str(e))
            return

        lines = []
        for k in ("MD5", "SHA-1", "SHA-256"):
            mine  = self._hashes.get(k, "")
            other = other_hashes.get(k, "")
            match = (
                _t("is_hash_match", "✅ match")
                if mine == other else _t("is_hash_differ", "❌ differ")
            )
            lines.append(f"{k}: {match}")

        QMessageBox.information(
            self,
            _t("is_compare_title", "Hash Comparison"),
            _t("is_compare_with", "Compared with: {name}").format(
                name=os.path.basename(path)
            ) + "\n\n" + "\n".join(lines),
        )

    # =========================================================================
    # Forensics
    # =========================================================================

    def _show_forensics_placeholder(self) -> None:
        c = self._tc()
        lbl = QLabel(_t("is_forensics_placeholder",
                        "Click «Run Analysis»\nto start forensics"))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {c['text_dim']}; font-size: 13px; padding: 20px;")
        lbl.setWordWrap(True)
        self._add_result_widget(lbl)

    def _start_forensics(self) -> None:
        if not self._pil_original:
            QMessageBox.information(self, _t("error", "Error"),
                                    _t("is_no_image", "Please load an image first."))
            return
        checks = {k: cb.isChecked() for k, cb in self._forensics_checks.items()}
        if not any(checks.values()):
            QMessageBox.information(self, _t("error", "Error"),
                                    _t("is_no_checks", "Select at least one check."))
            return

        self._forensics_btn.setEnabled(False)
        self._forensics_btn.setText(_t("is_forensics_btn_running", "Analysing…"))
        self._forensics_progress.setValue(0)
        self._forensics_progress.setVisible(True)
        self._hdr_status.setText(_t("is_forensics_running", "Forensics…"))
        self._clear_results()

        self._forensics_thread = QThread()
        self._forensics_worker = ForensicsWorker(
            self._pil_original, self._file_path or "", checks
        )
        self._forensics_worker.moveToThread(self._forensics_thread)
        self._forensics_thread.started.connect(self._forensics_worker.run)
        self._forensics_worker.progress.connect(self._forensics_progress.setValue)
        self._forensics_worker.finished.connect(self._on_forensics_done)
        self._forensics_worker.finished.connect(self._forensics_thread.quit)
        self._forensics_thread.start()

    def _on_forensics_done(self, report: dict) -> None:
        self._forensics_btn.setEnabled(True)
        self._forensics_btn.setText(_t("is_forensics_btn", "Run Analysis"))
        self._forensics_progress.setValue(100)
        self._hdr_status.setText(_t("is_forensics_done", "Forensics complete"))
        self._render_forensics_report(report)

    def _render_forensics_report(self, report: dict) -> None:
        self._clear_results()
        c = self._tc()
        ac, tp, ts, td = c["accent"], c["text_pri"], c["text_sec"], c["text_dim"]

        te = QTextEdit()
        te.setReadOnly(True)
        te.setMinimumHeight(220)
        te.setStyleSheet(f"""
            QTextEdit {{
                background: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                color: {tp};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 12px;
            }}
        """)

        html_parts: list[str] = []
        suspicious_count = 0
        verdict_notes: list[str] = []
        ela_image = None

        # EXIF
        if "exif" in report:
            exif = report["exif"]
            if "error" in exif:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ EXIF: {_t("error","Error")} — {exif["error"]}</span></p>'
                )
            else:
                html_parts.append(
                    f'<p><b style="color:{ac}">{_t("is_exif_section","📋 EXIF / Metadata")}</b></p>'
                )
                raw = exif.get("raw", {})
                for k, v in list(raw.items())[:20]:
                    html_parts.append(
                        f'<p style="margin:1px 0"><span style="color:{td}">{k}:</span> '
                        f'<span style="color:{ts}">{v}</span></p>'
                    )
                flags = exif.get("flags", [])
                for fl in flags:
                    html_parts.append(f'<p style="color:{ORANGE}">⚠ {fl}</p>')
                    suspicious_count += 1
                    verdict_notes.append(fl)
                if not flags and raw:
                    html_parts.append(
                        f'<p style="color:{GREEN}">{_t("is_exif_no_flags","✓ No suspicious signs found")}</p>'
                    )

        # ELA
        if "ela" in report:
            ela = report["ela"]
            if "error" in ela:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ ELA: {_t("error","Error")} — {ela["error"]}</span></p>'
                )
            else:
                ela_image = ela.get("ela_image")
                mean_v = ela.get("mean", 0)
                is_susp = ela.get("verdict", "") == "подозрительно"
                color = RED if is_susp else GREEN
                verdict_str = (
                    _t("is_ela_verdict_suspicious", "suspicious")
                    if is_susp else _t("is_ela_verdict_ok", "normal")
                )
                html_parts.append(
                    f'<p><b style="color:{ac}">{_t("is_ela_section","🔎 ELA (Error Level Analysis)")}</b></p>'
                )
                html_parts.append(
                    f'<p><b style="color:{color}">{mean_v}</b> — '
                    f'<span style="color:{color}">{verdict_str}</span></p>'
                )
                if is_susp:
                    suspicious_count += 1
                    verdict_notes.append(f"ELA: {mean_v}")

        # Clone
        if "clone" in report:
            cl = report["clone"]
            if "error" in cl:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ {_t("is_clone_section","Clone")}: '
                    f'{_t("error","Error")} — {cl["error"]}</span></p>'
                )
            else:
                dupes = cl.get("duplicate_blocks", 0)
                susp = cl.get("suspicious", False)
                color = RED if susp else GREEN
                html_parts.append(
                    f'<p><b style="color:{ac}">{_t("is_clone_section","🔁 Clone Detection")}</b></p>'
                )
                susp_str = (
                    _t("is_clone_suspicious", "⚠ possible clones")
                    if susp else _t("is_clone_ok", "✓ normal")
                )
                html_parts.append(
                    f'<p><b style="color:{color}">{dupes}</b>'
                    f' — <span style="color:{color}">{susp_str}</span></p>'
                )
                if susp:
                    suspicious_count += 1
                    verdict_notes.append(f"{_t('is_clone_section','Clone')}: {dupes}")

        # Noise
        if "noise" in report:
            ns = report["noise"]
            if "error" in ns:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ {_t("is_noise_section","Noise")}: '
                    f'{_t("error","Error")} — {ns["error"]}</span></p>'
                )
            else:
                susp = ns.get("suspicious", False)
                ratio = ns.get("ratio", 0)
                color = RED if susp else GREEN
                html_parts.append(
                    f'<p><b style="color:{ac}">{_t("is_noise_section","〰 Noise Analysis")}</b></p>'
                )
                susp_str = (
                    _t("is_noise_suspicious", "⚠ uneven noise")
                    if susp else _t("is_noise_ok", "✓ even")
                )
                html_parts.append(
                    f'<p><b style="color:{color}">{ratio}</b>'
                    f' — <span style="color:{color}">{susp_str}</span></p>'
                )
                if susp:
                    suspicious_count += 1
                    verdict_notes.append(f"{_t('is_noise_section','Noise')}: {ratio}")

        # Color
        if "color" in report:
            col = report["color"]
            if "error" in col:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ {_t("is_color_section","Color")}: '
                    f'{_t("error","Error")} — {col["error"]}</span></p>'
                )
            else:
                wb_map = {
                    "тёплый":     _t("is_wb_warm",    "warm"),
                    "холодный":   _t("is_wb_cool",    "cool"),
                    "нейтральный":_t("is_wb_neutral", "neutral"),
                }
                wb = wb_map.get(col.get("white_balance", ""), col.get("white_balance", "—"))
                r, g, b = col.get("r_mean", 0), col.get("g_mean", 0), col.get("b_mean", 0)
                html_parts.append(
                    f'<p><b style="color:{ac}">{_t("is_color_section","🎨 Color & White Balance")}</b></p>'
                )
                html_parts.append(
                    f'<p>{_t("is_color_channels","R/G/B channels:")} '
                    f'<span style="color:#ff7675">{r}</span> / '
                    f'<span style="color:{GREEN}">{g}</span> / '
                    f'<span style="color:#74b9ff">{b}</span></p>'
                )
                html_parts.append(
                    f'<p>{_t("is_color_wb","White balance: {wb}").format(wb=wb)}</p>'
                )

        te.setHtml("<html><body>" + "".join(html_parts) + "</body></html>")
        self._add_result_widget(te)

        # ELA image
        if ela_image is not None:
            ela_lbl_hdr = QLabel(_t("is_ela_image_label", "ELA image:"))
            ela_lbl_hdr.setStyleSheet(
                f"color: {c['text_sec']}; font-size: 12px; padding: 4px 0 2px 0;"
            )
            self._add_result_widget(ela_lbl_hdr)

            ela_px = pil_to_qpixmap(ela_image)
            ela_scaled = ela_px.scaledToWidth(
                min(ela_px.width(), 500),
                Qt.TransformationMode.SmoothTransformation,
            )
            ela_lbl = QLabel()
            ela_lbl.setPixmap(ela_scaled)
            ela_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ela_lbl.setStyleSheet(f"border: 1px solid {c['border']}; border-radius: 6px;")
            self._add_result_widget(ela_lbl)

        # Verdict banner
        if suspicious_count == 0:
            verdict_color = GREEN
            verdict_text  = _t("is_verdict_clean", "✅  No manipulation signs detected")
        elif suspicious_count == 1:
            verdict_color = ORANGE
            verdict_text  = _t("is_verdict_warn", "⚠  {count} suspicious sign detected").format(
                count=suspicious_count)
        else:
            verdict_color = RED
            verdict_text  = _t("is_verdict_danger", "🚨  {count} suspicious signs detected").format(
                count=suspicious_count)

        if verdict_notes:
            verdict_text += "\n• " + "\n• ".join(verdict_notes)

        verdict_banner = QLabel(verdict_text)
        verdict_banner.setWordWrap(True)
        verdict_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        verdict_banner.setStyleSheet(f"""
            background: {verdict_color}22;
            border: 1px solid {verdict_color}66;
            border-radius: 10px;
            color: {verdict_color};
            font-size: 13px;
            font-weight: 600;
            padding: 12px 16px;
            margin-top: 6px;
        """)
        self._add_result_widget(verdict_banner)
