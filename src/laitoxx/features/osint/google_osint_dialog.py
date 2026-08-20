import webbrowser
from urllib.parse import quote_plus

IS_GUI = False
try:
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLineEdit,
        QScrollArea,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    IS_GUI = True
except ImportError:
    pass

if IS_GUI:
    from .google_dialog_examples import GoogleDialogExamplesMixin

    class GoogleOsintDialog(GoogleDialogExamplesMixin, QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Google OSINT Dork Builder")
            self.setMinimumSize(800, 600)
            self.selected_engines = ["google"]

            self.operators = {
                "site": "Search within a specific site/domain (e.g., site:example.com). Syntax: site:domain.com",
                "inurl": "Search for URLs containing specific words (e.g., inurl:admin). Syntax: inurl:word",
                "intext": "Search for pages containing specific text (e.g., intext:password). Syntax: intext:word",
                "intitle": "Search for pages with specific words in title (e.g., intitle:login). Syntax: intitle:word",
                "filetype": "Search for specific file types (pdf, doc, xls, etc.). Syntax: filetype:extension",
                "ext": "Search for files with specific extensions (e.g., ext:sql). Syntax: ext:extension",
                "AROUND": "Find documents where words are within N words of each other. Syntax: 'word1' AROUND(n) 'word2'",
                "NEAR": "Similar to AROUND, used in Bing/SQL/Elasticsearch. Syntax: 'word1' NEAR/n 'word2'",
                "BEFORE": "Find documents where first word appears before second. Syntax: 'word1' BEFORE 'word2'",
                "AND": "Both words must be present (default behavior). Syntax: word1 AND word2",
                "OR": "At least one word must be present. Syntax: word1 OR word2",
                "NOT": "Exclude words from results. Syntax: word1 -word2 or word1 NOT word2",
                "exact_phrase": "Search for exact phrase match. Syntax: 'exact phrase here'",
                "grouping": "Group logical conditions. Syntax: (condition1 OR condition2) AND condition3",
                "inanchor": "Search for pages linked with specific anchor text. Syntax: inanchor:'click here'",
                "allinurl": "All specified words must be in URL. Syntax: allinurl:word1 word2",
                "allintitle": "All specified words must be in title. Syntax: allintitle:word1 word2",
                "allintext": "All specified words must be in text. Syntax: allintext:word1 word2",
                "cache": "View Google's cached version of a page. Syntax: cache:example.com",
                "related": "Find pages related to a URL. Syntax: related:example.com",
                "info": "Get information about a URL. Syntax: info:example.com",
                "link": "Find pages that link to a specific URL. Syntax: link:example.com",
                "after": "Search for content after specific date. Syntax: after:YYYY or after:YYYY-MM-DD",
                "before": "Search for content before specific date. Syntax: before:YYYY or before:YYYY-MM-DD",
                "daterange": "Search within date range. Syntax: daterange:startdate..enddate",
                "numrange": "Search within a range of numbers. Syntax: numrange:1-100",
                "wildcard_*": "Replace any number of words. Syntax: 'best * ever'",
                "wildcard__": "Replace exactly one word. Syntax: 'best _ in the world'",
                "define": "Get definitions of words. Syntax: define:word",
                "source": "Search news from specific source. Syntax: source:newsoutlet",
                "phonebook": "Search Google phonebook. Syntax: phonebook:John Doe location",
                "maps": "Search Google Maps. Syntax: maps:query",
                "book": "Search Google Books. Syntax: book:title or author",
                "finance": "Search Google Finance. Syntax: finance:stock_symbol",
                "movie": "Search for movie information. Syntax: movie:title",
                "weather": "Search weather information. Syntax: weather:location",
                "stocks": "Search stock information. Syntax: stocks:symbol",
                "location": "Search for location information. Syntax: location:query",
                "feed": "Search for RSS/Atom feeds. Syntax: feed:site.com",
                "group": "Search Google Groups. Syntax: group:query",
                "index_of": "Find open directories. Syntax: intitle:'index of' 'parent directory'",
                "phpinfo": "Find phpinfo.php pages. Syntax: inurl:'/phpinfo.php'",
                "exposed_files": "Find exposed database/config files. Syntax: ext:(sql|db|bak|conf) intext:password",
            }

            self.layout = QVBoxLayout(self)

            engines_group = QGroupBox("Search Engines")
            engines_layout = QHBoxLayout(engines_group)

            self.engine_checkboxes = {}
            engines = ["Google", "Bing", "DuckDuckGo", "Yandex"]
            for engine in engines:
                cb = QCheckBox(engine)
                cb.setChecked(engine == "Google")
                cb.stateChanged.connect(self.update_selected_engines)
                engines_layout.addWidget(cb)
                self.engine_checkboxes[engine.lower()] = cb

            self.layout.addWidget(engines_group)

            preset_group = QGroupBox("OSINT Search Templates")
            preset_layout = QHBoxLayout(preset_group)
            self.preset_combo = QComboBox()
            self.preset_combo.addItems(
                [
                    "Custom",
                    "Username footprint",
                    "Email mentions",
                    "Domain documents",
                    "Public configuration exposure",
                    "Person documents",
                    "Recent mentions",
                ]
            )
            self.preset_combo.currentTextChanged.connect(self.apply_preset)
            preset_layout.addWidget(self.preset_combo)
            self.layout.addWidget(preset_group)

            operators_group = QGroupBox("Dork Operators")
            operators_layout = QVBoxLayout(operators_group)

            scroll_area = QScrollArea()
            scroll_widget = QWidget()
            self.grid_layout = QGridLayout(scroll_widget)

            self.operator_checkboxes = {}
            self.operator_inputs = {}

            row, col = 0, 0
            for op_name, description in self.operators.items():
                # Checkbox
                cb = QCheckBox(op_name)
                cb.setToolTip(description)
                cb.stateChanged.connect(self.toggle_operator_input)
                self.grid_layout.addWidget(cb, row, col)
                self.operator_checkboxes[op_name] = cb

                # Input field (initially hidden)
                input_field = QLineEdit()
                input_field.setPlaceholderText(f"Enter value for {op_name}")
                input_field.setVisible(False)
                self.grid_layout.addWidget(input_field, row, col + 1)
                self.operator_inputs[op_name] = input_field

                col += 2
                if col >= 6:  # 3 columns of operator + input
                    col = 0
                    row += 1

            scroll_area.setWidget(scroll_widget)
            scroll_area.setWidgetResizable(True)
            operators_layout.addWidget(scroll_area)
            self.layout.addWidget(operators_group)

            query_group = QGroupBox("Search Query")
            query_layout = QVBoxLayout(query_group)
            self.base_query_input = QLineEdit()
            self.base_query_input.setPlaceholderText("Enter base search terms (optional)")
            query_layout.addWidget(self.base_query_input)
            self.layout.addWidget(query_group)

            preview_group = QGroupBox("Generated Query Preview")
            preview_layout = QVBoxLayout(preview_group)
            self.query_preview = QTextEdit()
            self.query_preview.setMaximumHeight(60)
            self.query_preview.setReadOnly(True)
            preview_layout.addWidget(self.query_preview)
            self.layout.addWidget(preview_group)

            button_box = QDialogButtonBox()
            self.search_button = button_box.addButton("Search", QDialogButtonBox.ButtonRole.AcceptRole)
            self.examples_button = button_box.addButton("Show Examples", QDialogButtonBox.ButtonRole.ActionRole)
            self.copy_button = button_box.addButton("Copy Query", QDialogButtonBox.ButtonRole.ActionRole)
            self.clear_button = button_box.addButton("Clear", QDialogButtonBox.ButtonRole.ResetRole)
            self.close_button = button_box.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)

            self.search_button.clicked.connect(self.perform_search)
            self.examples_button.clicked.connect(self.show_examples)
            self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.query_preview.toPlainText()))
            self.clear_button.clicked.connect(self.clear_all)
            self.close_button.clicked.connect(self.reject)

            self.layout.addWidget(button_box)

            self.base_query_input.textChanged.connect(self.update_preview)
            for cb in self.operator_checkboxes.values():
                cb.stateChanged.connect(self.update_preview)
            for input_field in self.operator_inputs.values():
                input_field.textChanged.connect(self.update_preview)

        def update_selected_engines(self):
            self.selected_engines = [engine for engine, cb in self.engine_checkboxes.items() if cb.isChecked()]
            if not self.selected_engines:
                self.selected_engines = ["google"]  # Ensure at least one engine

        def toggle_operator_input(self):
            sender = self.sender()
            if sender in self.operator_checkboxes.values():
                op_name = [name for name, cb in self.operator_checkboxes.items() if cb == sender][0]
                self.operator_inputs[op_name].setVisible(sender.isChecked())

        def update_preview(self):
            query_parts = []

            base_query = self.base_query_input.text().strip()
            if base_query:
                query_parts.append(base_query)

            for op_name, cb in self.operator_checkboxes.items():
                if cb.isChecked():
                    value = self.operator_inputs[op_name].text().strip()
                    if value:
                        query_parts.append(self._format_operator(op_name, value))

            final_query = " ".join(query_parts)
            self.query_preview.setText(final_query)

        @staticmethod
        def _format_operator(name, value):
            if name == "exact_phrase":
                return f'"{value}"'
            if name == "index_of":
                return f'intitle:"index of" "{value}"'
            if name == "phpinfo":
                return 'inurl:"/phpinfo.php"'
            if name == "exposed_files":
                return f'ext:(sql|db|bak|conf|env) intext:"{value}"'
            if name in {"AND", "OR", "NOT", "AROUND", "NEAR", "BEFORE"}:
                return value
            if name in {"grouping", "wildcard_*", "wildcard__", "daterange", "numrange"}:
                return value
            return f"{name}:{value}"

        def apply_preset(self, name):
            if name == "Custom":
                return
            for checkbox in self.operator_checkboxes.values():
                checkbox.setChecked(False)
            presets = {
                "Username footprint": [
                    ("exact_phrase", "@username"),
                    ("OR", "site:github.com OR site:reddit.com OR site:x.com"),
                ],
                "Email mentions": [("exact_phrase", "user@example.com"), ("NOT", "-site:example.com")],
                "Domain documents": [("site", "example.com"), ("filetype", "pdf")],
                "Public configuration exposure": [("site", "example.com"), ("exposed_files", "password")],
                "Person documents": [("exact_phrase", "First Last"), ("filetype", "pdf")],
                "Recent mentions": [("exact_phrase", "search phrase"), ("after", "2025-01-01")],
            }
            for operator, value in presets.get(name, []):
                checkbox = self.operator_checkboxes.get(operator)
                if checkbox:
                    checkbox.setChecked(True)
                    self.operator_inputs[operator].setText(value)

        def perform_search(self):
            query = self.query_preview.toPlainText().strip()
            if not query:
                return

            for engine in self.selected_engines:
                if engine == "google":
                    url = f"https://www.google.com/search?q={quote_plus(query)}"
                elif engine == "bing":
                    url = f"https://www.bing.com/search?q={quote_plus(query)}"
                elif engine == "duckduckgo":
                    url = f"https://duckduckgo.com/?q={quote_plus(query)}"
                elif engine == "yandex":
                    url = f"https://yandex.ru/search/?text={quote_plus(query)}"

                try:
                    webbrowser.open(url)
                except Exception as e:
                    print(f"Could not open {engine}: {e}")

            self.accept()

        def clear_all(self):
            self.base_query_input.clear()
            for cb in self.operator_checkboxes.values():
                cb.setChecked(False)
            for input_field in self.operator_inputs.values():
                input_field.clear()
                input_field.setVisible(False)
            self.query_preview.clear()
