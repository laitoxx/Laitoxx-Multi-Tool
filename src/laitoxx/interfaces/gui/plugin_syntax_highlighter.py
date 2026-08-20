"""
Lua Plugin Builder - code editor with syntax highlighting, code snippets,
syntax checking, and OS-dependent template generation.
"""

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
)

# ============================================================================
# Lua Syntax Highlighter
# ============================================================================


class LuaSyntaxHighlighter(QSyntaxHighlighter):
    """Rich Lua syntax highlighter with keywords, strings, comments, numbers, host API."""

    def __init__(self, document):
        super().__init__(document)
        self._rules = []

        # --- Keywords ---
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#c678dd"))
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "and",
            "break",
            "do",
            "else",
            "elseif",
            "end",
            "false",
            "for",
            "function",
            "goto",
            "if",
            "in",
            "local",
            "nil",
            "not",
            "or",
            "repeat",
            "return",
            "then",
            "true",
            "until",
            "while",
        ]
        for w in keywords:
            self._rules.append((QRegularExpression(rf"\b{w}\b"), kw_fmt))

        # --- Built-in functions ---
        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor("#61afef"))
        builtins = [
            "print",
            "type",
            "tostring",
            "tonumber",
            "pairs",
            "ipairs",
            "next",
            "select",
            "unpack",
            "pcall",
            "xpcall",
            "error",
            "assert",
            "rawget",
            "rawset",
            "rawequal",
            "setmetatable",
            "getmetatable",
        ]
        for w in builtins:
            self._rules.append((QRegularExpression(rf"\b{w}\b"), builtin_fmt))

        # --- host API ---
        host_fmt = QTextCharFormat()
        host_fmt.setForeground(QColor("#e5c07b"))
        host_fmt.setFontItalic(True)
        self._rules.append((QRegularExpression(r"\bhost\b"), host_fmt))

        host_method_fmt = QTextCharFormat()
        host_method_fmt.setForeground(QColor("#e5c07b"))
        host_methods = [
            "log",
            "http_get",
            "http_post",
            "json_decode",
            "json_encode",
            "read_file",
            "write_file",
            "file_exists",
            "get_config",
            "get_all_config",
            "hash",
            "base64_encode",
            "base64_decode",
            "url_encode",
            "url_decode",
            "sleep",
            "get_tool_version",
            "get_platform",
            "cache_get",
            "cache_set",
            "cache_clear",
        ]
        for m in host_methods:
            self._rules.append((QRegularExpression(rf"\b{m}\b"), host_method_fmt))

        # --- String/table modules ---
        mod_fmt = QTextCharFormat()
        mod_fmt.setForeground(QColor("#56b6c2"))
        modules = ["string", "table", "math"]
        for m in modules:
            self._rules.append((QRegularExpression(rf"\b{m}\b"), mod_fmt))

        # --- Numbers ---
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#d19a66"))
        self._rules.append((QRegularExpression(r"\b\d+\.?\d*\b"), num_fmt))
        self._rules.append((QRegularExpression(r"\b0x[0-9a-fA-F]+\b"), num_fmt))

        # --- Strings (single-line) ---
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#98c379"))
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), str_fmt))
        self._rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), str_fmt))

        # --- Single-line comments ---
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#5c6370"))
        comment_fmt.setFontItalic(True)
        self._rules.append((QRegularExpression(r"--(?!\[\[).*$"), comment_fmt))

        # --- Multi-line comment/string formats (handled in highlightBlock) ---
        self._multiline_comment_fmt = QTextCharFormat()
        self._multiline_comment_fmt.setForeground(QColor("#5c6370"))
        self._multiline_comment_fmt.setFontItalic(True)

        self._multiline_string_fmt = QTextCharFormat()
        self._multiline_string_fmt.setForeground(QColor("#98c379"))

    def highlightBlock(self, text):
        # Apply single-line rules
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        # Multi-line comments --[[ ... ]]
        self._handle_multiline(text, r"--\[\[", r"\]\]", self._multiline_comment_fmt, state=1)
        # Multi-line strings [[ ... ]]
        self._handle_multiline(text, r"\[\[", r"\]\]", self._multiline_string_fmt, state=2)

    def _handle_multiline(self, text, start_pat, end_pat, fmt, state):
        start_re = QRegularExpression(start_pat)
        end_re = QRegularExpression(end_pat)

        if self.previousBlockState() == state:
            start_idx = 0
        else:
            match = start_re.match(text)
            if match.hasMatch():
                start_idx = match.capturedStart()
            else:
                return

        while start_idx >= 0:
            end_match = end_re.match(text, start_idx + 1)
            if end_match.hasMatch():
                length = end_match.capturedEnd() - start_idx
                self.setFormat(start_idx, length, fmt)
                # Look for next start
                next_match = start_re.match(text, end_match.capturedEnd())
                start_idx = next_match.capturedStart() if next_match.hasMatch() else -1
            else:
                self.setFormat(start_idx, len(text) - start_idx, fmt)
                self.setCurrentBlockState(state)
                return
