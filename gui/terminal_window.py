"""
terminal_window.py — Pop-out terminal window.
Shares the same QTextEdit model as the main output_area via signal bridge.
Styled with glassmorphism to match the app theme.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QWidget, QSizeGrip,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QTextCursor


class TerminalWindow(QDialog):
    """
    Floating semi-transparent terminal that mirrors main output_area.
    - Shares text via append_text / set_text / clear_text signals.
    - Glassmorphism style: blurred dark background, accent border.
    - Frameless, draggable, resizable.
    """

    closed = pyqtSignal()

    def __init__(self, theme_data: dict, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(520, 340)
        self.resize(820, 520)
        self._theme = theme_data
        self._drag_pos: QPoint | None = None

        self._build_ui()
        self._apply_style()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # Glass card container
        self._card = QWidget(self)
        self._card.setObjectName("termCard")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── Title bar ────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(34)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 8, 0)
        tb_layout.setSpacing(6)

        dot_red   = self._dot("#ff5f57")
        dot_amber = self._dot("#ffbd2e")
        dot_green = self._dot("#28c941")
        tb_layout.addWidget(dot_red)
        tb_layout.addWidget(dot_amber)
        tb_layout.addWidget(dot_green)

        self._title_lbl = QLabel("Terminal")
        self._title_lbl.setObjectName("termTitle")
        tb_layout.addWidget(self._title_lbl, 1, Qt.AlignmentFlag.AlignCenter)

        btn_clear = QPushButton("⌫")
        btn_clear.setObjectName("termBtn")
        btn_clear.setFixedSize(26, 26)
        btn_clear.setToolTip("Clear output")
        btn_clear.clicked.connect(self._output.clear if hasattr(self, "_output") else lambda: None)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("termBtnClose")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.close)

        tb_layout.addWidget(btn_clear)
        tb_layout.addWidget(btn_close)

        card_layout.addWidget(title_bar)

        # ── Separator line ───────────────────────────────────────────
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setObjectName("termSep")
        card_layout.addWidget(sep)

        # ── Output area ──────────────────────────────────────────────
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setObjectName("termOutput")
        self._output.setMaximumBlockCount(2000)
        card_layout.addWidget(self._output, 1)

        # Fix clear button now that _output exists
        btn_clear.clicked.disconnect()
        btn_clear.clicked.connect(self._output.clear)

        # ── Resize grip ──────────────────────────────────────────────
        grip_row = QHBoxLayout()
        grip_row.addStretch()
        grip = QSizeGrip(self._card)
        grip.setFixedSize(14, 14)
        grip_row.addWidget(grip)
        grip_row.setContentsMargins(0, 0, 4, 4)
        card_layout.addLayout(grip_row)

        root.addWidget(self._card)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def _apply_style(self):
        td = self._theme
        bg       = td.get("window_bg_color",       td.get("text_area_bg_color",      "rgba(10,8,24,0.88)"))
        panel_bg = td.get("panel_bg_color",         "rgba(20,14,40,0.75)")
        text     = td.get("text_area_text_color",   "#e2dff5")
        accent   = td.get("accent_color",           "#c084fc")
        bdr      = td.get("border_color",           td.get("button_border_color",     "rgba(192,132,252,0.35)"))
        btn_bg   = td.get("button_bg_color",        "rgba(192,132,252,0.12)")
        btn_hov  = td.get("button_hover_bg_color",  "rgba(192,132,252,0.25)")
        txt_sec  = td.get("text_secondary_color",   "rgba(200,180,255,0.8)")
        sb_hand  = td.get("scrollbar_handle_color", bdr)
        sb_hov   = td.get("scrollbar_handle_hover_color", btn_hov)

        self.setStyleSheet(f"""
            #termCard {{
                background: {bg};
                border: 1px solid {bdr};
                border-radius: 14px;
            }}
            #titleBar {{
                background: {panel_bg};
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }}
            #termTitle {{
                color: {accent};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            #termSep {{
                background: {bdr};
            }}
            #termOutput {{
                background: transparent;
                color: {text};
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                border: none;
                padding: 10px 14px;
                selection-background-color: {btn_hov};
            }}
            #termBtn {{
                background: {btn_bg};
                border: 1px solid {bdr};
                border-radius: 5px;
                color: {txt_sec};
                font-size: 11px;
            }}
            #termBtn:hover {{
                background: {btn_hov};
                color: white;
            }}
            #termBtnClose {{
                background: rgba(255,80,80,0.12);
                border: 1px solid rgba(255,80,80,0.3);
                border-radius: 5px;
                color: rgba(255,100,100,0.85);
                font-size: 11px;
                font-weight: 700;
            }}
            #termBtnClose:hover {{
                background: rgba(255,80,80,0.35);
                color: white;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {sb_hand};
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {sb_hov};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

    # ------------------------------------------------------------------
    # Public API — called from main_window to mirror output
    # ------------------------------------------------------------------

    def set_text(self, text: str):
        self._output.setPlainText(text)

    def append_text(self, text: str):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def clear_text(self):
        self._output.clear()

    def get_text(self) -> str:
        return self._output.toPlainText()

    def update_theme(self, theme_data: dict):
        self._theme = theme_data
        self._apply_style()

    # ------------------------------------------------------------------
    # Dot helper
    # ------------------------------------------------------------------

    @staticmethod
    def _dot(color: str) -> QLabel:
        lbl = QLabel()
        lbl.setFixedSize(12, 12)
        lbl.setStyleSheet(
            f"background:{color}; border-radius:6px; border:none;"
        )
        return lbl

    # ------------------------------------------------------------------
    # Draggable frameless window
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only drag from title bar area (top 34px)
            if event.position().y() < 46:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
