"""Command palette and Smart Paste dialogs."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.utilities.ioc_extractor import TOOL_BY_KIND, Entity


class CommandPalette(QDialog):
    def __init__(self, commands: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get("Command Palette"))
        self.setMinimumSize(520, 430)
        self._commands = commands
        self.selected_command: tuple[str, str] | None = None
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(translator.get("Type a command or tool name..."))
        self.list = QListWidget()
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        self.search.textChanged.connect(self._filter)
        self.list.itemActivated.connect(self._accept_item)
        self._filter("")
        self.search.setFocus()

    def _filter(self, query: str):
        self.list.setUpdatesEnabled(False)
        self.list.clear()
        query = query.casefold().strip()
        for label, command in self._commands:
            if query in label.casefold():
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, command)
                self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.list.setUpdatesEnabled(True)

    def _accept_item(self, item=None):
        item = item or self.list.currentItem()
        if item:
            self.selected_command = (item.text(), item.data(Qt.ItemDataRole.UserRole))
            self.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._accept_item()
            return
        super().keyPressEvent(event)


class SmartPasteDialog(QDialog):
    def __init__(self, entities: list[Entity], parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get("Smart Paste"))
        self.setMinimumSize(560, 400)
        self.entities = entities
        self.action: str | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(translator.get("Recognized entities")))
        self.list = QListWidget()
        for entity in entities:
            item = QListWidgetItem(f"{entity.kind.upper():10}  {entity.value}")
            item.setData(Qt.ItemDataRole.UserRole, entity)
            self.list.addItem(item)
        if entities:
            self.list.setCurrentRow(0)
        layout.addWidget(self.list)
        buttons = QHBoxLayout()
        run = QPushButton(translator.get("Run suggested tool"))
        graph = QPushButton(translator.get("Add all to graph"))
        extract = QPushButton(translator.get("Show extracted IOC"))
        run.clicked.connect(lambda: self._finish("run"))
        graph.clicked.connect(lambda: self._finish("graph"))
        extract.clicked.connect(lambda: self._finish("extract"))
        buttons.addWidget(run)
        buttons.addWidget(graph)
        buttons.addWidget(extract)
        layout.addLayout(buttons)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

    @property
    def selected_entity(self) -> Entity | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    @property
    def suggested_tool(self) -> str | None:
        entity = self.selected_entity
        return TOOL_BY_KIND.get(entity.kind) if entity else None

    def _finish(self, action: str):
        self.action = action
        self.accept()
