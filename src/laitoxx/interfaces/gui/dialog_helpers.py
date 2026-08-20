"""Shared helpers used by small application dialogs."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog


def build_ok_cancel_buttons(parent: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
    )
    buttons.accepted.connect(parent.accept)
    buttons.rejected.connect(parent.reject)
    return buttons


def open_file(parent: QDialog, title: str, file_filter: str) -> str | None:
    filepath, _ = QFileDialog.getOpenFileName(parent, title, "", file_filter)
    return filepath or None


def save_file(parent: QDialog, title: str, file_filter: str) -> str | None:
    filepath, _ = QFileDialog.getSaveFileName(parent, title, "", file_filter)
    return filepath or None
