"""
graph_editor.py — Modern Graph/Link editor for LAITOXX.
Glassmorphism UI, gradient buttons, real-time opacity slider.
"""
from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QTextEdit, QDialog, QDialogButtonBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QFrame, QColorDialog, QSizePolicy, QSpacerItem,
    QAbstractItemView, QSlider, QScrollArea,
)
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient, QPalette
from PyQt6.QtCore import (
    Qt, QUrl, pyqtSignal, pyqtSlot, QObject,
    QPropertyAnimation, QEasingCurve, QPoint,
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebChannel import QWebChannel
    HAS_WEB = True
except ImportError:
    HAS_WEB = False

from gui.graph_model import (
    Graph, Node, Edge,
    NODE_TYPES, NODE_TYPE_DEFAULTS, NODE_SHAPES,
    EDGE_TYPES, EDGE_LINE_TYPES, SHAPE_ID_TO_TOKENS,
)
from gui.mermaid_generator import generate_html, generate_mermaid
from gui.translator import translator

def _t(key: str, **kwargs) -> str:
    return translator.get(key, **kwargs)


# ===========================================================================
# Design tokens
# ===========================================================================

# Accent colors
_ACCENT       = "#c084fc"   # purple
_ACCENT2      = "#f472b6"   # pink
_ACCENT_DIM   = "#7c3aed"

# Backgrounds
_BG_DEEP      = "#0d0d1a"
_BG_PANEL     = "rgba(15, 12, 30, {a})"    # panel with variable alpha
_BG_ITEM      = "rgba(255, 255, 255, 0.04)"
_BG_ITEM_SEL  = "rgba(192, 132, 252, 0.18)"
_BG_ITEM_HOV  = "rgba(255, 255, 255, 0.07)"

# Borders
_BORDER       = "rgba(192, 132, 252, 0.25)"
_BORDER_FOCUS = "rgba(192, 132, 252, 0.7)"

# Text
_TEXT_PRI   = "#f1f0ff"
_TEXT_SEC   = "#a99fc0"
_TEXT_DIM   = "#6b6580"

# Toolbar gradient button variants
_BTN_FILE    = ("rgba(124,58,237,0.55)",  "rgba(139,92,246,0.75)",  "#7c3aed")
_BTN_EDIT    = ("rgba(14,165,233,0.45)",  "rgba(56,189,248,0.65)",  "#0ea5e9")
_BTN_DANGER  = ("rgba(220,38,38,0.45)",   "rgba(239,68,68,0.65)",   "#dc2626")
_BTN_EXPORT  = ("rgba(5,150,105,0.45)",   "rgba(16,185,129,0.65)",  "#059669")


def _panel_bg(alpha: float) -> str:
    return _BG_PANEL.format(a=alpha)


# ===========================================================================
# Styled button factory
# ===========================================================================

class GradientButton(QPushButton):
    """Pill-shaped button with gradient background and glow on hover."""

    def __init__(self, text: str, colors: tuple = _BTN_FILE, parent=None):
        super().__init__(text, parent)
        c_from, c_to, c_border = colors
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {c_from}, stop:1 {c_to});
                border: 1px solid {c_border};
                border-radius: 8px;
                color: {_TEXT_PRI};
                font-size: 12px;
                font-weight: 600;
                padding: 0 14px;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {c_to}, stop:1 {c_from});
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{
                background: {c_from};
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: rgba(80,70,100,0.3);
                border-color: rgba(255,255,255,0.08);
                color: {_TEXT_DIM};
            }}
        """)


class IconButton(QPushButton):
    """Small square icon-style button."""
    def __init__(self, text: str, tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setToolTip(tooltip)
        self.setFixedSize(32, 30)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(192,132,252,0.1);
                border: 1px solid {_BORDER};
                border-radius: 7px;
                color: {_TEXT_PRI};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba(192,132,252,0.25);
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{ background: rgba(192,132,252,0.4); }}
        """)


# ===========================================================================
# Section label (coloured title bar)
# ===========================================================================

class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(26)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.setFont(font)
        self.setStyleSheet(f"""
            QLabel {{
                color: {_ACCENT};
                background: rgba(192,132,252,0.08);
                border-bottom: 1px solid {_BORDER};
                padding: 2px 8px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
        """)


# ===========================================================================
# Glass panel (QFrame with variable alpha)
# ===========================================================================

class GlassPanel(QFrame):
    def __init__(self, alpha: float = 0.55, parent=None):
        super().__init__(parent)
        self._alpha = alpha
        self._border_color = _BORDER
        self._bg_base = "15, 10, 30"
        self._refresh_style()

    def set_alpha(self, alpha: float):
        self._alpha = max(0.05, min(1.0, alpha))
        self._refresh_style()

    def set_theme(self, border_color: str, bg_color: str = ""):
        """Update border and optional background tint from theme data."""
        self._border_color = border_color
        if bg_color:
            # Extract RGB from rgba(...) or use hex directly
            import re as _re
            m = _re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", bg_color)
            if m:
                self._bg_base = f"{m[1]}, {m[2]}, {m[3]}"
        self._refresh_style()

    def _refresh_style(self):
        a = self._alpha
        bg = f"rgba({self._bg_base}, {a:.2f})"
        self.setStyleSheet(f"""
            GlassPanel {{
                background: {bg};
                border: 1px solid {self._border_color};
                border-radius: 12px;
            }}
        """)


# ===========================================================================
# Opacity slider widget
# ===========================================================================

class OpacitySlider(QWidget):
    value_changed = pyqtSignal(float)  # 0.0 – 1.0

    def __init__(self, label: str = "Opacity", initial: float = 0.55, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(58)
        lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        layout.addWidget(lbl)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(5, 100)
        self._slider.setValue(int(initial * 100))
        self._slider.setFixedHeight(18)
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255,255,255,0.1);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px; height: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {_ACCENT}, stop:1 {_ACCENT2});
                border: none;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_ACCENT_DIM}, stop:1 {_ACCENT});
                border-radius: 2px;
            }}
        """)
        self._slider.valueChanged.connect(self._on_change)
        layout.addWidget(self._slider, 1)

        self._val_lbl = QLabel(f"{int(initial*100)}%")
        self._val_lbl.setFixedWidth(36)
        self._val_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 11px; font-weight: 600;")
        layout.addWidget(self._val_lbl)

    def _on_change(self, v: int):
        self._val_lbl.setText(f"{v}%")
        self.value_changed.emit(v / 100.0)

    def get_value(self) -> float:
        return self._slider.value() / 100.0


# ===========================================================================
# Color picker button
# ===========================================================================

def _color_button(color_str: str, on_pick) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(26, 22)
    btn.setToolTip("Pick color")
    _apply_color_btn_style(btn, color_str)
    btn.clicked.connect(lambda: _pick_color(btn, on_pick))
    return btn


def _apply_color_btn_style(btn: QPushButton, color_str: str) -> None:
    btn.setStyleSheet(
        f"background-color: {color_str}; border: 1px solid rgba(255,255,255,0.4);"
        f" border-radius: 5px;"
    )
    btn.setProperty("_color", color_str)


def _pick_color(btn: QPushButton, callback) -> None:
    current = btn.property("_color") or "#ffffff"
    color = QColorDialog.getColor(QColor(current))
    if color.isValid():
        _apply_color_btn_style(btn, color.name())
        callback(color.name())


# ===========================================================================
# Style editor
# ===========================================================================

class StyleEditor(QWidget):
    changed = pyqtSignal(str)

    def __init__(self, parent=None, is_edge: bool = False):
        super().__init__(parent)
        self._is_edge = is_edge
        self._fill   = "#cccccc"
        self._stroke = "#888888"
        self._text   = "#000000"
        self._width  = "1"
        self._dash   = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
            return l

        if not is_edge:
            layout.addWidget(_lbl(_t("ge_style_fill")))
            self._btn_fill = _color_button(self._fill, self._on_fill)
            layout.addWidget(self._btn_fill)

        layout.addWidget(_lbl(_t("ge_style_line")))
        self._btn_stroke = _color_button(self._stroke, self._on_stroke)
        layout.addWidget(self._btn_stroke)

        if not is_edge:
            layout.addWidget(_lbl(_t("ge_style_text")))
            self._btn_text = _color_button(self._text, self._on_text)
            layout.addWidget(self._btn_text)

        layout.addWidget(_lbl(_t("ge_style_width")))
        self._combo_width = QComboBox()
        self._combo_width.addItems(["1", "2", "3", "4"])
        self._combo_width.setFixedWidth(48)
        self._combo_width.currentTextChanged.connect(self._on_width)
        layout.addWidget(self._combo_width)

        layout.addWidget(_lbl(_t("ge_style_dash")))
        self._combo_dash = QComboBox()
        self._combo_dash.addItem(_t("ge_dash_solid"),  "")
        self._combo_dash.addItem(_t("ge_dash_dashed"), "5 5")
        self._combo_dash.addItem(_t("ge_dash_dotted"), "2 3")
        self._combo_dash.setFixedWidth(90)
        self._combo_dash.currentIndexChanged.connect(self._on_dash)
        layout.addWidget(self._combo_dash)

        layout.addStretch()

    def _on_fill(self, v):   self._fill   = v; self._emit()
    def _on_stroke(self, v): self._stroke = v; self._emit()
    def _on_text(self, v):   self._text   = v; self._emit()
    def _on_width(self, v):  self._width  = v; self._emit()
    def _on_dash(self, _):   self._dash   = self._combo_dash.currentData(); self._emit()

    def _emit(self):
        self.changed.emit(self.build_style())

    def build_style(self) -> str:
        parts = [f"stroke:{self._stroke}", f"stroke-width:{self._width}px"]
        if not self._is_edge:
            parts.insert(0, f"fill:{self._fill}")
            parts.append(f"color:{self._text}")
        if self._dash:
            parts.append(f"stroke-dasharray:{self._dash}")
        return ",".join(parts)

    def load_style(self, s: str) -> None:
        for part in s.split(","):
            part = part.strip()
            if part.startswith("fill:") and not self._is_edge:
                self._fill = part[5:]
                _apply_color_btn_style(self._btn_fill, self._fill)
            elif part.startswith("stroke:") and not part.startswith("stroke-"):
                self._stroke = part[7:]
                _apply_color_btn_style(self._btn_stroke, self._stroke)
            elif part.startswith("color:") and not self._is_edge:
                self._text = part[6:]
                _apply_color_btn_style(self._btn_text, self._text)
            elif part.startswith("stroke-width:"):
                w = part[13:].replace("px", "").strip()
                idx = self._combo_width.findText(w)
                if idx >= 0: self._combo_width.setCurrentIndex(idx); self._width = w
            elif part.startswith("stroke-dasharray:"):
                dash = part[17:].strip()
                for i in range(self._combo_dash.count()):
                    if self._combo_dash.itemData(i) == dash:
                        self._combo_dash.setCurrentIndex(i); self._dash = dash; break


# ===========================================================================
# Metadata table
# ===========================================================================

class MetadataTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(80)
        self.table.setMaximumHeight(120)
        layout.addWidget(self.table)

        btns = QHBoxLayout()
        add = GradientButton(_t("ge_meta_add"), _BTN_EDIT)
        add.setFixedHeight(24)
        rem = GradientButton(_t("ge_meta_remove"), _BTN_DANGER)
        rem.setFixedHeight(24)
        add.clicked.connect(self._add_row)
        rem.clicked.connect(self._del_row)
        btns.addWidget(add)
        btns.addWidget(rem)
        btns.addStretch()
        layout.addLayout(btns)

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem("key"))
        self.table.setItem(r, 1, QTableWidgetItem("value"))

    def _del_row(self):
        rows = {i.row() for i in self.table.selectedItems()}
        for r in sorted(rows, reverse=True):
            self.table.removeRow(r)

    def get_metadata(self) -> dict[str, str]:
        result = {}
        for r in range(self.table.rowCount()):
            k = self.table.item(r, 0)
            v = self.table.item(r, 1)
            if k and v:
                result[k.text()] = v.text()
        return result

    def set_metadata(self, meta: dict[str, str]) -> None:
        self.table.setRowCount(0)
        for k, v in meta.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(k))
            self.table.setItem(r, 1, QTableWidgetItem(v))


# ===========================================================================
# Shared dialog stylesheet
# ===========================================================================

def _dialog_ss() -> str:
    """Build dialog stylesheet from current module-level tokens (updated at theme change)."""
    return f"""
    QDialog, QWidget {{
        background: {_BG_DEEP};
        color: {_TEXT_PRI};
        font-family: 'Segoe UI', Arial, sans-serif;
    }}
    QLabel {{ color: {_TEXT_PRI}; font-size: 12px; }}
    QLineEdit, QTextEdit, QComboBox {{
        background: rgba(255,255,255,0.04);
        border: 1px solid {_BORDER};
        border-radius: 7px;
        color: {_TEXT_PRI};
        padding: 4px 8px;
        font-size: 12px;
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border-color: {_BORDER_FOCUS};
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: {_BG_DEEP};
        color: {_TEXT_PRI};
        selection-background-color: {_BORDER};
        border: 1px solid {_BORDER};
        border-radius: 6px;
    }}
    QTableWidget {{
        background: rgba(255,255,255,0.03);
        color: {_TEXT_PRI};
        gridline-color: rgba(255,255,255,0.07);
        border: 1px solid {_BORDER};
        border-radius: 7px;
    }}
    QHeaderView::section {{
        background: {_BORDER};
        color: {_ACCENT};
        border: none;
        padding: 4px;
        font-size: 11px;
        font-weight: 600;
    }}
    QScrollBar:vertical {{
        background: transparent; width: 8px;
    }}
    QScrollBar::handle:vertical {{
        background: {_BORDER};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {_BORDER_FOCUS};
    }}
    QDialogButtonBox QPushButton {{
        background: {_ACCENT_DIM};
        border: 1px solid {_ACCENT_DIM};
        border-radius: 7px;
        color: white;
        font-weight: 600;
        padding: 5px 18px;
        font-size: 12px;
    }}
    QDialogButtonBox QPushButton:hover {{
        background: {_ACCENT};
        border-color: {_ACCENT};
    }}
"""


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
    return lbl


# ===========================================================================
# Node Dialog
# ===========================================================================

class NodeDialog(QDialog):
    def __init__(self, parent=None, node: Optional[Node] = None, title="Add Node"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.setStyleSheet(_dialog_ss())
        self._node = node

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        hdr = QLabel(title)
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.label_edit = QLineEdit(node.label if node else "")
        self.label_edit.setPlaceholderText(_t("ge_label_placeholder"))
        form.addRow(_field_label(_t("ge_field_label")), self.label_edit)

        self.type_combo = QComboBox()
        _node_type_keys = [
            "ge_node_type_person", "ge_node_type_email", "ge_node_type_phone",
            "ge_node_type_website", "ge_node_type_company", "ge_node_type_ip",
            "ge_node_type_address", "ge_node_type_document", "ge_node_type_custom",
        ]
        for key, internal in zip(_node_type_keys, NODE_TYPES):
            self.type_combo.addItem(_t(key), internal)
        if node:
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == node.node_type:
                    self.type_combo.setCurrentIndex(i)
                    break
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow(_field_label(_t("ge_field_type")), self.type_combo)

        self.shape_combo = QComboBox()
        _shape_keys = {
            "rect": "ge_shape_rect", "round": "ge_shape_round",
            "circle": "ge_shape_circle", "diamond": "ge_shape_diamond",
            "hexagon": "ge_shape_hexagon", "flag": "ge_shape_flag",
            "trapez": "ge_shape_trapez",
        }
        for _disp, (shape_id, _o, _c) in NODE_SHAPES.items():
            self.shape_combo.addItem(_t(_shape_keys.get(shape_id, shape_id)), shape_id)
        current_shape = node.mermaid_shape if node else "rect"
        self._select_shape(current_shape)
        form.addRow(_field_label(_t("ge_field_shape")), self.shape_combo)

        self.desc_edit = QTextEdit(node.description if node else "")
        self.desc_edit.setPlaceholderText(_t("ge_desc_placeholder"))
        self.desc_edit.setMaximumHeight(60)
        form.addRow(_field_label(_t("ge_field_description")), self.desc_edit)

        layout.addLayout(form)

        # Style editor section
        se_hdr = QLabel(_t("ge_visual_style"))
        se_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(se_hdr)
        self.style_editor = StyleEditor(is_edge=False)
        if node and node.mermaid_style:
            self.style_editor.load_style(node.mermaid_style)
        layout.addWidget(self.style_editor)

        # Metadata section
        meta_hdr = QLabel(_t("ge_metadata"))
        meta_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(meta_hdr)
        self.meta_table = MetadataTable()
        if node and node.metadata:
            self.meta_table.set_metadata(node.metadata)
        layout.addWidget(self.meta_table)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _select_shape(self, shape_id: str):
        for i in range(self.shape_combo.count()):
            if self.shape_combo.itemData(i) == shape_id:
                self.shape_combo.setCurrentIndex(i)
                return
        self.shape_combo.setCurrentIndex(0)

    def _get_shape_value(self) -> str:
        return self.shape_combo.currentData() or "rect"

    def _on_type_changed(self, _index):
        internal = self.type_combo.currentData() or self.type_combo.currentText()
        defaults = NODE_TYPE_DEFAULTS.get(internal, {})
        if defaults:
            self._select_shape(defaults.get("shape", "rect"))
            self.style_editor.load_style(defaults.get("style", ""))

    def get_node(self) -> Node:
        style = self.style_editor.build_style()
        node_type = self.type_combo.currentData() or self.type_combo.currentText()
        if self._node:
            n = self._node
            n.label        = self.label_edit.text().strip() or "Node"
            n.node_type    = node_type
            n.description  = self.desc_edit.toPlainText()
            n.mermaid_shape = self._get_shape_value()
            n.mermaid_style = style
            n.metadata     = self.meta_table.get_metadata()
            return n
        return Node(
            label=self.label_edit.text().strip() or "Node",
            node_type=node_type,
            description=self.desc_edit.toPlainText(),
            mermaid_shape=self._get_shape_value(),
            mermaid_style=style,
            metadata=self.meta_table.get_metadata(),
        )


# ===========================================================================
# Edge Dialog
# ===========================================================================

class EdgeDialog(QDialog):
    def __init__(self, parent=None, edge: Optional[Edge] = None,
                 nodes: Optional[list[Node]] = None, title="Add Edge"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.setStyleSheet(_dialog_ss())
        self._edge = edge
        nodes = nodes or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        hdr = QLabel(title)
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT2};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.source_combo = QComboBox()
        self.target_combo = QComboBox()
        for n in nodes:
            display = f"{n.label}  [{n.id}]"
            self.source_combo.addItem(display, n.id)
            self.target_combo.addItem(display, n.id)
        if edge:
            self._sel(self.source_combo, edge.source_id)
            self._sel(self.target_combo, edge.target_id)
        form.addRow(_field_label(_t("ge_field_source")), self.source_combo)
        form.addRow(_field_label(_t("ge_field_target")), self.target_combo)

        self.label_edit = QLineEdit(edge.label if edge else "")
        self.label_edit.setPlaceholderText(_t("ge_edge_label_placeholder"))
        form.addRow(_field_label(_t("ge_field_label")), self.label_edit)

        _edge_type_keys = [
            "ge_edge_type_connected", "ge_edge_type_worksfor", "ge_edge_type_owns",
            "ge_edge_type_relatedto", "ge_edge_type_communicates",
            "ge_edge_type_locatedat", "ge_edge_type_memberof", "ge_edge_type_custom",
        ]
        self.type_combo = QComboBox()
        for key, internal in zip(_edge_type_keys, EDGE_TYPES):
            self.type_combo.addItem(_t(key), internal)
        if edge:
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == edge.edge_type:
                    self.type_combo.setCurrentIndex(i)
                    break
        form.addRow(_field_label(_t("ge_field_type")), self.type_combo)

        _line_keys = [
            "ge_line_arrow", "ge_line_thick", "ge_line_dotted",
            "ge_line_open", "ge_line_open_dotted", "ge_line_double",
        ]
        self.line_combo = QComboBox()
        for key, val in zip(_line_keys, EDGE_LINE_TYPES.values()):
            self.line_combo.addItem(_t(key), val)
        if edge:
            for i in range(self.line_combo.count()):
                if self.line_combo.itemData(i) == edge.mermaid_line:
                    self.line_combo.setCurrentIndex(i)
                    break
        form.addRow(_field_label(_t("ge_field_line")), self.line_combo)

        layout.addLayout(form)

        se_hdr = QLabel(_t("ge_visual_style"))
        se_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(se_hdr)
        self.style_editor = StyleEditor(is_edge=True)
        if edge and edge.mermaid_style:
            self.style_editor.load_style(edge.mermaid_style)
        layout.addWidget(self.style_editor)

        meta_hdr = QLabel(_t("ge_metadata"))
        meta_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(meta_hdr)
        self.meta_table = MetadataTable()
        if edge and edge.metadata:
            self.meta_table.set_metadata(edge.metadata)
        layout.addWidget(self.meta_table)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _sel(self, combo: QComboBox, node_id: str):
        for i in range(combo.count()):
            if combo.itemData(i) == node_id:
                combo.setCurrentIndex(i)
                return

    def get_edge(self) -> Optional[Edge]:
        src = self.source_combo.currentData()
        tgt = self.target_combo.currentData()
        if not src or not tgt:
            return None
        style = self.style_editor.build_style()
        edge_type = self.type_combo.currentData() or self.type_combo.currentText()
        if self._edge:
            e = self._edge
            e.source_id = src; e.target_id = tgt
            e.label = self.label_edit.text().strip()
            e.edge_type = edge_type
            e.mermaid_line = self.line_combo.currentData()
            e.mermaid_style = style
            e.metadata = self.meta_table.get_metadata()
            return e
        return Edge(
            source_id=src, target_id=tgt,
            label=self.label_edit.text().strip(),
            edge_type=edge_type,
            mermaid_line=self.line_combo.currentData(),
            mermaid_style=style,
            metadata=self.meta_table.get_metadata(),
        )


# ===========================================================================
# Properties panels (right column)
# ===========================================================================

class _PropPanel(GlassPanel):
    """Base for Node/Edge properties panels."""
    _edit_requested = None   # override in subclass as pyqtSignal

    def __init__(self, title: str, fields: list[str], parent=None):
        super().__init__(alpha=0.5, parent=parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color: {_ACCENT}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 0.5px;"
        )
        hdr.addWidget(self._title_lbl)
        self._btn_edit = GradientButton(_t("ge_prop_edit"), _BTN_EDIT)
        self._btn_edit.setMinimumWidth(90)
        self._btn_edit.setFixedHeight(24)
        self._btn_edit.clicked.connect(self._on_edit)
        hdr.addWidget(self._btn_edit)
        layout.addLayout(hdr)

        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setStyleSheet(f"color: {_BORDER};")
        layout.addWidget(self._sep)

        self._fields: dict[str, QLabel] = {}
        self._key_labels: list[QLabel] = []
        self._current_id: Optional[str] = None

        for key in fields:
            row = QHBoxLayout()
            row.setSpacing(4)
            k_lbl = QLabel(f"{key}:")
            k_lbl.setFixedWidth(72)
            k_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
            self._key_labels.append(k_lbl)
            val = QLabel("—")
            val.setWordWrap(True)
            val.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
            self._fields[key] = val
            row.addWidget(k_lbl)
            row.addWidget(val, 1)
            layout.addLayout(row)

        layout.addStretch()

    def apply_theme(self, accent: str, border: str, txt_sec: str, txt_dim: str):
        """Restyle panel labels from theme colours."""
        self._title_lbl.setStyleSheet(
            f"color: {accent}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;"
        )
        self._sep.setStyleSheet(f"color: {border};")
        for k_lbl in self._key_labels:
            k_lbl.setStyleSheet(f"color: {txt_dim}; font-size: 11px;")
        for val_lbl in self._fields.values():
            val_lbl.setStyleSheet(f"color: {txt_sec}; font-size: 11px;")

    def _on_edit(self):
        pass

    def _set(self, key: str, value: str):
        if key in self._fields:
            self._fields[key].setText(value or "—")

    def clear(self):
        self._current_id = None
        for lbl in self._fields.values():
            lbl.setText("—")


class NodePropertiesPanel(_PropPanel):
    node_edit_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(_t("ge_prop_node"), [
            _t("ge_prop_id"), _t("ge_prop_label"), _t("ge_prop_type"),
            _t("ge_prop_shape"), _t("ge_prop_description"), _t("ge_prop_meta"),
        ], parent)
        self._field_keys = [
            _t("ge_prop_id"), _t("ge_prop_label"), _t("ge_prop_type"),
            _t("ge_prop_shape"), _t("ge_prop_description"), _t("ge_prop_meta"),
        ]

    def load_node(self, node: Optional[Node]):
        if not node:
            self.clear()
            return
        self._current_id = node.id
        self._set(_t("ge_prop_id"), node.id)
        self._set(_t("ge_prop_label"), node.label)
        self._set(_t("ge_prop_type"), node.node_type)
        self._set(_t("ge_prop_shape"), node.mermaid_shape)
        self._set(_t("ge_prop_description"), node.description)
        meta = ", ".join(f"{k}={v}" for k, v in node.metadata.items())
        self._set(_t("ge_prop_meta"), meta)

    def _on_edit(self):
        if self._current_id:
            self.node_edit_requested.emit(self._current_id)


class EdgePropertiesPanel(_PropPanel):
    edge_edit_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(_t("ge_prop_edge"), [
            _t("ge_prop_id"), _t("ge_prop_source"), _t("ge_prop_target"),
            _t("ge_prop_label"), _t("ge_prop_type"), _t("ge_prop_line"),
        ], parent)

    def load_edge(self, edge: Optional[Edge], graph: Optional[Graph] = None):
        if not edge:
            self.clear()
            return
        self._current_id = edge.id
        self._set(_t("ge_prop_id"), edge.id)
        src_lbl = tgt_lbl = ""
        if graph:
            sn = graph.get_node(edge.source_id)
            tn = graph.get_node(edge.target_id)
            src_lbl = sn.label if sn else edge.source_id
            tgt_lbl = tn.label if tn else edge.target_id
        self._set(_t("ge_prop_source"), src_lbl)
        self._set(_t("ge_prop_target"), tgt_lbl)
        self._set(_t("ge_prop_label"), edge.label)
        self._set(_t("ge_prop_type"), edge.edge_type)
        self._set(_t("ge_prop_line"), edge.mermaid_line)

    def _on_edit(self):
        if self._current_id:
            self.edge_edit_requested.emit(self._current_id)


# ===========================================================================
# Mermaid viewer
# ===========================================================================

class MermaidView(QWidget):
    node_context_requested = pyqtSignal(str, int, int)  # node_id, x, y (client coords)
    background_context_requested = pyqtSignal(int, int)  # x, y (client coords)

    class _GraphWebBridge(QObject):
        node_context = pyqtSignal(str, int, int)
        background_context = pyqtSignal(int, int)

        @pyqtSlot(str, int, int)
        def onNodeContext(self, node_id: str, x: int, y: int):
            self.node_context.emit(node_id, x, y)

        @pyqtSlot(int, int)
        def onBackgroundContext(self, x: int, y: int):
            self.background_context.emit(x, y)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme: dict = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_WEB:
            self._web = QWebEngineView()
            self._web.setStyleSheet("border-radius: 10px;")
            self._web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self._bridge = MermaidView._GraphWebBridge()
            self._channel = QWebChannel(self._web.page())
            self._channel.registerObject("bridge", self._bridge)
            self._web.page().setWebChannel(self._channel)
            self._bridge.node_context.connect(self.node_context_requested.emit)
            self._bridge.background_context.connect(self.background_context_requested.emit)
            layout.addWidget(self._web)
            self._text = None
        else:
            self._web = None
            info = QLabel(_t("ge_no_web_engine"))
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info.setStyleSheet(
                f"color: {_ACCENT}; font-size: 13px; background: rgba(192,132,252,0.06);"
                f" border: 1px dashed {_BORDER}; border-radius: 10px; padding: 20px;"
            )
            layout.addWidget(info)
            self._text = QTextEdit()
            self._text.setReadOnly(True)
            self._text.setStyleSheet(
                f"font-family: 'Cascadia Code', Consolas, monospace; font-size: 12px;"
                f" background: rgba(0,0,0,0.3); color: {_TEXT_PRI}; border: none;"
            )
            layout.addWidget(self._text)

    def render_graph(self, graph: Graph) -> None:
        if self._web:
            self._web.setHtml(
                generate_html(graph, lang=translator.lang, theme=self._theme),
                QUrl("about:blank"),
            )
        elif self._text:
            self._text.setPlainText(generate_mermaid(graph))

    def map_web_to_global(self, x: int, y: int) -> QPoint:
        if self._web:
            return self._web.mapToGlobal(QPoint(x, y))
        return self.mapToGlobal(QPoint(x, y))


# ===========================================================================
# Vertical separator for toolbar
# ===========================================================================

def _vsep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setFixedWidth(1)
    sep.setStyleSheet(f"background: {_BORDER}; border: none;")
    return sep


# ===========================================================================
# Main Graph Editor Window
# ===========================================================================

# ===========================================================================
# Node type → suggested built-in actions
# ===========================================================================

_NODE_TYPE_ACTIONS: dict[str, list[tuple[str, str]]] = {
    # node_type → [(action_key, tool_registry_name), ...]
    "Phone":    [("ge_act_check_phone",    "Check Phone Number")],
    "Email":    [("ge_act_check_email",    "Validate Email"),
                 ("ge_act_gmail_osint",    "Gmail Osint")],
    "IP":       [("ge_act_check_ip",       "Check IP")],
    "Website":  [("ge_act_info_website",   "Info Website"),
                 ("ge_act_find_subdomains","Subdomain finder")],
    "Person":   [("ge_act_search_nick",    "Search Nick")],
    "Address":  [],
    "Company":  [("ge_act_info_website",   "Info Website")],
    "Document": [],
    "Custom":   [],
}


# ===========================================================================
# Node Action Dialog
# ===========================================================================

class NodeActionDialog(QDialog):
    """Dialog to choose and run an action on a node's value."""

    def __init__(self, parent=None, node: Optional[Node] = None,
                 builtin_actions: list[tuple[str, str]] | None = None,
                 lua_plugins: list | None = None):
        super().__init__(parent)
        self.setWindowTitle(_t("ge_act_dialog_title"))
        self.setMinimumWidth(440)
        self.setStyleSheet(_dialog_ss())
        self._node = node
        self._selected_action = None  # (type, key)  type='builtin'|'plugin'

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        hdr = QLabel(_t("ge_act_dialog_title"))
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        # Node info
        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"background: rgba(192,132,252,0.06); border: 1px solid {_BORDER};"
            f" border-radius: 8px; padding: 8px;"
        )
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        if node:
            type_lbl = QLabel(f"{_t('ge_field_type')}: {node.node_type}")
            type_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; border: none;")
            info_layout.addWidget(type_lbl)

            label_lbl = QLabel(f"{_t('ge_field_label')}: {node.label}")
            label_lbl.setStyleSheet(f"color: {_TEXT_PRI}; font-size: 13px; font-weight: 600; border: none;")
            info_layout.addWidget(label_lbl)

            # Show the "value" — use description (which often contains the actual data)
            val = self._extract_value(node)
            self._value = val
            val_lbl = QLabel(f"{_t('ge_act_value')}: {val}")
            val_lbl.setStyleSheet(f"color: {_ACCENT2}; font-size: 12px; border: none;")
            val_lbl.setWordWrap(True)
            info_layout.addWidget(val_lbl)

            # Editable value field
            self._value_edit = QLineEdit(val)
            self._value_edit.setPlaceholderText(_t("ge_act_value_placeholder"))
            info_layout.addWidget(self._value_edit)

        layout.addWidget(info_frame)

        # Actions list
        actions_lbl = QLabel(_t("ge_act_choose"))
        actions_lbl.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 6px;"
        )
        layout.addWidget(actions_lbl)

        self._actions_list = QListWidget()
        self._actions_list.setStyleSheet(f"""
            QListWidget {{
                background: rgba(255,255,255,0.03);
                border: 1px solid {_BORDER};
                border-radius: 8px;
                color: {_TEXT_PRI};
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid rgba(255,255,255,0.04);
            }}
            QListWidget::item:selected {{
                background: rgba(192,132,252,0.2);
            }}
            QListWidget::item:hover {{
                background: rgba(255,255,255,0.06);
            }}
        """)
        self._actions_list.setMinimumHeight(140)
        self._actions_list.itemDoubleClicked.connect(self.accept)

        # Populate with builtin actions
        if builtin_actions:
            for trans_key, tool_name in builtin_actions:
                item = QListWidgetItem(f"⚙  {_t(trans_key)}")
                item.setData(Qt.ItemDataRole.UserRole, ("builtin", tool_name))
                item.setToolTip(tool_name)
                self._actions_list.addItem(item)

        # Separator if both
        if builtin_actions and lua_plugins:
            sep = QListWidgetItem(f"── {_t('ge_act_plugins')} ──")
            sep.setFlags(Qt.ItemFlag.NoItemFlags)
            self._actions_list.addItem(sep)

        # Populate with Lua plugins (type = "search")
        if lua_plugins:
            for plugin_meta in lua_plugins:
                item = QListWidgetItem(f"🔌  {plugin_meta.name}")
                item.setData(Qt.ItemDataRole.UserRole, ("plugin", plugin_meta))
                item.setToolTip(plugin_meta.description)
                self._actions_list.addItem(item)

        layout.addWidget(self._actions_list)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(_t("ge_act_run"))
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _extract_value(self, node: Node) -> str:
        """Extract the most useful value from a node for passing to a tool."""
        desc = node.description.strip()
        # If description has meaningful data (not just a source label), use first line
        if desc:
            lines = [l.strip() for l in desc.split("\n") if l.strip()]
            # Skip lines that look like labels ("key: value" → take value)
            for line in lines:
                if ": " in line:
                    return line.split(": ", 1)[1]
                return line
        return node.label

    def get_result(self) -> tuple | None:
        """Returns (action_type, action_data, value) or None."""
        item = self._actions_list.currentItem()
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return None
        value = self._value_edit.text().strip() if hasattr(self, '_value_edit') else self._value
        return (data[0], data[1], value)


class GraphEditorWindow(QDialog):
    # Signal emitted when user wants to run an action from graph editor
    # (action_type: str, action_data: object, value: str)
    run_action_requested = pyqtSignal(str, object, str)

    def __init__(self, parent=None, theme_data: Optional[dict] = None,
                 lua_plugins: list | None = None):
        super().__init__(parent)
        self.setWindowTitle(_t("graph_editor_title"))
        self.setMinimumSize(1140, 720)
        self._graph = Graph(name=_t("ge_new_graph_name"))
        self._current_filepath: Optional[str] = None
        self._theme = theme_data or {}
        self._panel_alpha = 0.55
        self._lua_plugins = lua_plugins or []

        self._build_ui()
        self.update_theme(self._theme)
        self._refresh_all()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(6)

        root.addLayout(self._build_toolbar())

        # Opacity control bar
        root.addLayout(self._build_opacity_bar())

        # Thin accent line
        self._accent_line = QFrame()
        self._accent_line.setFrameShape(QFrame.Shape.HLine)
        self._accent_line.setFixedHeight(1)
        self._accent_line.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 transparent, stop:0.3 {_ACCENT}, stop:0.7 {_ACCENT2}, stop:1 transparent);"
            f" border: none;"
        )
        root.addWidget(self._accent_line)

        # Main area
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setHandleWidth(2)
        self._main_splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {_BORDER}; }}"
        )

        self._left_panel  = self._build_left_panel()
        self._center_panel = self._build_center_panel()
        self._right_panel  = self._build_right_panel()

        self._main_splitter.addWidget(self._left_panel)
        self._main_splitter.addWidget(self._center_panel)
        self._main_splitter.addWidget(self._right_panel)
        self._main_splitter.setSizes([230, 670, 240])
        self._main_splitter.setChildrenCollapsible(False)
        root.addWidget(self._main_splitter, 1)

        # Status bar
        status_bar = QHBoxLayout()
        self._status = QLabel(_t("ge_status_ready"))
        self._status.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 11px;"
        )
        self._node_count = QLabel(_t("ge_node_count", n=0))
        self._node_count.setStyleSheet(
            f"color: {_ACCENT}; font-size: 11px; font-weight: 600;"
        )
        self._edge_count = QLabel(_t("ge_edge_count", n=0))
        self._edge_count.setStyleSheet(
            f"color: {_ACCENT2}; font-size: 11px; font-weight: 600;"
        )
        status_bar.addWidget(self._status)
        status_bar.addStretch()
        status_bar.addWidget(self._node_count)
        status_bar.addWidget(QLabel("·"))
        status_bar.addWidget(self._edge_count)
        root.addLayout(status_bar)

    def _build_toolbar(self) -> QHBoxLayout:
        tb = QHBoxLayout()
        tb.setSpacing(5)

        def gbtn(text, tip, slot, colors=_BTN_FILE):
            b = GradientButton(text, colors)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            tb.addWidget(b)
            return b

        gbtn(_t("ge_new"),     _t("ge_new"),     self._new_graph)
        gbtn(_t("ge_open"),    _t("ge_open"),    self._open_graph)
        gbtn(_t("ge_save"),    _t("ge_save"),    self._save_graph)
        gbtn(_t("ge_save_as"), _t("ge_save_as"), self._save_graph_as)

        tb.addWidget(_vsep())

        gbtn(_t("ge_add_node"), _t("ge_add_node"), self._add_node,        _BTN_EDIT)
        gbtn(_t("ge_add_edge"), _t("ge_add_edge"), self._add_edge,        _BTN_EDIT)
        gbtn(_t("ge_delete"),   _t("ge_delete"),   self._delete_selected, _BTN_DANGER)

        tb.addWidget(_vsep())

        lbl_dir = QLabel(_t("ge_direction_label"))
        lbl_dir.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        tb.addWidget(lbl_dir)
        self._dir_combo = QComboBox()
        self._dir_combo.addItems(["TD", "LR", "RL", "BT"])
        self._dir_combo.setFixedWidth(58)
        self._dir_combo.currentTextChanged.connect(self._on_direction_change)
        tb.addWidget(self._dir_combo)

        tb.addWidget(_vsep())

        gbtn(_t("ge_export"), _t("ge_export"), self._export_mermaid, _BTN_EXPORT)

        tb.addStretch()

        lbl_name = QLabel(_t("ge_name_label"))
        lbl_name.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        tb.addWidget(lbl_name)
        self._graph_name_edit = QLineEdit(_t("ge_new_graph_name"))
        self._graph_name_edit.setPlaceholderText(_t("ge_name_placeholder"))
        self._graph_name_edit.setFixedWidth(170)
        self._graph_name_edit.textChanged.connect(self._on_name_changed)
        tb.addWidget(self._graph_name_edit)

        return tb

    def _build_opacity_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(12)

        self._opacity_panels = OpacitySlider(_t("ge_panels_opacity"), 0.55)
        self._opacity_panels.value_changed.connect(self._on_panel_opacity)

        bar.addWidget(self._opacity_panels)
        bar.addStretch()
        return bar

    def _build_left_panel(self) -> GlassPanel:
        panel = GlassPanel(self._panel_alpha)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setHandleWidth(2)
        vsplit.setStyleSheet(f"QSplitter::handle {{ background: {_BORDER}; }}")

        # Nodes section
        nodes_w = QWidget()
        nodes_w.setStyleSheet("background: transparent;")
        nlay = QVBoxLayout(nodes_w)
        nlay.setContentsMargins(0, 0, 0, 0)
        nlay.setSpacing(4)
        nlay.addWidget(SectionLabel(_t("ge_section_nodes")))

        self._nodes_list = QListWidget()
        self._nodes_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._nodes_list.customContextMenuRequested.connect(self._node_list_context)
        self._nodes_list.currentItemChanged.connect(self._on_node_selected)
        self._nodes_list.setStyleSheet(self._list_style())
        nlay.addWidget(self._nodes_list)
        vsplit.addWidget(nodes_w)

        # Edges section
        edges_w = QWidget()
        edges_w.setStyleSheet("background: transparent;")
        elay = QVBoxLayout(edges_w)
        elay.setContentsMargins(0, 0, 0, 0)
        elay.setSpacing(4)
        elay.addWidget(SectionLabel(_t("ge_section_edges")))

        self._edges_list = QListWidget()
        self._edges_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._edges_list.customContextMenuRequested.connect(self._edge_list_context)
        self._edges_list.currentItemChanged.connect(self._on_edge_selected)
        self._edges_list.setStyleSheet(self._list_style(accent=_ACCENT2))
        elay.addWidget(self._edges_list)
        vsplit.addWidget(edges_w)

        vsplit.setSizes([320, 200])
        layout.addWidget(vsplit)
        return panel

    def _build_center_panel(self) -> GlassPanel:
        panel = GlassPanel(self._panel_alpha)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        layout.addWidget(SectionLabel(_t("ge_section_preview")))

        self._mermaid_view = MermaidView()
        self._mermaid_view.node_context_requested.connect(self._on_graph_node_context)
        self._mermaid_view.background_context_requested.connect(self._on_graph_background_context)
        layout.addWidget(self._mermaid_view, 1)

        # Raw code toggle
        code_hdr = QHBoxLayout()
        code_lbl = QLabel(_t("ge_mermaid_code_label"))
        code_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 10px; font-weight: 600;")
        code_hdr.addWidget(code_lbl)
        code_hdr.addStretch()
        layout.addLayout(code_hdr)

        self._raw_code = QTextEdit()
        self._raw_code.setReadOnly(True)
        self._raw_code.setMaximumHeight(110)
        self._raw_code.setStyleSheet(
            f"font-family: 'Cascadia Code', Consolas, monospace; font-size: 11px;"
            f" background: rgba(0,0,0,0.45); color: #b8a9d9;"
            f" border: 1px solid {_BORDER}; border-radius: 8px; padding: 6px;"
        )
        layout.addWidget(self._raw_code)
        return panel

    def _build_right_panel(self) -> GlassPanel:
        panel = GlassPanel(self._panel_alpha)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(SectionLabel(_t("ge_section_properties")))

        self._node_props = NodePropertiesPanel()
        self._node_props.node_edit_requested.connect(self._edit_node_by_id)
        layout.addWidget(self._node_props)

        self._edge_props = EdgePropertiesPanel()
        self._edge_props.edge_edit_requested.connect(self._edit_edge_by_id)
        layout.addWidget(self._edge_props)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------
    # List style helper
    # ------------------------------------------------------------------

    @staticmethod
    def _list_style(accent: str = _ACCENT, txt_pri: str = _TEXT_PRI,
                    bdr: str = _BORDER) -> str:
        return f"""
            QListWidget {{
                background: rgba(0,0,0,0.0);
                border: none;
                color: {txt_pri};
                font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                background: rgba(255,255,255,0.04);
                border-radius: 7px;
                padding: 5px 8px;
                margin: 1px 0;
                border: 1px solid transparent;
            }}
            QListWidget::item:hover {{
                background: rgba(255,255,255,0.07);
                border-color: {bdr};
            }}
            QListWidget::item:selected {{
                background: {bdr};
                border: 1px solid {accent};
                color: white;
            }}
        """

    # ------------------------------------------------------------------
    # Opacity handler
    # ------------------------------------------------------------------

    def _on_panel_opacity(self, value: float):
        self._panel_alpha = value
        for panel in (self._left_panel, self._center_panel, self._right_panel):
            panel.set_alpha(value)

    # ------------------------------------------------------------------
    # Global stylesheet
    # ------------------------------------------------------------------

    def update_theme(self, theme_data: dict):
        """Called from MainWindow when user changes the theme."""
        self._theme = theme_data
        border = theme_data.get("border_color", theme_data.get("button_border_color", _BORDER))
        bg     = theme_data.get("panel_bg_color", theme_data.get("window_bg_color", ""))
        for panel in (self._left_panel, self._center_panel, self._right_panel):
            panel.set_theme(border, bg)
        self._apply_global_style()
        self._restyle_widgets(theme_data)

    def _restyle_widgets(self, td: dict):
        """Re-apply inline styles on widgets that were styled at build time."""
        accent   = td.get("accent_color",         _ACCENT)
        accent2  = td.get("accent_color",          _ACCENT2)  # edge count uses second accent
        dim      = td.get("accent_dim_color",      _ACCENT_DIM)
        bdr      = td.get("border_color",          td.get("button_border_color", _BORDER))
        txt_pri  = td.get("text_area_text_color",  _TEXT_PRI)
        txt_sec  = td.get("text_secondary_color",  _TEXT_SEC)
        btn_bg   = td.get("button_bg_color",       "rgba(124,58,237,0.5)")
        btn_hov  = td.get("button_hover_bg_color", "rgba(139,92,246,0.7)")
        panel_bg = td.get("panel_bg_color",        td.get("window_bg_color", ""))

        # Status bar labels
        if hasattr(self, "_status"):
            self._status.setStyleSheet(f"color: {txt_sec}; font-size: 11px;")
        if hasattr(self, "_node_count"):
            self._node_count.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: 600;")
        if hasattr(self, "_edge_count"):
            self._edge_count.setStyleSheet(f"color: {accent2}; font-size: 11px; font-weight: 600;")

        # Accent separator line
        if hasattr(self, "_accent_line"):
            self._accent_line.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 transparent, stop:0.3 {accent}, stop:0.7 {accent2}, stop:1 transparent);"
                f" border: none;"
            )

        # Splitter handles
        if hasattr(self, "_main_splitter"):
            self._main_splitter.setStyleSheet(
                f"QSplitter::handle {{ background: {bdr}; }}"
            )

        # Opacity slider
        if hasattr(self, "_opacity_panels"):
            self._opacity_panels._slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    height: 4px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    width: 14px; height: 14px;
                    margin: -5px 0;
                    border-radius: 7px;
                    background: {accent};
                    border: none;
                }}
                QSlider::sub-page:horizontal {{
                    background: {dim};
                    border-radius: 2px;
                }}
            """)

        # All nested QSplitter handles
        from PyQt6.QtWidgets import QSplitter as _QSplitter, QFrame as _QFrame
        for spl in self.findChildren(_QSplitter):
            spl.setStyleSheet(f"QSplitter::handle {{ background: {bdr}; }}")

        # Vertical separator lines (VLine QFrames with background: border color)
        for frm in self.findChildren(_QFrame):
            ss = frm.styleSheet()
            if ss and "background:" in ss and "border: none" in ss and frm.frameShape() in (
                _QFrame.Shape.VLine, _QFrame.Shape.HLine
            ):
                frm.setStyleSheet(f"background: {bdr}; border: none;")

        # GradientButton colours follow theme via btn_bg/btn_hov — update all GradientButtons
        # by overriding their stylesheet with theme-derived colours
        grad_ss = f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {btn_bg}, stop:1 {btn_hov});
                border: 1px solid {dim};
                border-radius: 8px;
                color: {txt_pri};
                font-size: 12px;
                font-weight: 600;
                padding: 0 14px;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {btn_hov}, stop:1 {btn_bg});
                border-color: {accent};
            }}
            QPushButton:pressed {{ background: {btn_bg}; padding-top: 2px; }}
            QPushButton:disabled {{
                background: rgba(80,70,100,0.3);
                border-color: rgba(255,255,255,0.08);
                color: {_TEXT_DIM};
            }}
        """
        # Walk all GradientButton children and restyle them
        for child in self.findChildren(GradientButton):
            child.setStyleSheet(grad_ss)

        # SectionLabel children — restyle
        sect_ss = f"""
            QLabel {{
                color: {accent};
                background: {btn_bg};
                border-bottom: 1px solid {bdr};
                padding: 2px 8px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
        """
        for child in self.findChildren(SectionLabel):
            child.setStyleSheet(sect_ss)

        # IconButton children
        icon_ss = f"""
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {bdr};
                border-radius: 7px;
                color: {txt_pri};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {btn_hov};
                border-color: {accent};
            }}
            QPushButton:pressed {{ background: {btn_hov}; }}
        """
        for child in self.findChildren(IconButton):
            child.setStyleSheet(icon_ss)

        # _PropPanel (NodePropertiesPanel / EdgePropertiesPanel)
        for prop_panel in (getattr(self, "_node_props", None), getattr(self, "_edge_props", None)):
            if prop_panel and isinstance(prop_panel, _PropPanel):
                prop_panel.apply_theme(accent, bdr, txt_sec, _TEXT_DIM)
                prop_panel.set_theme(bdr, panel_bg)

        # Node / Edge list widgets
        new_list_ss = self._list_style(accent, txt_pri, bdr)
        if hasattr(self, "_nodes_list"):
            self._nodes_list.setStyleSheet(new_list_ss)
        if hasattr(self, "_edges_list"):
            self._edges_list.setStyleSheet(new_list_ss)

        # Raw Mermaid code display
        if hasattr(self, "_raw_code"):
            self._raw_code.setStyleSheet(
                f"font-family: 'Cascadia Code', Consolas, monospace; font-size: 11px;"
                f" background: rgba(0,0,0,0.45); color: {txt_sec};"
                f" border: 1px solid {bdr}; border-radius: 8px; padding: 6px;"
            )

        # Update MermaidView theme and re-render graph with new colors
        if hasattr(self, "_mermaid_view"):
            self._mermaid_view._theme = td
            self._mermaid_view.render_graph(self._graph)

        # Re-colour all plain QLabel children that have inline colour styles.
        # We distinguish role by inspecting current style string for known token values.
        _ACCENT_VALS  = {"#c084fc", "#f472b6", "#7c3aed"}  # default purple accents
        _SEC_VALS     = {"#a99fc0"}
        _DIM_VALS     = {"#6b6580"}
        _PRI_VALS     = {"#f1f0ff"}
        from PyQt6.QtWidgets import QLabel as _QLabel
        import re as _re
        _color_re = _re.compile(r"color\s*:\s*([^;\"']+)")
        _bg_re    = _re.compile(r"background\s*:\s*rgba\(\s*192\s*,\s*132\s*,\s*252\s*,\s*[\d.]+\s*\)")
        for lbl in self.findChildren(_QLabel):
            ss = lbl.styleSheet()
            if not ss:
                continue
            changed = False
            # Replace hardcoded purple rgba backgrounds
            if "rgba(192" in ss and "252" in ss:
                new_ss = _bg_re.sub(f"background: {btn_bg}", ss)
                if new_ss != ss:
                    ss = new_ss
                    changed = True
            if "color" in ss:
                m = _color_re.search(ss)
                if m:
                    cur = m.group(1).strip().lower()
                    if cur in {v.lower() for v in _ACCENT_VALS}:
                        ss = _color_re.sub(f"color: {accent}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _SEC_VALS}:
                        ss = _color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _DIM_VALS}:
                        ss = _color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _PRI_VALS}:
                        ss = _color_re.sub(f"color: {txt_pri}", ss)
                        changed = True
            if changed:
                lbl.setStyleSheet(ss)

    def _apply_global_style(self):
        td = self._theme
        bg_color   = td.get("window_bg_color",       td.get("text_area_bg_color",   "rgba(13,11,26,0.95)"))
        text_color = td.get("text_area_text_color",  _TEXT_PRI)
        btn_bg     = td.get("button_bg_color",       "rgba(124,58,237,0.5)")
        btn_hover  = td.get("button_hover_bg_color", "rgba(139,92,246,0.7)")
        btn_border = td.get("border_color",          td.get("button_border_color",   _BORDER))
        btn_text   = td.get("button_text_color",     "white")
        sb_bg      = td.get("panel_bg_color",        td.get("sidebar_bg_color",      "rgba(13,11,26,0.95)"))
        accent     = td.get("accent_color",          _ACCENT)

        # Update module-level tokens so newly created widgets pick them up
        import gui.graph_editor as _self_mod
        _self_mod._ACCENT      = accent
        _self_mod._ACCENT2     = td.get("text_secondary_color", accent)
        _self_mod._ACCENT_DIM  = td.get("accent_dim_color", _ACCENT_DIM)
        _self_mod._BORDER      = btn_border
        _self_mod._BORDER_FOCUS = accent
        _self_mod._TEXT_PRI    = text_color
        _self_mod._TEXT_SEC    = td.get("text_secondary_color", _TEXT_SEC)
        _self_mod._TEXT_DIM    = td.get("text_secondary_color", _TEXT_SEC)
        _self_mod._BG_DEEP     = bg_color

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg_color};
                color: {text_color};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                font-size: 12px;
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
            QLineEdit, QComboBox {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {btn_border};
                border-radius: 7px;
                color: {text_color};
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {accent};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {sb_bg};
                color: {text_color};
                selection-background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 6px;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {btn_border};
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {btn_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QMenu {{
                background: {sb_bg};
                border: 1px solid {btn_border};
                border-radius: 8px;
                color: {text_color};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 18px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background: {btn_hover};
                color: white;
            }}
            QMessageBox {{
                background: {bg_color};
                color: {text_color};
            }}
            QMessageBox QPushButton {{
                background: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 6px;
                color: {btn_text};
                padding: 5px 14px;
                min-width: 60px;
            }}
            QMessageBox QPushButton:hover {{
                background: {btn_hover};
            }}
            QSplitter::handle {{
                background: {btn_border};
            }}
        """)

    # ------------------------------------------------------------------
    # Graph actions
    # ------------------------------------------------------------------

    def _new_graph(self):
        if self._graph.nodes or self._graph.edges:
            reply = QMessageBox.question(
                self, _t("ge_new"), _t("ge_new_graph_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._graph = Graph(name=_t("ge_new_graph_name"))
        self._current_filepath = None
        self._graph_name_edit.setText(_t("ge_new_graph_name"))
        self._refresh_all()
        self._set_status(_t("ge_new_graph_created"))

    def _open_graph(self):
        path, _ = QFileDialog.getOpenFileName(
            self, _t("ge_open"), "", "Graph JSON (*.json);;All Files (*)"
        )
        if path:
            try:
                self._graph = Graph.load_json(path)
                self._current_filepath = path
                self._graph_name_edit.setText(self._graph.name)
                idx = self._dir_combo.findText(self._graph.direction)
                if idx >= 0:
                    self._dir_combo.setCurrentIndex(idx)
                self._refresh_all()
                self._set_status(_t("ge_opened", name=os.path.basename(path)))
            except Exception as ex:
                QMessageBox.critical(self, _t("error"), _t("ge_error_open", err=ex))

    def _save_graph(self):
        if self._current_filepath:
            self._do_save(self._current_filepath)
        else:
            self._save_graph_as()

    def _save_graph_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, _t("ge_save_as"), f"{self._graph.name}.json",
            "Graph JSON (*.json);;All Files (*)"
        )
        if path:
            self._do_save(path)

    def _do_save(self, path: str):
        try:
            self._graph.save_json(path)
            self._current_filepath = path
            self._set_status(_t("ge_saved", name=os.path.basename(path)))
        except Exception as ex:
            QMessageBox.critical(self, _t("error"), _t("ge_error_save", err=ex))

    def _add_node(self):
        dlg = NodeDialog(self, title=_t("ge_dialog_add_node"))
        if dlg.exec():
            node = dlg.get_node()
            self._graph.add_node(node)
            self._refresh_all()
            self._set_status(_t("ge_node_added", label=node.label))

    def _add_edge(self):
        if len(self._graph.nodes) < 2:
            QMessageBox.information(self, _t("ge_add_edge"), _t("ge_need_2_nodes"))
            return
        dlg = EdgeDialog(self, nodes=self._graph.nodes, title=_t("ge_dialog_add_edge"))
        if dlg.exec():
            edge = dlg.get_edge()
            if edge:
                ok = self._graph.add_edge(edge)
                if ok:
                    self._refresh_all()
                    self._set_status(_t("ge_edge_added", src=edge.source_id, tgt=edge.target_id))
                else:
                    QMessageBox.warning(self, _t("error"), _t("ge_error_invalid_edge"))

    def _delete_selected(self):
        node_item = self._nodes_list.currentItem()
        if node_item:
            node_id = node_item.data(Qt.ItemDataRole.UserRole)
            node = self._graph.get_node(node_id)
            if node:
                reply = QMessageBox.question(
                    self, _t("ge_delete_node_title"),
                    _t("ge_delete_node_confirm", label=node.label),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._graph.remove_node(node_id)
                    self._refresh_all()
                    self._set_status(_t("ge_node_deleted", label=node.label))
            return
        edge_item = self._edges_list.currentItem()
        if edge_item:
            edge_id = edge_item.data(Qt.ItemDataRole.UserRole)
            edge = self._graph.get_edge(edge_id)
            if edge:
                self._graph.remove_edge(edge_id)
                self._refresh_all()
                self._set_status(_t("ge_edge_deleted", id=edge.id))

    def _export_mermaid(self):
        code = generate_mermaid(self._graph)
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("ge_dialog_mermaid_title"))
        dlg.setMinimumWidth(540)
        dlg.setStyleSheet(_dialog_ss())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(14, 14, 14, 14)
        hdr = QLabel(_t("ge_dialog_mermaid_title"))
        hdr.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {_ACCENT_DIM};")
        layout.addWidget(hdr)
        text = QTextEdit(code)
        text.setStyleSheet(
            f"font-family: 'Cascadia Code', Consolas, monospace; font-size: 12px;"
            f" background: rgba(0,0,0,0.5); color: #c4b5fd;"
            f" border: 1px solid {_BORDER}; border-radius: 8px;"
        )
        layout.addWidget(text)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    def _on_direction_change(self, direction: str):
        self._graph.direction = direction
        self._refresh_view()

    def _on_name_changed(self, name: str):
        self._graph.name = name

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def _node_list_context(self, pos):
        item = self._nodes_list.itemAt(pos)
        if not item:
            return
        node_id = item.data(Qt.ItemDataRole.UserRole)
        node = self._graph.get_node(node_id)
        if not node:
            return
        self._show_node_context_menu(node, self._nodes_list.mapToGlobal(pos))

    def _show_node_context_menu(self, node: Node, global_pos: QPoint):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        edit_act  = menu.addAction(_t("ge_ctx_edit"))
        clone_act = menu.addAction(_t("ge_ctx_clone"))
        menu.addSeparator()
        run_act = menu.addAction(_t("ge_ctx_run_action"))
        copy_act = menu.addAction(_t("ge_ctx_copy_value"))
        menu.addSeparator()
        del_act = menu.addAction(_t("ge_ctx_delete"))

        action = menu.exec(global_pos)
        if action == edit_act:
            self._edit_node_by_id(node.id)
        elif action == clone_act:
            self._clone_node(node.id)
        elif action == run_act:
            self._run_action_on_node(node)
        elif action == copy_act:
            self._copy_node_value(node)
        elif action == del_act:
            self._graph.remove_node(node.id)
            self._refresh_all()

    def _show_graph_context_menu(self, global_pos: QPoint):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        add_node = menu.addAction(_t("ge_add_node"))
        add_edge = menu.addAction(_t("ge_add_edge"))
        menu.addSeparator()
        export_act = menu.addAction(_t("ge_export"))
        action = menu.exec(global_pos)
        if action == add_node:
            self._add_node()
        elif action == add_edge:
            self._add_edge()
        elif action == export_act:
            self._export_mermaid()

    def _on_graph_node_context(self, node_id: str, x: int, y: int):
        node = self._graph.get_node(node_id)
        if not node:
            return
        global_pos = self._mermaid_view.map_web_to_global(x, y)
        self._show_node_context_menu(node, global_pos)

    def _on_graph_background_context(self, x: int, y: int):
        global_pos = self._mermaid_view.map_web_to_global(x, y)
        self._show_graph_context_menu(global_pos)

    def _edge_list_context(self, pos):
        from PyQt6.QtWidgets import QMenu
        item = self._edges_list.itemAt(pos)
        if not item:
            return
        edge_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        edit_act = menu.addAction(_t("ge_ctx_edit"))
        menu.addSeparator()
        del_act  = menu.addAction(_t("ge_ctx_delete"))
        action = menu.exec(self._edges_list.mapToGlobal(pos))
        if action == edit_act:
            self._edit_edge_by_id(edge_id)
        elif action == del_act:
            self._graph.remove_edge(edge_id)
            self._refresh_all()

    # ------------------------------------------------------------------
    # Edit existing items
    # ------------------------------------------------------------------

    def _edit_node_by_id(self, node_id: str):
        node = self._graph.get_node(node_id)
        if not node:
            return
        dlg = NodeDialog(self, node=node, title=_t("ge_dialog_edit_node", label=node.label))
        if dlg.exec():
            dlg.get_node()
            self._refresh_all()
            self._set_status(_t("ge_node_updated", label=node.label))

    def _edit_edge_by_id(self, edge_id: str):
        edge = self._graph.get_edge(edge_id)
        if not edge:
            return
        dlg = EdgeDialog(self, edge=edge, nodes=self._graph.nodes,
                         title=_t("ge_dialog_edit_edge", id=edge.id))
        if dlg.exec():
            dlg.get_edge()
            self._refresh_all()
            self._set_status(_t("ge_edge_updated", id=edge.id))

    def _clone_node(self, node_id: str):
        src = self._graph.get_node(node_id)
        if not src:
            return
        new_node = Node(
            label=src.label + _t("ge_copy_suffix"),
            node_type=src.node_type,
            description=src.description,
            metadata=dict(src.metadata),
            mermaid_shape=src.mermaid_shape,
            mermaid_style=src.mermaid_style,
        )
        self._graph.add_node(new_node)
        self._refresh_all()
        self._set_status(_t("ge_node_cloned", label=new_node.label))

    # ------------------------------------------------------------------
    # Node actions
    # ------------------------------------------------------------------

    def _run_action_on_node(self, node: Node):
        """Open the action dialog for the given node."""
        if not node:
            return
        # Get builtin actions for this node type
        builtin_actions = _NODE_TYPE_ACTIONS.get(node.node_type, [])
        # Always add Database search as universal option
        universal = [
            ("ge_act_db_search", "Database search"),
        ]
        all_builtin = list(builtin_actions)
        for u in universal:
            if u not in all_builtin:
                all_builtin.append(u)

        # Filter lua plugins — only "search" type
        search_plugins = [p for p in self._lua_plugins
                          if p.enabled and p.plugin_type == "search"]

        dlg = NodeActionDialog(
            self, node=node,
            builtin_actions=all_builtin,
            lua_plugins=search_plugins,
        )
        if dlg.exec():
            result = dlg.get_result()
            if result:
                action_type, action_data, value = result
                self.run_action_requested.emit(action_type, action_data, value)

    def _copy_node_value(self, node: Node):
        """Copy node's primary value to clipboard."""
        from PyQt6.QtWidgets import QApplication
        if not node:
            return
        desc = node.description.strip()
        # Extract the most useful value
        value = node.label
        if desc:
            lines = [l.strip() for l in desc.split("\n") if l.strip()]
            for line in lines:
                if ": " in line:
                    value = line.split(": ", 1)[1]
                    break
                else:
                    value = line
                    break
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(value)
        self._set_status(_t("ge_value_copied", value=value[:40]))

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_node_selected(self, current, previous):
        if not current:
            self._node_props.clear()
            return
        node = self._graph.get_node(current.data(Qt.ItemDataRole.UserRole))
        self._node_props.load_node(node)
        self._edge_props.clear()

    def _on_edge_selected(self, current, previous):
        if not current:
            self._edge_props.clear()
            return
        edge = self._graph.get_edge(current.data(Qt.ItemDataRole.UserRole))
        self._edge_props.load_edge(edge, self._graph)
        self._node_props.clear()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_all(self):
        self._refresh_nodes_list()
        self._refresh_edges_list()
        self._refresh_view()

    def _refresh_nodes_list(self):
        self._nodes_list.clear()
        for node in self._graph.nodes:
            item = QListWidgetItem(f"  {node.node_type}  ·  {node.label}")
            item.setData(Qt.ItemDataRole.UserRole, node.id)
            item.setToolTip(f"ID: {node.id}\n{node.description}")
            self._nodes_list.addItem(item)

    def _refresh_edges_list(self):
        self._edges_list.clear()
        for edge in self._graph.edges:
            src = self._graph.get_node(edge.source_id)
            tgt = self._graph.get_node(edge.target_id)
            s = src.label if src else edge.source_id
            t = tgt.label if tgt else edge.target_id
            prefix = f"{edge.label}  " if edge.label else ""
            item = QListWidgetItem(f"  {prefix}{s}  →  {t}")
            item.setData(Qt.ItemDataRole.UserRole, edge.id)
            self._edges_list.addItem(item)

    def _refresh_view(self):
        self._mermaid_view.render_graph(self._graph)
        self._raw_code.setPlainText(generate_mermaid(self._graph))

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self._status.setText(msg)
        self._node_count.setText(_t("ge_node_count", n=len(self._graph.nodes)))
        self._edge_count.setText(_t("ge_edge_count", n=len(self._graph.edges)))
