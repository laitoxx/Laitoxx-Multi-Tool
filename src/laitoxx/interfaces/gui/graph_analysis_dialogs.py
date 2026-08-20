"""Focused graph editor widgets and dialogs."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    QDate,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .graph_controls import GradientButton
from .graph_node_dialog import _dialog_ss, _field_label
from .graph_ui_style import *  # noqa: F403


class ShortestPathDialog(QDialog):
    """Dialog to pick source and target nodes for shortest path."""

    def __init__(self, parent=None, nodes=None):
        super().__init__(parent)
        self.setWindowTitle("Shortest Path")
        self.setMinimumWidth(400)
        self.setStyleSheet(_dialog_ss())
        nodes = nodes or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        hdr = QLabel("\u26d3  Shortest Path")
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(8)
        self.source_combo = QComboBox()
        self.target_combo = QComboBox()
        for n in nodes:
            display = f"{n.label}  [{n.id[:8]}]"
            self.source_combo.addItem(display, n.id)
            self.target_combo.addItem(display, n.id)
        if len(nodes) > 1:
            self.target_combo.setCurrentIndex(1)
        form.addRow(_field_label("Source"), self.source_combo)
        form.addRow(_field_label("Target"), self.target_combo)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_selection(self):
        return self.source_combo.currentData(), self.target_combo.currentData()


# ===========================================================================
# Centrality Dialog (M4)
# ===========================================================================


class CentralityDialog(QDialog):
    """Dialog to pick centrality metric."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Centrality Analysis")
        self.setMinimumWidth(360)
        self.setStyleSheet(_dialog_ss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        hdr = QLabel("\u25c9  Centrality Analysis")
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        desc = QLabel("Resize nodes proportionally to their centrality score.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(8)
        self.metric_combo = QComboBox()
        self.metric_combo.addItem("Degree Centrality", "degree")
        self.metric_combo.addItem("Betweenness Centrality", "betweenness")
        self.metric_combo.addItem("Closeness Centrality", "closeness")
        self.metric_combo.addItem("Eigenvector Centrality", "eigenvector")
        form.addRow(_field_label("Metric"), self.metric_combo)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_metric(self):
        return self.metric_combo.currentData()


# ===========================================================================
# Timeline Slider Widget (M5)
# ===========================================================================


class TimelineSlider(QWidget):
    """Dual date picker for temporal graph filtering."""

    range_changed = pyqtSignal(str, str)  # start_iso, end_iso

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        lbl = QLabel("\U0001f550 Timeline:")
        lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
        layout.addWidget(lbl)

        self._from = QDateEdit()
        self._from.setCalendarPopup(True)
        self._from.setDate(QDate(2000, 1, 1))
        self._from.setDisplayFormat("yyyy-MM-dd")
        self._from.setFixedWidth(120)
        self._from.setStyleSheet(self._date_ss())
        self._from.dateChanged.connect(self._emit_range)
        layout.addWidget(self._from)

        dash = QLabel("\u2014")
        dash.setStyleSheet(f"color: {_ACCENT}; font-size: 13px;")
        layout.addWidget(dash)

        self._to = QDateEdit()
        self._to.setCalendarPopup(True)
        self._to.setDate(QDate.currentDate())
        self._to.setDisplayFormat("yyyy-MM-dd")
        self._to.setFixedWidth(120)
        self._to.setStyleSheet(self._date_ss())
        self._to.dateChanged.connect(self._emit_range)
        layout.addWidget(self._to)

        self._btn_reset = GradientButton("Reset", _BTN_DANGER)
        self._btn_reset.setFixedHeight(24)
        self._btn_reset.clicked.connect(self._reset)
        layout.addWidget(self._btn_reset)

        layout.addStretch()

    def _date_ss(self):
        return f"""
            QDateEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {_BORDER};
                border-radius: 7px;
                color: {_TEXT_PRI};
                padding: 2px 6px;
                font-size: 11px;
            }}
            QDateEdit:focus {{
                border-color: {_BORDER_FOCUS};
            }}
            QDateEdit::drop-down {{
                border: none; width: 18px;
            }}
        """

    def _emit_range(self):
        start = self._from.date().toString("yyyy-MM-dd")
        end = self._to.date().toString("yyyy-MM-dd")
        self.range_changed.emit(start, end)

    def _reset(self):
        self._from.blockSignals(True)
        self._to.blockSignals(True)
        self._from.setDate(QDate(2000, 1, 1))
        self._to.setDate(QDate.currentDate())
        self._from.blockSignals(False)
        self._to.blockSignals(False)
        self.range_changed.emit("", "")
