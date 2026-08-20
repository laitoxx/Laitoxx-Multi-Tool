"""Focused behavior slice for CogniPassWindow."""
# ruff: noqa: F405

from .cognipass_window_context import *  # noqa: F403


class CogniPassWindowMixin1:
    @staticmethod
    def _line(placeholder: str = "") -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        return field

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel(_t("cognipass_title", "Targeted password generator"))
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            _t(
                "cognipass_subtitle",
                "Generate audit candidates from known personal context with CogniPass",
            )
        )
        subtitle.setObjectName("PageSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        root.addLayout(titles)

        notice = QLabel(
            _t(
                "cognipass_notice",
                "Use only for authorized password audits. Processing is local; personal data is not sent to a service.",
            )
        )
        notice.setObjectName("Muted")
        notice.setWordWrap(True)
        root.addWidget(notice)

        root.addWidget(self._build_profile_panel(), 1)

        self.status = QLabel(_t("cognipass_ready", "Ready to generate candidates"))
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        root.addWidget(self.progress)

        action_row = QHBoxLayout()
        self.generate_button = QPushButton(_t("cognipass_generate", "Generate"))
        self.generate_button.setProperty("variant", "primary")
        self.generate_button.clicked.connect(self._start)
        self.cancel_button = QPushButton(_t("cognipass_cancel", "Stop"))
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        self.open_folder_button = QPushButton(_t("cognipass_open_folder", "Open folder"))
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self._open_folder)
        action_row.addStretch()
        action_row.addWidget(self.open_folder_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.generate_button)
        root.addLayout(action_row)

    def _build_profile_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(8)

        person = QGroupBox(_t("cognipass_target", "Target profile"))
        form = QFormLayout(person)
        self.first_name = self._line("Michael")
        self.last_name = self._line("Garcia")
        self.middle_name = self._line()
        self.birth_date = self._line("DD.MM.YYYY")
        self.pet = self._line()
        self.team = self._line()
        form.addRow(_t("cognipass_first", "First name"), self.first_name)
        form.addRow(_t("cognipass_last", "Last name"), self.last_name)
        form.addRow(_t("cognipass_middle", "Middle name"), self.middle_name)
        form.addRow(_t("cognipass_birth", "Birth date"), self.birth_date)
        form.addRow(_t("cognipass_pet", "Pet"), self.pet)
        form.addRow(_t("cognipass_team", "Favorite team"), self.team)
        layout.addWidget(person)

        self.additional_toggle = QPushButton("› " + _t("cognipass_additional", "Additional family details"))
        self.additional_toggle.setObjectName("AdditionalToggle")
        self.additional_toggle.setCheckable(True)
        self.additional_toggle.setChecked(False)
        self.additional_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.additional_toggle.toggled.connect(self._toggle_additional)
        layout.addWidget(self.additional_toggle)

        self.additional_panel = QFrame()
        self.additional_panel.setObjectName("PanelSurface")
        additional_layout = QVBoxLayout(self.additional_panel)
        additional_layout.setContentsMargins(10, 8, 10, 10)
        additional_layout.setSpacing(8)

        self.spouse_group = QGroupBox(_t("cognipass_spouse", "Spouse"))
        self.spouse_group.setCheckable(True)
        self.spouse_group.setChecked(False)
        spouse_form = QFormLayout(self.spouse_group)
        self.spouse_first = self._line()
        self.spouse_last = self._line()
        self.spouse_birth = self._line("DD.MM.YYYY")
        spouse_form.addRow(_t("cognipass_first", "First name"), self.spouse_first)
        spouse_form.addRow(_t("cognipass_last", "Last name"), self.spouse_last)
        spouse_form.addRow(_t("cognipass_birth", "Birth date"), self.spouse_birth)
        additional_layout.addWidget(self.spouse_group)

        children_group = QGroupBox(_t("cognipass_children", "Children"))
        children_layout = QVBoxLayout(children_group)
        self.children = QTableWidget(0, 2)
        self.children.setHorizontalHeaderLabels(
            [
                _t("cognipass_first", "First name"),
                _t("cognipass_birth", "Birth date"),
            ]
        )
        self.children.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.children.setFixedHeight(132)
        children_layout.addWidget(self.children)
        child_actions = QHBoxLayout()
        add_child = QPushButton(_t("cognipass_add_child", "Add child"))
        add_child.clicked.connect(self._add_child)
        remove_child = QPushButton(_t("cognipass_remove_child", "Remove selected"))
        remove_child.clicked.connect(self._remove_child)
        child_actions.addWidget(add_child)
        child_actions.addWidget(remove_child)
        child_actions.addStretch()
        children_layout.addLayout(child_actions)
        additional_layout.addWidget(children_group)
        self.additional_panel.setVisible(False)
        layout.addWidget(self.additional_panel)

        parameters = QGroupBox(_t("cognipass_parameters", "Generation parameters"))
        parameter_form = QFormLayout(parameters)
        self.pin_only = QCheckBox(_t("cognipass_pin", "PIN candidates only"))
        self.pin_only.toggled.connect(self._pin_mode_changed)
        self.minimum_length = QSpinBox()
        self.minimum_length.setRange(1, 128)
        self.minimum_length.setValue(8)
        self.maximum_length = QSpinBox()
        self.maximum_length.setRange(1, 128)
        self.maximum_length.setValue(32)
        self.count = QSpinBox()
        self.count.setRange(0, 10_000_000)
        self.count.setSingleStep(1000)
        self.count.setValue(10_000)
        self.count.setSpecialValueText(_t("cognipass_all", "All deterministic"))
        parameter_form.addRow(self.pin_only)
        parameter_form.addRow(_t("cognipass_min_length", "Minimum length"), self.minimum_length)
        parameter_form.addRow(_t("cognipass_max_length", "Maximum length"), self.maximum_length)
        parameter_form.addRow(_t("cognipass_count", "Candidate count"), self.count)
        layout.addWidget(parameters)

        output = QGroupBox(_t("cognipass_output", "Dictionary output"))
        output_layout = QHBoxLayout(output)
        self.output_path = self._line()
        default_folder = Path.home() / "Documents"
        if not default_folder.exists():
            default_folder = Path.home()
        self.output_path.setText(str(default_folder / "cognipass.txt"))
        output_layout.addWidget(self.output_path, 1)
        browse = QPushButton(_t("cognipass_browse", "Browse"))
        browse.clicked.connect(self._browse_output)
        output_layout.addWidget(browse)
        layout.addWidget(output)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _toggle_additional(self, expanded: bool) -> None:
        self.additional_panel.setVisible(expanded)
        arrow = "⌄" if expanded else "›"
        self.additional_toggle.setText(f"{arrow} " + _t("cognipass_additional", "Additional family details"))

    def _add_child(self) -> None:
        row = self.children.rowCount()
        self.children.insertRow(row)
        self.children.setItem(row, 0, QTableWidgetItem(""))
        self.children.setItem(row, 1, QTableWidgetItem(""))
        self.children.setCurrentCell(row, 0)
        self.children.editItem(self.children.item(row, 0))

    def _remove_child(self) -> None:
        rows = sorted({index.row() for index in self.children.selectedIndexes()}, reverse=True)
        for row in rows:
            self.children.removeRow(row)

    def _pin_mode_changed(self, enabled: bool) -> None:
        if enabled:
            self.minimum_length.setValue(4)
            self.maximum_length.setValue(8)
        elif self.maximum_length.value() <= 8:
            self.minimum_length.setValue(8)
            self.maximum_length.setValue(32)

    def _browse_output(self) -> None:
        path, _filter = QFileDialog.getSaveFileName(
            self,
            _t("cognipass_output", "Dictionary output"),
            self.output_path.text(),
            "Text dictionary (*.txt);;All files (*)",
        )
        if path:
            self.output_path.setText(path)

    def _profile(self) -> CogniPassProfile:
        children = []
        for row in range(self.children.rowCount()):
            name_item = self.children.item(row, 0)
            date_item = self.children.item(row, 1)
            name = name_item.text().strip() if name_item else ""
            date = date_item.text().strip() if date_item else ""
            if name or date:
                children.append(ChildProfile(name, date))
        spouse_enabled = self.spouse_group.isChecked()
        return CogniPassProfile(
            first_name=self.first_name.text(),
            last_name=self.last_name.text(),
            middle_name=self.middle_name.text(),
            birth_date=self.birth_date.text(),
            pet=self.pet.text(),
            team=self.team.text(),
            spouse_first_name=self.spouse_first.text() if spouse_enabled else "",
            spouse_last_name=self.spouse_last.text() if spouse_enabled else "",
            spouse_birth_date=self.spouse_birth.text() if spouse_enabled else "",
            children=children,
            pin_only=self.pin_only.isChecked(),
            minimum_length=self.minimum_length.value(),
            maximum_length=self.maximum_length.value(),
            count=self.count.value(),
            output_path=Path(self.output_path.text().strip()),
        )
