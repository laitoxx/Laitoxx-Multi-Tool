import webbrowser
from urllib.parse import quote_plus
from ..shared_utils import Color

# Check if running in GUI mode
IS_GUI = False
try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
                                 QLineEdit, QScrollArea, QWidget, QGridLayout,
                                 QTextEdit, QGroupBox, QDialogButtonBox)
    IS_GUI = True
except ImportError:
    pass

if IS_GUI:
    class GoogleOsintDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Google OSINT Dork Builder")
            self.setMinimumSize(800, 600)
            self.selected_engines = ["google"]  # Default to Google

            # Available dork operators with detailed explanations
            self.operators = {
                # Basic operators
                "site": "Search within a specific site/domain (e.g., site:example.com). Syntax: site:domain.com",
                "inurl": "Search for URLs containing specific words (e.g., inurl:admin). Syntax: inurl:word",
                "intext": "Search for pages containing specific text (e.g., intext:password). Syntax: intext:word",
                "intitle": "Search for pages with specific words in title (e.g., intitle:login). Syntax: intitle:word",
                "filetype": "Search for specific file types (pdf, doc, xls, etc.). Syntax: filetype:extension",
                "ext": "Search for files with specific extensions (e.g., ext:sql). Syntax: ext:extension",

                # Advanced proximity operators
                "AROUND": "Find documents where words are within N words of each other. Syntax: 'word1' AROUND(n) 'word2'",
                "NEAR": "Similar to AROUND, used in Bing/SQL/Elasticsearch. Syntax: 'word1' NEAR/n 'word2'",
                "BEFORE": "Find documents where first word appears before second. Syntax: 'word1' BEFORE 'word2'",

                # Logical operators
                "AND": "Both words must be present (default behavior). Syntax: word1 AND word2",
                "OR": "At least one word must be present. Syntax: word1 OR word2",
                "NOT": "Exclude words from results. Syntax: word1 -word2 or word1 NOT word2",

                # Grouping and exact phrases
                "exact_phrase": "Search for exact phrase match. Syntax: 'exact phrase here'",
                "grouping": "Group logical conditions. Syntax: (condition1 OR condition2) AND condition3",

                # Advanced URL and content operators
                "inanchor": "Search for pages linked with specific anchor text. Syntax: inanchor:'click here'",
                "allinurl": "All specified words must be in URL. Syntax: allinurl:word1 word2",
                "allintitle": "All specified words must be in title. Syntax: allintitle:word1 word2",
                "allintext": "All specified words must be in text. Syntax: allintext:word1 word2",

                # Special Google features
                "cache": "View Google's cached version of a page. Syntax: cache:example.com",
                "related": "Find pages related to a URL. Syntax: related:example.com",
                "info": "Get information about a URL. Syntax: info:example.com",
                "link": "Find pages that link to a specific URL. Syntax: link:example.com",

                # Date and range operators
                "after": "Search for content after specific date. Syntax: after:YYYY or after:YYYY-MM-DD",
                "before": "Search for content before specific date. Syntax: before:YYYY or before:YYYY-MM-DD",
                "daterange": "Search within date range. Syntax: daterange:startdate..enddate",
                "numrange": "Search within a range of numbers. Syntax: numrange:1-100",

                # Wildcards and placeholders
                "wildcard_*": "Replace any number of words. Syntax: 'best * ever'",
                "wildcard__": "Replace exactly one word. Syntax: 'best _ in the world'",

                # Specialized searches
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

                # Security research operators
                "index_of": "Find open directories. Syntax: intitle:'index of' 'parent directory'",
                "phpinfo": "Find phpinfo.php pages. Syntax: inurl:'/phpinfo.php'",
                "exposed_files": "Find exposed database/config files. Syntax: ext:(sql|db|bak|conf) intext:password"
            }

            self.layout = QVBoxLayout(self)

            # Search engines selection
            engines_group = QGroupBox("Search Engines")
            engines_layout = QHBoxLayout(engines_group)

            self.engine_checkboxes = {}
            engines = ["Google", "Bing", "DuckDuckGo", "Yandex"]
            for engine in engines:
                cb = QCheckBox(engine)
                cb.setChecked(engine == "Google")  # Default Google selected
                cb.stateChanged.connect(self.update_selected_engines)
                engines_layout.addWidget(cb)
                self.engine_checkboxes[engine.lower()] = cb

            self.layout.addWidget(engines_group)

            # Operators section
            operators_group = QGroupBox("Dork Operators")
            operators_layout = QVBoxLayout(operators_group)

            # Create scrollable area for operators
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

            # Base query input
            query_group = QGroupBox("Search Query")
            query_layout = QVBoxLayout(query_group)
            self.base_query_input = QLineEdit()
            self.base_query_input.setPlaceholderText(
                "Enter base search terms (optional)")
            query_layout.addWidget(self.base_query_input)
            self.layout.addWidget(query_group)

            # Generated query preview
            preview_group = QGroupBox("Generated Query Preview")
            preview_layout = QVBoxLayout(preview_group)
            self.query_preview = QTextEdit()
            self.query_preview.setMaximumHeight(60)
            self.query_preview.setReadOnly(True)
            preview_layout.addWidget(self.query_preview)
            self.layout.addWidget(preview_group)

            # Buttons
            button_box = QDialogButtonBox()
            self.search_button = button_box.addButton(
                "Search", QDialogButtonBox.ButtonRole.AcceptRole)
            self.examples_button = button_box.addButton(
                "Show Examples", QDialogButtonBox.ButtonRole.ActionRole)
            self.clear_button = button_box.addButton(
                "Clear", QDialogButtonBox.ButtonRole.ResetRole)
            self.close_button = button_box.addButton(
                "Close", QDialogButtonBox.ButtonRole.RejectRole)

            self.search_button.clicked.connect(self.perform_search)
            self.examples_button.clicked.connect(self.show_examples)
            self.clear_button.clicked.connect(self.clear_all)
            self.close_button.clicked.connect(self.reject)

            self.layout.addWidget(button_box)

            # Connect signals for live preview
            self.base_query_input.textChanged.connect(self.update_preview)
            for cb in self.operator_checkboxes.values():
                cb.stateChanged.connect(self.update_preview)
            for input_field in self.operator_inputs.values():
                input_field.textChanged.connect(self.update_preview)

        def update_selected_engines(self):
            self.selected_engines = [
                engine for engine, cb in self.engine_checkboxes.items() if cb.isChecked()]
            if not self.selected_engines:
                # Ensure at least one engine
                self.selected_engines = ["google"]

        def toggle_operator_input(self):
            sender = self.sender()
            if sender in self.operator_checkboxes.values():
                op_name = [
                    name for name, cb in self.operator_checkboxes.items() if cb == sender][0]
                self.operator_inputs[op_name].setVisible(sender.isChecked())

        def update_preview(self):
            query_parts = []

            # Add base query
            base_query = self.base_query_input.text().strip()
            if base_query:
                query_parts.append(base_query)

            # Add selected operators
            for op_name, cb in self.operator_checkboxes.items():
                if cb.isChecked():
                    value = self.operator_inputs[op_name].text().strip()
                    if value:
                        if op_name in ['numrange', 'daterange']:
                            query_parts.append(f"{value}")
                        elif op_name in ['before', 'after']:
                            query_parts.append(f"{op_name}:{value}")
                        else:
                            query_parts.append(f"{op_name}:{value}")

            final_query = " ".join(query_parts)
            self.query_preview.setText(final_query)

        def perform_search(self):
            query = self.query_preview.toPlainText().strip()
            if not query:
                return

            # Open search in selected engines
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

        def show_examples(self):
            examples_dialog = QDialog(self)
            examples_dialog.setWindowTitle("Google Dork Examples")
            examples_dialog.setMinimumSize(600, 400)

            layout = QVBoxLayout(examples_dialog)

            examples_text = QTextEdit()
            examples_text.setReadOnly(True)

            examples = [
                # Basic dorks
                "site:example.com inurl:admin",
                "filetype:pdf site:gov confidential",
                "inurl:login.asp intitle:admin",
                "site:example.com ext:sql intext:password",

                # Advanced proximity dorks
                "\"tesla\" AROUND(5) \"battery\"",
                "\"AI\" NEAR/3 \"ethics\"",
                "\"quantum\" BEFORE \"mechanics\"",

                # Security research dorks
                "intitle:\"index of\" \"parent directory\"",
                "inurl:\"/phpinfo.php\"",
                "ext:(sql|db|bak|conf) intext:password",
                "site:github.com \"password\" filetype:env",

                # Content discovery dorks
                "inanchor:\"click here\" site:example.com",
                "allinurl: admin login site:example.com",
                "allintitle:\"login admin\" site:example.com",

                # Date-based searches
                "\"data science\" after:2022 before:2024",
                "site:news.com daterange:20230101-20231231",
                "numrange:1-100 filetype:xls",

                # Specialized searches
                "source:bbc \"Ukraine\"",
                "define:entropy",
                "phonebook:John Doe New York",
                "weather:New York",
                "stocks:AAPL",
                "movie:\"The Matrix\"",
                "book:\"Python programming\"",

                # Wildcard examples
                "\"best _ in the world\"",
                "\"the best * ever\"",

                # Complex combined dorks
                "(\"login\" OR \"admin\") NEAR/5 \"password\" site:example.com",
                "(site:example.com OR site:example.org) filetype:pdf confidential",
                "ext:sql -site:github.com intext:\"DROP TABLE\"",

                # Cache and related searches
                "cache:bbc.com",
                "related:openai.com",
                "info:example.com",
                "link:example.com"
            ]

            examples_text.setText(
                "\n".join(f"• {example}" for example in examples))
            layout.addWidget(examples_text)

            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Close)
            button_box.rejected.connect(examples_dialog.reject)
            layout.addWidget(button_box)

            examples_dialog.exec()

        def clear_all(self):
            self.base_query_input.clear()
            for cb in self.operator_checkboxes.values():
                cb.setChecked(False)
            for input_field in self.operator_inputs.values():
                input_field.clear()
                input_field.setVisible(False)
            self.query_preview.clear()


def google_osint():
    """
    Constructs advanced Google dorking queries with various operators and opens them in the user's default web browser.
    """
    if IS_GUI:
        # Try to get the main window from the call stack
        import inspect
        for frame in inspect.stack():
            if 'MainWindow' in str(frame.frame.f_code):
                main_window = frame.frame.f_locals.get('self')
                if main_window:
                    dialog = GoogleOsintDialog(main_window)
                    dialog.exec()
                    return

    # Fallback to console mode
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Google OSINT Dork Builder")
    print(f"{Color.DARK_GRAY}Build advanced Google dorks with multiple operators.")

    # Available dork operators with detailed explanations
    operators = {
        "1": {"name": "site", "desc": "Search within a specific site/domain. Syntax: site:domain.com"},
        "2": {"name": "inurl", "desc": "Search for URLs containing specific words. Syntax: inurl:word"},
        "3": {"name": "intext", "desc": "Search for pages containing specific text. Syntax: intext:word"},
        "4": {"name": "intitle", "desc": "Search for pages with specific words in title. Syntax: intitle:word"},
        "5": {"name": "filetype", "desc": "Search for specific file types. Syntax: filetype:extension"},
        "6": {"name": "ext", "desc": "Search for files with specific extensions. Syntax: ext:extension"},
        "7": {"name": "AROUND", "desc": "Find documents where words are within N words. Syntax: 'word1' AROUND(n) 'word2'"},
        "8": {"name": "NEAR", "desc": "Similar to AROUND (Bing/SQL/Elasticsearch). Syntax: 'word1' NEAR/n 'word2'"},
        "9": {"name": "BEFORE", "desc": "First word appears before second. Syntax: 'word1' BEFORE 'word2'"},
        "10": {"name": "AND", "desc": "Both words must be present. Syntax: word1 AND word2"},
        "11": {"name": "OR", "desc": "At least one word must be present. Syntax: word1 OR word2"},
        "12": {"name": "NOT", "desc": "Exclude words from results. Syntax: -word or NOT word"},
        "13": {"name": "exact_phrase", "desc": "Search for exact phrase match. Syntax: 'exact phrase here'"},
        "14": {"name": "grouping", "desc": "Group logical conditions. Syntax: (condition1 OR condition2) AND condition3"},
        "15": {"name": "inanchor", "desc": "Search for pages linked with specific anchor text. Syntax: inanchor:'click here'"},
        "16": {"name": "allinurl", "desc": "All specified words must be in URL. Syntax: allinurl:word1 word2"},
        "17": {"name": "allintitle", "desc": "All specified words must be in title. Syntax: allintitle:word1 word2"},
        "18": {"name": "allintext", "desc": "All specified words must be in text. Syntax: allintext:word1 word2"},
        "19": {"name": "cache", "desc": "View Google's cached version of a page. Syntax: cache:example.com"},
        "20": {"name": "related", "desc": "Find pages related to a URL. Syntax: related:example.com"},
        "21": {"name": "info", "desc": "Get information about a URL. Syntax: info:example.com"},
        "22": {"name": "link", "desc": "Find pages that link to a specific URL. Syntax: link:example.com"},
        "23": {"name": "after", "desc": "Search for content after specific date. Syntax: after:YYYY or after:YYYY-MM-DD"},
        "24": {"name": "before", "desc": "Search for content before specific date. Syntax: before:YYYY or before:YYYY-MM-DD"},
        "25": {"name": "daterange", "desc": "Search within date range. Syntax: daterange:start..end"},
        "26": {"name": "numrange", "desc": "Search within a range of numbers. Syntax: numrange:1-100"},
        "27": {"name": "wildcard_*", "desc": "Replace any number of words. Syntax: 'best * ever'"},
        "28": {"name": "wildcard__", "desc": "Replace exactly one word. Syntax: 'best _ in the world'"},
        "29": {"name": "define", "desc": "Get definitions of words. Syntax: define:word"},
        "30": {"name": "source", "desc": "Search news from specific source. Syntax: source:newsoutlet"},
        "31": {"name": "phonebook", "desc": "Search Google phonebook. Syntax: phonebook:John Doe location"},
        "32": {"name": "maps", "desc": "Search Google Maps. Syntax: maps:query"},
        "33": {"name": "book", "desc": "Search Google Books. Syntax: book:title or author"},
        "34": {"name": "finance", "desc": "Search Google Finance. Syntax: finance:stock_symbol"},
        "35": {"name": "movie", "desc": "Search for movie information. Syntax: movie:title"},
        "36": {"name": "weather", "desc": "Search weather information. Syntax: weather:location"},
        "37": {"name": "stocks", "desc": "Search stock information. Syntax: stocks:symbol"},
        "38": {"name": "location", "desc": "Search for location information. Syntax: location:query"},
        "39": {"name": "feed", "desc": "Search for RSS/Atom feeds. Syntax: feed:site.com"},
        "40": {"name": "group", "desc": "Search Google Groups. Syntax: group:query"},
        "41": {"name": "index_of", "desc": "Find open directories. Syntax: intitle:'index of' 'parent directory'"},
        "42": {"name": "phpinfo", "desc": "Find phpinfo.php pages. Syntax: inurl:'/phpinfo.php'"},
        "43": {"name": "exposed_files", "desc": "Find exposed database/config files. Syntax: ext:(sql|db|bak|conf) intext:password"},
        "44": {"name": "custom", "desc": "Enter custom operator or advanced dork manually"}
    }

    # Display operators menu
    print(f"\n{Color.DARK_GRAY}Available Dork Operators:")
    for key, op in operators.items():
        print(
            f"{Color.LIGHT_BLUE}{key:>2}.{Color.RESET} {op['name']:<12} - {op['desc']}")

    print(f"\n{Color.DARK_GRAY}Usage:")
    print(f"{Color.GRAY}- Select operators by number (comma-separated for multiple)")
    print(f"{Color.GRAY}- Enter '0' to build custom query manually")
    print(f"{Color.GRAY}- Enter 'help' to see examples")

    choice = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Select operators (e.g., 1,2,3): {Color.RESET}").strip()

    if choice.lower() == 'help':
        show_dork_examples()
        return google_osint()  # Restart after showing help

    if choice == '0':
        return manual_dork_builder()

    selected_ops = []
    if choice:
        choices = [c.strip() for c in choice.split(',')]
        for c in choices:
            if c in operators:
                selected_ops.append(operators[c])
            else:
                print(
                    f"{Color.DARK_GRAY}[{Color.YELLOW}⚠{Color.DARK_GRAY}]{Color.YELLOW} Invalid choice: {c}")

    if not selected_ops:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No valid operators selected!")
        return

    # Build the dork query
    query_parts = []

    for op in selected_ops:
        op_name = op['name']
        if op_name == 'custom':
            custom_op = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter custom operator: {Color.RESET}").strip()
            if ':' in custom_op:
                op_name, value = custom_op.split(':', 1)
                query_parts.append(f"{op_name}:{value}")
            else:
                query_parts.append(custom_op)
        else:
            value = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter value for '{op_name}': {Color.RESET}").strip()
            if value:
                if op_name in ['numrange', 'daterange']:
                    query_parts.append(f"{value}")
                elif op_name in ['before', 'after']:
                    query_parts.append(f"{op_name}:{value}")
                else:
                    query_parts.append(f"{op_name}:{value}")

    # Add base search terms
    base_query = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter base search terms (optional): {Color.RESET}").strip()
    if base_query:
        query_parts.insert(0, base_query)

    if not query_parts:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No query components provided!")
        return

    # Combine all parts
    final_query = " ".join(query_parts)

    # Ask user which search engines to use
    print(f"\n{Color.DARK_GRAY}Available Search Engines:")
    print(f"{Color.LIGHT_BLUE}1.{Color.RESET} Google (recommended for most dorks)")
    print(f"{Color.LIGHT_BLUE}2.{Color.RESET} Bing (good for NEAR/n and advanced operators)")
    print(f"{Color.LIGHT_BLUE}3.{Color.RESET} DuckDuckGo (privacy-focused)")
    print(f"{Color.LIGHT_BLUE}4.{Color.RESET} Yandex (good for Russian content)")
    print(f"{Color.LIGHT_BLUE}5.{Color.RESET} All engines")

    engine_choice = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Select search engines (comma-separated, default=1): {Color.RESET}").strip()

    if not engine_choice:
        engine_choice = "1"

    selected_engines = []
    choices = [c.strip() for c in engine_choice.split(',')]
    engines_map = {
        "1": "google",
        "2": "bing",
        "3": "duckduckgo",
        "4": "yandex",
        "5": "all"
    }

    for choice in choices:
        if choice in engines_map:
            if engines_map[choice] == "all":
                selected_engines = ["google", "bing", "duckduckgo", "yandex"]
                break
            else:
                selected_engines.append(engines_map[choice])

    if not selected_engines:
        selected_engines = ["google"]

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Generated Dork:")
    print(f"{Color.LIGHT_BLUE}{final_query}{Color.RESET}")

    # Open search in selected engines
    for engine in selected_engines:
        if engine == "google":
            url = f"https://www.google.com/search?q={quote_plus(final_query)}"
        elif engine == "bing":
            url = f"https://www.bing.com/search?q={quote_plus(final_query)}"
        elif engine == "duckduckgo":
            url = f"https://duckduckgo.com/?q={quote_plus(final_query)}"
        elif engine == "yandex":
            url = f"https://yandex.ru/search/?text={quote_plus(final_query)}"

        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Opening {engine.upper()} search:")
        print(f"{Color.LIGHT_BLUE}{url}{Color.RESET}")

        try:
            webbrowser.open(url)
            print(
                f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {engine.upper()} search opened successfully.")
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not open {engine}: {e}")
            print(f"{Color.GRAY}You can manually copy the link above.")


def manual_dork_builder():
    """Manual dork query builder for advanced users."""
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Manual Dork Builder")
    print(f"{Color.DARK_GRAY}Enter your complete dork query manually.")

    query = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter your dork query: {Color.RESET}").strip()

    if not query:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No query provided!")
        return

    # Ask user which search engines to use
    print(f"\n{Color.DARK_GRAY}Available Search Engines:")
    print(f"{Color.LIGHT_BLUE}1.{Color.RESET} Google (recommended for most dorks)")
    print(f"{Color.LIGHT_BLUE}2.{Color.RESET} Bing (good for NEAR/n and advanced operators)")
    print(f"{Color.LIGHT_BLUE}3.{Color.RESET} DuckDuckGo (privacy-focused)")
    print(f"{Color.LIGHT_BLUE}4.{Color.RESET} Yandex (good for Russian content)")
    print(f"{Color.LIGHT_BLUE}5.{Color.RESET} All engines")

    engine_choice = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Select search engines (comma-separated, default=1): {Color.RESET}").strip()

    if not engine_choice:
        engine_choice = "1"

    selected_engines = []
    choices = [c.strip() for c in engine_choice.split(',')]
    engines_map = {
        "1": "google",
        "2": "bing",
        "3": "duckduckgo",
        "4": "yandex",
        "5": "all"
    }

    for choice in choices:
        if choice in engines_map:
            if engines_map[choice] == "all":
                selected_engines = ["google", "bing", "duckduckgo", "yandex"]
                break
            else:
                selected_engines.append(engines_map[choice])

    if not selected_engines:
        selected_engines = ["google"]

    # Open search in selected engines
    for engine in selected_engines:
        if engine == "google":
            url = f"https://www.google.com/search?q={quote_plus(query)}"
        elif engine == "bing":
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
        elif engine == "duckduckgo":
            url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        elif engine == "yandex":
            url = f"https://yandex.ru/search/?text={quote_plus(query)}"

        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Opening {engine.upper()} search:")
        print(f"{Color.LIGHT_BLUE}{url}{Color.RESET}")

        try:
            webbrowser.open(url)
            print(
                f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {engine.upper()} search opened successfully.")
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not open {engine}: {e}")
            print(f"{Color.GRAY}You can manually copy the link above.")


def show_dork_examples():
    """Display examples of common Google dorks."""
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Google Dork Examples")
    print(f"{Color.DARK_GRAY}📚 Advanced Dork Examples with Explanations:")

    examples = [
        # Basic dorks
        ("site:example.com inurl:admin", "Find admin pages on a specific site"),
        ("filetype:pdf site:gov confidential",
         "Find confidential PDFs on government sites"),
        ("inurl:login.asp intitle:admin", "Find ASP login pages with admin in title"),
        ("site:example.com ext:sql intext:password",
         "Find SQL files with passwords on a site"),

        # Advanced proximity dorks
        ("\"tesla\" AROUND(5) \"battery\"",
         "Find Tesla and battery within 5 words"),
        ("\"AI\" NEAR/3 \"ethics\"", "Find AI and ethics within 3 words (Bing/SQL)"),
        ("\"quantum\" BEFORE \"mechanics\"", "Find quantum before mechanics"),

        # Security research dorks
        ("intitle:\"index of\" \"parent directory\"", "Find open directories"),
        ("inurl:\"/phpinfo.php\"", "Find PHP info disclosure pages"),
        ("ext:(sql|db|bak|conf) intext:password",
         "Find exposed database files with passwords"),
        ("site:github.com \"password\" filetype:env",
         "Find exposed .env files on GitHub"),

        # Content discovery dorks
        ("inanchor:\"click here\" site:example.com",
         "Find pages linking with 'click here'"),
        ("allinurl: admin login site:example.com",
         "All words in URL on specific site"),
        ("allintitle:\"login admin\" site:example.com", "All words in title"),

        # Date-based searches
        ("\"data science\" after:2022 before:2024",
         "Data science content from 2022-2024"),
        ("site:news.com daterange:20230101-20231231", "News from 2023"),
        ("numrange:1-100 filetype:xls", "Excel files with numbers 1-100"),

        # Specialized searches
        ("source:bbc \"Ukraine\"", "BBC news about Ukraine"),
        ("define:entropy", "Definition of entropy"),
        ("phonebook:John Doe New York", "Phonebook search"),
        ("weather:New York", "Weather in New York"),
        ("stocks:AAPL", "Apple stock information"),
        ("movie:\"The Matrix\"", "Information about The Matrix"),
        ("book:\"Python programming\"", "Python programming books"),

        # Wildcard examples
        ("\"best _ in the world\"", "Fill in the blank with one word"),
        ("\"the best * ever\"", "Fill in the blank with any words"),

        # Complex combined dorks
        ("(\"login\" OR \"admin\") NEAR/5 \"password\" site:example.com",
         "Login/admin near password"),
        ("(site:example.com OR site:example.org) filetype:pdf confidential",
         "Confidential PDFs on multiple sites"),
        ("ext:sql -site:github.com intext:\"DROP TABLE\"",
         "SQL files with DROP TABLE (excluding GitHub)"),

        # Cache and related searches
        ("cache:bbc.com", "Google's cached version of BBC"),
        ("related:openai.com", "Sites related to OpenAI"),
        ("info:example.com", "Information about a site"),
        ("link:example.com", "Pages linking to example.com")
    ]

    for i, (example, description) in enumerate(examples, 1):
        print(
            f"{Color.LIGHT_BLUE}{i:2d}.{Color.RESET} {Color.LIGHT_GREEN}{example}{Color.RESET}")
        print(f"{Color.GRAY}   └─ {description}{Color.RESET}")

    print(f"\n{Color.DARK_GRAY}💡 Pro Tips:")
    print(f"{Color.GRAY}• Combine operators for powerful searches")
    print(f"{Color.GRAY}• Use quotes for exact phrases")
    print(f"{Color.GRAY}• AROUND(n) works best in Google, NEAR/n in Bing")
    print(f"{Color.GRAY}• Some operators may not work in all search engines")

    input(f"\n{Color.GRAY}Press Enter to continue...{Color.RESET}")
