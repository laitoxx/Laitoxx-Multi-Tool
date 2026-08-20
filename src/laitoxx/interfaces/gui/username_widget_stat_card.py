# ruff: noqa: F405
from .username_window_base import *  # noqa: F403


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
        self._value.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {color}; background: transparent;")
        top.addWidget(self._value)
        top.addStretch()
        layout.addLayout(top)

        self._label = QLabel(label)
        self._label.setStyleSheet(f"font-size: 10px; color: {_TEXT_DIM}; background: transparent;")
        layout.addWidget(self._label)

    def set_value(self, v: str):
        self._value.setText(v)
