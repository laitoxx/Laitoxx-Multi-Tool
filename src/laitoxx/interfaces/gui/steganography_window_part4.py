"""Method-specific controls for SteganographyWindow."""
# ruff: noqa: F405

from .steganography_window_context import *  # noqa: F403


class SteganographyWindowMixin4:
    def _add_control(self, grid, row, label, widget):
        caption = QLabel(translator.get(label))
        caption.setObjectName("Muted")
        grid.addWidget(caption, row, 0)
        grid.addWidget(widget, row, 1)
        self._method_control_rows.append((caption, widget))

    def _build_method_controls(self, grid):
        self._method_control_rows = []
        self.method_combo = QComboBox()
        for method_id, label in method_choices():
            self.method_combo.addItem(label, method_id)
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        self._add_control(grid, 1, "Method:", self.method_combo)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["interleaved", "sequential", "spread"])
        self.strategy_combo.currentIndexChanged.connect(self._update_capacity)
        self._add_control(grid, 2, "Placement:", self.strategy_combo)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(list(CHANNEL_PRESETS))
        self.channel_combo.setCurrentText("RGB")
        self.channel_combo.currentIndexChanged.connect(self._update_capacity)
        self._add_control(grid, 3, "Channels:", self.channel_combo)

        self.bits_spin = QSpinBox()
        self.bits_spin.setRange(1, 8)
        self.bits_spin.setValue(1)
        self.bits_spin.valueChanged.connect(self._update_capacity)
        self._add_control(grid, 4, "Bits per channel:", self.bits_spin)

        self.robustness_combo = QComboBox()
        self.robustness_combo.addItems(["low", "medium", "high"])
        self.robustness_combo.setCurrentText("medium")
        self._add_control(grid, 5, "DCT robustness:", self.robustness_combo)

        self.pvd_direction_combo = QComboBox()
        self.pvd_direction_combo.addItems(["horizontal", "vertical", "both"])
        self._add_control(grid, 6, "PVD direction:", self.pvd_direction_combo)

        self.pvd_range_combo = QComboBox()
        self.pvd_range_combo.addItems(["wu-tsai", "wide", "narrow"])
        self._add_control(grid, 7, "PVD ranges:", self.pvd_range_combo)

        self.palette_colors_combo = QComboBox()
        for value in (256, 128, 64, 32):
            self.palette_colors_combo.addItem(str(value), value)
        self._add_control(grid, 8, "Palette colors:", self.palette_colors_combo)

        self.png_keyword_input = QLineEdit("stEg")
        self._add_control(grid, 9, "PNG keyword:", self.png_keyword_input)

        self.compression_check = QCheckBox(translator.get("Compress payload"))
        self.compression_check.setChecked(True)
        self.compression_check.toggled.connect(self._update_capacity)
        grid.addWidget(self.compression_check, 10, 1)

    def _method_id(self):
        return self.method_combo.currentData() or "LSB"

    def _populate_methods(self):
        current = self._method_id()
        extraction = self.mode_combo.currentIndex() == 1
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        for method_id, label in method_choices():
            self.method_combo.addItem(label, method_id)
        if extraction:
            self.method_combo.addItem(translator.get("Try all applicable methods"), AUTO_METHOD_ID)
        index = self.method_combo.findData(current)
        self.method_combo.setCurrentIndex(max(0, index))
        self.method_combo.blockSignals(False)
        self._on_method_changed()

    def _update_method_control_visibility(self):
        method = self._method_id()
        visible = {
            self.strategy_combo: method == "LSB",
            self.channel_combo: method in {"LSB", "SPREAD"},
            self.bits_spin: method in {"LSB", "SPREAD"},
            self.robustness_combo: method == "DCT",
            self.pvd_direction_combo: method == "PVD",
            self.pvd_range_combo: method == "PVD",
            self.palette_colors_combo: method == "PALETTE",
            self.png_keyword_input: method == "PNGCHUNK",
        }
        for label, widget in self._method_control_rows[1:]:
            state = visible.get(widget, False)
            label.setVisible(state)
            widget.setVisible(state)
        self.compression_check.setVisible(method in {"LSB", "SPREAD"})
