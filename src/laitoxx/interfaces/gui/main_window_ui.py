"""Main window responsibility mixin."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator


class GlassButton(QPushButton):
    pass


class MainWindowUiMixin:
    def _build_ui(self):
        self.main_container = QWidget()
        self.main_container.setObjectName("WorkspaceRoot")
        self.setCentralWidget(self.main_container)

        # Background layer
        self.background_container = QStackedWidget(self.main_container)
        self.gif_label = QLabel()
        self.gif_label.setScaledContents(True)
        self.video_widget = QVideoWidget()
        self.background_container.addWidget(self.gif_label)
        self.background_container.addWidget(self.video_widget)

        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)
        self.player.setLoops(-1)
        self._apply_performance_mode()

        # UI layer
        self.ui_container = QWidget(self.main_container)
        self.ui_container.setStyleSheet("background:transparent;")

        self._build_topbar()
        self._build_sidebar()
        self._build_main_content()
        self._build_active_tools_panel()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar_widget)
        self.splitter.addWidget(self._main_content_widget)
        self.splitter.addWidget(self.active_tools_widget)
        self.splitter.setSizes([210, 1050, 220])

        ui_layout = QVBoxLayout(self.ui_container)
        ui_layout.addWidget(self.topbar_widget)
        ui_layout.addWidget(self.splitter, 1)
        ui_layout.setSpacing(10)
        ui_layout.setContentsMargins(12, 12, 12, 12)

    def _build_topbar(self):
        self.topbar_widget = QWidget()
        self.topbar_widget.setObjectName("TopBar")
        layout = QHBoxLayout(self.topbar_widget)
        layout.setContentsMargins(16, 9, 12, 9)
        brand = QLabel("LAITOXX")
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        layout.addSpacing(18)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(translator.get("search"))
        self.search_bar.textChanged.connect(self._filter_tools)
        layout.addWidget(self.search_bar, 1)
        self.smart_paste_btn = QPushButton(translator.get("Smart Paste"))
        self.smart_paste_btn.setProperty("variant", "primary")
        self.smart_paste_btn.clicked.connect(self._smart_paste)
        layout.addWidget(self.smart_paste_btn)
        self.palette_btn = QPushButton("Ctrl+K")
        self.palette_btn.setProperty("variant", "ghost")
        self.palette_btn.setToolTip(translator.get("Command Palette"))
        self.palette_btn.clicked.connect(self._open_command_palette)
        layout.addWidget(self.palette_btn)

    def _build_sidebar(self):
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("Sidebar")
        self.sidebar_widget.setMinimumWidth(188)
        self.sidebar_widget.setMaximumWidth(240)
        layout = QVBoxLayout(self.sidebar_widget)
        layout.setContentsMargins(10, 14, 10, 12)
        layout.setSpacing(5)

        section = QLabel("WORKSPACE")
        section.setObjectName("SectionLabel")
        layout.addWidget(section)

        self.btn_settings = GlassButton("")
        self.btn_plugin_builder = GlassButton("")
        self.btn_graph_editor = GlassButton("")
        self.btn_create_theme = GlassButton("")

        from PyQt6.QtWidgets import QComboBox

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["English", "Русский", "Українська", "Türkçe"])
        # Set current index based on translator.lang
        lang_map = {"en": 0, "ru": 1, "uk": 2, "tr": 3}
        self.combo_lang.setCurrentIndex(lang_map.get(translator.lang, 0))
        self.combo_lang.setStyleSheet("padding: 5px; border-radius: 5px;")

        self.btn_hide_ui = GlassButton("")
        self.btn_exit = GlassButton("")

        for btn in (self.btn_settings, self.btn_plugin_builder, self.btn_graph_editor, self.btn_create_theme):
            btn.setProperty("nav", True)
            layout.addWidget(btn)
        layout.addWidget(self.btn_hide_ui)
        layout.addWidget(self.combo_lang)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addWidget(self.btn_exit)

        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_plugin_builder.clicked.connect(self._open_plugin_builder)
        self.btn_graph_editor.clicked.connect(self._open_graph_editor)
        self.btn_create_theme.clicked.connect(self._create_new_theme)
        self.combo_lang.currentIndexChanged.connect(self._on_combo_lang_changed)
        self.btn_hide_ui.clicked.connect(self._toggle_ui_visibility)
        self.btn_exit.clicked.connect(self.close)

    def _build_main_content(self):
        self._main_content_widget = QWidget()
        self._main_content_widget.setObjectName("ContentSurface")
        layout = QVBoxLayout(self._main_content_widget)
        layout.setContentsMargins(18, 16, 18, 14)
        title = QLabel("Workspace")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Choose a tool or search across the complete toolkit")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.stacked_widget = QStackedWidget()
        self.output_area = QPlainTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumBlockCount(2000)

        # Output header row with pop-out button
        output_header = QHBoxLayout()
        output_header.setContentsMargins(0, 2, 0, 0)
        output_header.setSpacing(6)
        output_header.addStretch()
        self._btn_add_graph = QPushButton(translator.get("Add results to graph"))
        self._btn_add_graph.setFixedHeight(22)
        self._btn_add_graph.clicked.connect(self._add_output_to_graph)
        output_header.addWidget(self._btn_add_graph)
        self._btn_popout = QPushButton("⧉ " + translator.get("terminal"))
        self._btn_popout.setFixedHeight(22)
        self._btn_popout.setToolTip(translator.get("terminal_tooltip"))
        self._btn_popout.setCheckable(True)
        self._btn_popout.clicked.connect(self._toggle_terminal_window)
        output_header.addWidget(self._btn_popout)

        layout.addWidget(self.stacked_widget)
        layout.addLayout(output_header)
        layout.addWidget(self.output_area)
        layout.setStretch(1, 2)
        layout.setStretch(3, 1)

    def _append_output(self, text: str) -> None:
        if not text:
            return
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.output_area.setTextCursor(cursor)
        self.output_area.ensureCursorVisible()
        if self._terminal_window and self._terminal_window.isVisible():
            self._terminal_window.append_text(text)

    def _set_output(self, text: str) -> None:
        self.output_area.setPlainText(text or "")
        if self._terminal_window and self._terminal_window.isVisible():
            self._terminal_window.set_text(text or "")

    def _build_active_tools_panel(self):
        self.active_tools_widget = QWidget()
        self.active_tools_widget.setObjectName("ActivityPanel")
        self.active_tools_widget.setMinimumWidth(190)
        self.active_tools_widget.setMaximumWidth(260)
        layout = QVBoxLayout(self.active_tools_widget)
        layout.setContentsMargins(14, 14, 14, 12)
        title = QLabel("ACTIVITY")
        title.setObjectName("SectionLabel")
        layout.addWidget(title)
        self.activity_status = QLabel("●  System ready")
        self.activity_status.setObjectName("StatusDot")
        layout.addWidget(self.activity_status)
        self.activity_hint = QLabel("Running tools and background tasks will appear here.")
        self.activity_hint.setObjectName("Muted")
        self.activity_hint.setWordWrap(True)
        layout.addWidget(self.activity_hint)
        self.activity_items_layout = layout
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------
