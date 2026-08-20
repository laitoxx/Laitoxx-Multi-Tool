"""
Lua Plugin Builder - code editor with syntax highlighting, code snippets,
syntax checking, and OS-dependent template generation.
"""

import re

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QPainter,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

from laitoxx.interfaces.gui.design_system import resolved_theme

# ============================================================================
# Lua Syntax Highlighter
# ============================================================================


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor._line_number_area_width()

    def paintEvent(self, event):
        self.editor._paint_line_numbers(event)


class LuaCodeEditor(QPlainTextEdit):
    """Code editor with line numbers, auto-indent, and tab handling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._line_bg = QColor("#21252b")
        self._line_fg = QColor("#636d83")
        self._current_line = QColor("#2c313a")

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(QFontMetrics(font).horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #282c34; color: #abb2bf;"
            "  border: 1px solid #3e4451; border-radius: 4px;"
            "  selection-background-color: #3e4451;"
            "}"
        )

        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_width()
        self._highlight_current_line()

    def apply_theme(self, theme_data: dict) -> None:
        td = resolved_theme(theme_data)
        accent = QColor(td["accent_color"])
        self._line_bg = accent.darker(700)
        self._line_fg = QColor(td["text_secondary_color"])
        self._current_line = QColor(accent)
        self._current_line.setAlpha(34)
        self.setStyleSheet(
            f"QPlainTextEdit {{ background: {td['surface_work_color']}; color: {td['text_primary_color']};"
            f" border: 1px solid {td['border_subtle_color']}; border-radius: 6px;"
            f" selection-background-color: {td['accent_soft_color']}; }}"
        )
        self._line_number_area.update()
        self._highlight_current_line()

    def _line_number_area_width(self):
        digits = max(1, len(str(self.blockCount())))
        return QFontMetrics(self.font()).horizontalAdvance("9") * (digits + 2) + 6

    def _update_line_number_width(self):
        self.setViewportMargins(self._line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), self._line_number_area_width(), cr.height()))

    def _paint_line_numbers(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self._line_bg)
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(self._line_fg)
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self):
        selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self._current_line)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)
        self.setExtraSelections(selections)

    def keyPressEvent(self, event: QKeyEvent):
        # Tab -> 4 spaces
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            return
        # Auto-indent on Enter
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            line = cursor.block().text()
            indent = ""
            for ch in line:
                if ch in (" ", "\t"):
                    indent += ch
                else:
                    break
            # Increase indent after lines ending with: then, do, else, function(
            stripped = line.rstrip()
            if stripped.endswith(("then", "do", "else", "function", "repeat")):
                indent += "    "
            elif re.search(r"function\s*\(.*\)\s*$", stripped):
                indent += "    "
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return
        super().keyPressEvent(event)

    def insert_snippet(self, code: str):
        """Insert a code snippet at the current cursor position."""
        cursor = self.textCursor()
        cursor.insertText(code)
        self.setTextCursor(cursor)
        self.setFocus()
