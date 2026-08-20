"""Focused graph editor widgets and dialogs."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .graph_controls import GradientButton, _apply_color_btn_style, _color_button
from .graph_ui_style import *  # noqa: F403


class StyleEditor(QWidget):
    changed = pyqtSignal(str)

    def __init__(self, parent=None, is_edge: bool = False):
        super().__init__(parent)
        self._is_edge = is_edge
        self._fill = "#cccccc"
        self._stroke = "#888888"
        self._text = "#000000"
        self._width = "1"
        self._dash = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        def _lbl(t):
            lbl = QLabel(t)
            lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
            return lbl

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
        self._combo_dash.addItem(_t("ge_dash_solid"), "")
        self._combo_dash.addItem(_t("ge_dash_dashed"), "5 5")
        self._combo_dash.addItem(_t("ge_dash_dotted"), "2 3")
        self._combo_dash.setFixedWidth(90)
        self._combo_dash.currentIndexChanged.connect(self._on_dash)
        layout.addWidget(self._combo_dash)

        layout.addStretch()

    def _on_fill(self, v):
        self._fill = v
        self._emit()

    def _on_stroke(self, v):
        self._stroke = v
        self._emit()

    def _on_text(self, v):
        self._text = v
        self._emit()

    def _on_width(self, v):
        self._width = v
        self._emit()

    def _on_dash(self, _):
        self._dash = self._combo_dash.currentData()
        self._emit()

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
                if idx >= 0:
                    self._combo_width.setCurrentIndex(idx)
                    self._width = w
            elif part.startswith("stroke-dasharray:"):
                dash = part[17:].strip()
                for i in range(self._combo_dash.count()):
                    if self._combo_dash.itemData(i) == dash:
                        self._combo_dash.setCurrentIndex(i)
                        self._dash = dash
                        break


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
