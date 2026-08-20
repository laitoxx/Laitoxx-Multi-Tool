"""Examples dialog for the Google OSINT builder."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTextEdit, QVBoxLayout


class GoogleDialogExamplesMixin:
    def show_examples(self):
        examples_dialog = QDialog(self)
        examples_dialog.setWindowTitle("Google Dork Examples")
        examples_dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(examples_dialog)

        examples_text = QTextEdit()
        examples_text.setReadOnly(True)

        examples = [
            "site:example.com inurl:admin",
            "filetype:pdf site:gov confidential",
            "inurl:login.asp intitle:admin",
            "site:example.com ext:sql intext:password",
            '"tesla" AROUND(5) "battery"',
            '"AI" NEAR/3 "ethics"',
            '"quantum" BEFORE "mechanics"',
            'intitle:"index of" "parent directory"',
            'inurl:"/phpinfo.php"',
            "ext:(sql|db|bak|conf) intext:password",
            'site:github.com "password" filetype:env',
            'inanchor:"click here" site:example.com',
            "allinurl: admin login site:example.com",
            'allintitle:"login admin" site:example.com',
            '"data science" after:2022 before:2024',
            "site:news.com daterange:20230101-20231231",
            "numrange:1-100 filetype:xls",
            'source:bbc "Ukraine"',
            "define:entropy",
            "phonebook:John Doe New York",
            "weather:New York",
            "stocks:AAPL",
            'movie:"The Matrix"',
            'book:"Python programming"',
            '"best _ in the world"',
            '"the best * ever"',
            '("login" OR "admin") NEAR/5 "password" site:example.com',
            "(site:example.com OR site:example.org) filetype:pdf confidential",
            'ext:sql -site:github.com intext:"DROP TABLE"',
            "cache:bbc.com",
            "related:openai.com",
            "info:example.com",
            "link:example.com",
        ]

        examples_text.setText("\n".join(f"• {example}" for example in examples))
        layout.addWidget(examples_text)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(examples_dialog.reject)
        layout.addWidget(button_box)

        examples_dialog.exec()
