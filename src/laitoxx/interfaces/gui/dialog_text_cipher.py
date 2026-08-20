"""Text Cipher workspace with live DenCode-style transformations."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laitoxx.features.utilities.text_cipher import _transform
from laitoxx.features.utilities.text_cipher_engine import SPECS
from laitoxx.features.utilities.text_cipher_engine.registry import SPEC_BY_ID
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme

PARAMETERS = {
    "encoding": ("Character encoding", "utf-8"),
    "separator": ("Byte separator", " "),
    "space": ("URL spaces", "%20"),
    "line_break": ("Line width (0 = off)", "0"),
    "quote": ("Quote character", '"'),
    "source_radix": ("Source radix", "10"),
    "radix": ("Target radix", "36"),
    "shift": ("Shift", "3"),
    "a": ("Affine A", "5"),
    "b": ("Affine B", "8"),
    "key": ("Key (A-Z)", "SECRET"),
    "symbols": ("Two symbols", "AB"),
    "columns": ("Columns", "3"),
    "rails": ("Rails", "3"),
    "style": ("Unicode style", "bold"),
    "rotors": ("Rotors", "I II III"),
    "rings": ("Ring settings", "AAA"),
    "positions": ("Start positions", "AAA"),
    "reflector": ("Reflector", "B"),
    "plugboard": ("Plugboard pairs", ""),
    "script": ("Output script", "romaji"),
    "mode": ("Mode", "strict"),
    "hash_function": ("SHA-3 function", "sha3_256"),
}
INTEGER_PARAMETERS = {"line_break", "source_radix", "radix", "shift", "a", "b", "columns", "rails"}
INTEGER_RANGES = {
    "line_break": (0, 512),
    "source_radix": (2, 36),
    "radix": (2, 36),
    "shift": (-25, 25),
    "a": (1, 25),
    "b": (0, 25),
    "columns": (1, 10_000),
    "rails": (2, 1_000),
}
CHOICE_PARAMETERS = {
    "encoding": ("utf-8", "utf-16", "utf-32", "latin-1"),
    "space": ("%20", "+"),
    "quote": ('"', "'", "`"),
    "a": ("1", "3", "5", "7", "9", "11", "15", "17", "19", "21", "23", "25"),
    "style": (
        "bold",
        "italic",
        "bold_italic",
        "script",
        "script_bold",
        "sans",
        "sans_bold",
        "sans_italic",
        "sans_bold_italic",
        "fraktur",
        "double_struck",
        "monospace",
        "small_caps",
        "circled",
        "negative_circled",
        "squared",
        "negative_squared",
    ),
    "reflector": ("B", "C"),
    "script": ("romaji", "hiragana", "katakana"),
    "mode": ("strict", "lenient"),
    "hash_function": ("sha3_224", "sha3_256", "sha3_384", "sha3_512"),
}


class TextCipherDialog(QDialog):
    def __init__(self, parent=None, tool_name="Text Cipher"):
        super().__init__(parent)
        self.setWindowTitle("Text Cipher")
        self.setObjectName("TextCipherDialog")
        self.setMinimumSize(920, 660)
        self.resize(1120, 760)
        self._parameter_rows: dict[str, tuple[QLabel, QWidget]] = {}
        self._last_valid_result = ""
        self._theme = resolved_theme(getattr(parent, "theme_data", None))

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self._update_preview)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_controls())
        splitter.addWidget(self._build_workspace())
        splitter.setSizes([300, 800])
        root.addWidget(splitter, 1)
        root.addLayout(self._build_footer())

        self.setStyleSheet(build_workspace_qss(self._theme) + self._local_style())
        self._populate_modes(self.category_combo.currentText())
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._accept_if_valid)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._focus_source)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.search_input.setFocus)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("PageHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 13, 14, 13)
        titles = QVBoxLayout()
        title = QLabel("Text Cipher")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Encode, decode and inspect text locally across 86 transformations")
        subtitle.setObjectName("PageSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        layout.addLayout(titles, 1)
        badge = QLabel("LOCAL  •  LIVE")
        badge.setObjectName("CipherBadge")
        layout.addWidget(badge)
        return header

    def _build_controls(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ToolPanel")
        panel.setMinimumWidth(270)
        panel.setMaximumWidth(370)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        section = QLabel("TRANSFORMATION")
        section.setObjectName("SectionLabel")
        layout.addWidget(section)

        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText("Search 86 transformations…  Ctrl+F")
        self.search_input.textChanged.connect(self._filter_modes)
        layout.addWidget(self.search_input)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All results", *dict.fromkeys(spec.category for spec in SPECS)])
        self.category_combo.currentTextChanged.connect(self._populate_modes)
        layout.addWidget(self.category_combo)

        self.mode_combo = QComboBox()
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        layout.addWidget(self.mode_combo)

        direction_row = QHBoxLayout()
        self._action_label = QLabel("Direction")
        self.action_combo = QComboBox()
        self.action_combo.addItem("Encode", "encode")
        self.action_combo.addItem("Decode", "decode")
        self.action_combo.currentIndexChanged.connect(self._schedule_preview)
        direction_row.addWidget(self._action_label)
        direction_row.addWidget(self.action_combo, 1)
        layout.addLayout(direction_row)

        self.parameter_panel = QFrame()
        self.parameter_panel.setObjectName("WorkSurface")
        parameter_layout = QFormLayout(self.parameter_panel)
        parameter_layout.setContentsMargins(10, 10, 10, 10)
        parameter_layout.setSpacing(7)
        for name, (label_text, default) in PARAMETERS.items():
            label = QLabel(label_text)
            if name in CHOICE_PARAMETERS:
                field = QComboBox()
                field.addItems(CHOICE_PARAMETERS[name])
                field.setCurrentText(default)
                field.currentTextChanged.connect(self._schedule_preview)
            elif name in INTEGER_PARAMETERS:
                field = QSpinBox()
                field.setRange(*INTEGER_RANGES[name])
                field.setValue(int(default))
                field.valueChanged.connect(self._schedule_preview)
            else:
                field = QLineEdit(default)
                field.textChanged.connect(self._schedule_preview)
            field.setObjectName("ParameterInput")
            parameter_layout.addRow(label, field)
            self._parameter_rows[name] = (label, field)
        layout.addWidget(self.parameter_panel)

        self.mode_hint = QLabel()
        self.mode_hint.setObjectName("Muted")
        self.mode_hint.setWordWrap(True)
        layout.addWidget(self.mode_hint)
        layout.addStretch()

        self.swap_button = QPushButton("⇄  Swap and reverse direction")
        self.swap_button.clicked.connect(self._swap_direction)
        layout.addWidget(self.swap_button)
        return panel

    def _build_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        editors = QSplitter(Qt.Orientation.Vertical)
        editors.setChildrenCollapsible(False)
        editors.addWidget(self._build_editor_card(source=True))
        editors.addWidget(self._build_editor_card(source=False))
        editors.setSizes([310, 310])
        layout.addWidget(editors, 1)

        self.status_label = QLabel("Ready - type or paste text to begin")
        self.status_label.setObjectName("CipherStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        return workspace

    def _build_editor_card(self, *, source: bool) -> QFrame:
        card = QFrame()
        card.setObjectName("WorkSurface")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 12)
        header = QHBoxLayout()
        title = QLabel("SOURCE" if source else "RESULT")
        title.setObjectName("SectionLabel")
        header.addWidget(title)
        header.addStretch()
        counter = QLabel("0 chars  •  0 bytes")
        counter.setObjectName("Muted")
        header.addWidget(counter)
        if source:
            paste = QPushButton("Paste")
            paste.setProperty("variant", "ghost")
            paste.clicked.connect(self._paste_source)
            clear = QPushButton("Clear")
            clear.setProperty("variant", "ghost")
            clear.clicked.connect(self._clear_source)
            header.addWidget(paste)
            header.addWidget(clear)
        else:
            copy = QPushButton("Copy")
            copy.setProperty("variant", "primary")
            copy.clicked.connect(self._copy_result)
            header.addWidget(copy)
        layout.addLayout(header)
        editor = QTextEdit()
        editor.setObjectName("CipherEditor")
        editor.setAcceptRichText(False)
        if source:
            self.source_counter = counter
            self.text_input = editor
            editor.setPlaceholderText("Type or paste text here…  Ctrl+L")
            editor.textChanged.connect(self._source_changed)
        else:
            self.result_counter = counter
            self.preview = editor
            editor.setReadOnly(True)
            editor.setPlaceholderText("The transformed result appears here automatically")
        layout.addWidget(editor, 1)
        return card

    def _build_footer(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        hint = QLabel("Ctrl+Enter  send result to workspace")
        hint.setObjectName("Muted")
        layout.addWidget(hint)
        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.accept_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.accept_button.setText("Send to workspace")
        self.accept_button.setProperty("variant", "primary")
        self.accept_button.setEnabled(False)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        return layout

    def _populate_modes(self, category: str) -> None:
        if self.search_input.text().strip():
            self._filter_modes(self.search_input.text())
            return
        previous = self.mode_combo.currentData()
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        if category == "All results":
            self.mode_combo.addItem("All compatible transformations", "all")
        else:
            for spec in SPECS:
                if spec.category == category:
                    self.mode_combo.addItem(spec.label, spec.identifier)
        index = self.mode_combo.findData(previous)
        self.mode_combo.setCurrentIndex(index if index >= 0 else 0)
        self.mode_combo.blockSignals(False)
        self._mode_changed()

    def _filter_modes(self, query: str) -> None:
        query = query.strip().casefold()
        if not query:
            self.category_combo.setEnabled(True)
            self._populate_modes(self.category_combo.currentText())
            return
        previous = self.mode_combo.currentData()
        self.category_combo.setEnabled(False)
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        for spec in SPECS:
            haystack = f"{spec.label} {spec.category} {spec.identifier}".casefold()
            if query in haystack:
                self.mode_combo.addItem(f"{spec.label}  ·  {spec.category}", spec.identifier)
        index = self.mode_combo.findData(previous)
        self.mode_combo.setCurrentIndex(index if index >= 0 else 0)
        self.mode_combo.blockSignals(False)
        self._mode_changed()

    def _mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        spec = SPEC_BY_ID.get(mode)
        reversible = bool(spec and spec.reversible)
        self._action_label.setVisible(reversible)
        self.action_combo.setVisible(reversible)
        self.swap_button.setEnabled(reversible)
        visible = set(spec.parameters if spec else ())
        for name, (label, field) in self._parameter_rows.items():
            label.setVisible(name in visible)
            field.setVisible(name in visible)
        self.parameter_panel.setVisible(bool(visible))
        if mode == "all":
            self.mode_hint.setText("Overview mode tries every compatible decoder and encoder with safe defaults.")
        elif spec:
            direction = "Encode and decode are available." if reversible else "This transformation is one-way."
            self.mode_hint.setText(f"{spec.category}  •  {direction}")
        else:
            self.mode_hint.setText("No transformations match your search.")
        self._schedule_preview()

    def _options(self) -> dict:
        spec = SPEC_BY_ID.get(self.mode_combo.currentData())
        result = {}
        for name in spec.parameters if spec else ():
            field = self._parameter_rows[name][1]
            if isinstance(field, QSpinBox):
                value = field.value()
            elif isinstance(field, QComboBox):
                value = field.currentText()
            else:
                value = field.text()
            result[name] = value
        return result

    def _source_changed(self) -> None:
        self._update_counter(self.source_counter, self.text_input.toPlainText())
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        self._preview_timer.start()

    def _update_preview(self) -> None:
        mode = self.mode_combo.currentData()
        source = self.text_input.toPlainText()
        if not mode or not source:
            self.preview.clear()
            self._last_valid_result = ""
            self.accept_button.setEnabled(False)
            self.status_label.setText("Ready - type or paste text to begin")
            self.status_label.setProperty("state", "idle")
            self._refresh_status_style()
            self._update_counter(self.result_counter, "")
            return
        result = _transform(mode, self.action_combo.currentData() or "encode", source, **self._options())
        self.preview.setPlainText(result)
        self._update_counter(self.result_counter, result)
        is_error = result.startswith("[error:") or result.startswith("[unknown mode:")
        self._last_valid_result = "" if is_error else result
        self.accept_button.setEnabled(not is_error)
        if is_error:
            self.status_label.setText(result.removeprefix("[").removesuffix("]"))
            self.status_label.setProperty("state", "error")
        else:
            label = self.mode_combo.currentText().split("  ·  ", 1)[0]
            self.status_label.setText(f"✓  {label} completed locally")
            self.status_label.setProperty("state", "success")
        self._refresh_status_style()

    @staticmethod
    def _update_counter(label: QLabel, text: str) -> None:
        label.setText(f"{len(text):,} chars  •  {len(text.encode('utf-8')):,} bytes")

    def _swap_direction(self) -> None:
        if not self._last_valid_result or not self.swap_button.isEnabled():
            return
        self.text_input.setPlainText(self._last_valid_result)
        self.action_combo.setCurrentIndex(1 - self.action_combo.currentIndex())
        self.text_input.setFocus()

    def _paste_source(self) -> None:
        self.text_input.setPlainText(QGuiApplication.clipboard().text())
        self.text_input.setFocus()

    def _clear_source(self) -> None:
        self.text_input.clear()
        self.text_input.setFocus()

    def _copy_result(self) -> None:
        if self.preview.toPlainText():
            QGuiApplication.clipboard().setText(self.preview.toPlainText())
            self.status_label.setText("✓  Result copied to clipboard")

    def _focus_source(self) -> None:
        self.text_input.setFocus()
        self.text_input.selectAll()

    def _accept_if_valid(self) -> None:
        if self.text_input.toPlainText() and self._last_valid_result:
            self.accept()

    def _refresh_status_style(self) -> None:
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def get_values(self):
        text = self.text_input.toPlainText()
        if not text:
            return None
        return {
            "mode": self.mode_combo.currentData(),
            "action": self.action_combo.currentData(),
            "text": text,
            "options": self._options(),
        }

    def _local_style(self) -> str:
        theme = self._theme
        code_font = theme.get("code_font_family") or "Cascadia Mono"
        return f"""
        QDialog#TextCipherDialog {{ background: {theme["surface_base_color"]}; }}
        QLabel#CipherBadge {{
            color: {theme["accent_color"]}; background: {theme["accent_soft_color"]};
            border: 1px solid {theme["accent_dim_color"]}; border-radius: 10px;
            padding: 6px 10px; font-size: 10px; font-weight: 700;
        }}
        QTextEdit#CipherEditor {{ font-family: "{code_font}", Consolas, monospace; font-size: 13px; }}
        QLabel#CipherStatus {{
            background: {theme["surface_input_color"]}; border: 1px solid {theme["border_subtle_color"]};
            border-radius: 8px; padding: 8px 12px; color: {theme["text_secondary_color"]};
        }}
        QLabel#CipherStatus[state="success"] {{ color: {theme["success_color"]}; border-color: {theme["success_color"]}; }}
        QLabel#CipherStatus[state="error"] {{ color: {theme["danger_color"]}; border-color: {theme["danger_color"]}; }}
        """
