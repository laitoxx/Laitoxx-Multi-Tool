"""
Lua Plugin Builder — code editor with syntax highlighting, code snippets,
syntax checking, and OS-dependent template generation.
"""

import os
import re
import random

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QFormLayout, QDialogButtonBox, QStackedWidget, QScrollArea,
    QSplitter, QFileDialog, QMessageBox, QToolButton, QMenu,
    QPlainTextEdit, QApplication,
)
from PyQt6.QtGui import (
    QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPainter,
    QTextFormat, QKeyEvent, QFontMetrics,
)
from PyQt6.QtCore import Qt, QRect, QRegularExpression


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
            "and", "break", "do", "else", "elseif", "end", "false",
            "for", "function", "goto", "if", "in", "local", "nil",
            "not", "or", "repeat", "return", "then", "true", "until", "while",
        ]
        for w in keywords:
            self._rules.append((QRegularExpression(rf"\b{w}\b"), kw_fmt))

        # --- Built-in functions ---
        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor("#61afef"))
        builtins = [
            "print", "type", "tostring", "tonumber", "pairs", "ipairs",
            "next", "select", "unpack", "pcall", "xpcall", "error",
            "assert", "rawget", "rawset", "rawequal",
            "setmetatable", "getmetatable",
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
            "log", "http_get", "http_post", "json_decode", "json_encode",
            "read_file", "write_file", "file_exists", "get_config",
            "get_all_config", "hash", "base64_encode", "base64_decode",
            "url_encode", "url_decode", "sleep", "get_tool_version",
            "get_platform", "cache_get", "cache_set", "cache_clear",
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
        self._handle_multiline(text, r"--\[\[", r"\]\]",
                               self._multiline_comment_fmt, state=1)
        # Multi-line strings [[ ... ]]
        self._handle_multiline(text, r"\[\[", r"\]\]",
                               self._multiline_string_fmt, state=2)

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


# ============================================================================
# Line Number Area for the code editor
# ============================================================================

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor._line_number_area_width()

    def paintEvent(self, event):
        self.editor._paint_line_numbers(event)


# ============================================================================
# Lua Code Editor Widget
# ============================================================================

class LuaCodeEditor(QPlainTextEdit):
    """Code editor with line numbers, auto-indent, and tab handling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)

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
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self._line_number_area_width(), cr.height())
        )

    def _paint_line_numbers(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#21252b"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#636d83"))
                painter.drawText(
                    0, top, self._line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1)
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self):
        selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#2c313a"))
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
                if ch in (' ', '\t'):
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


# ============================================================================
# Code Snippets
# ============================================================================

CODE_SNIPPETS = {
    "http_get": {
        "label": "HTTP GET Request",
        "description": "Make an HTTP GET request and parse JSON response",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "https://api.example.com/endpoint"},
        ],
        "template": '''
    local body, err = host:http_get("{url}", 15)
    if not body then
        host:print("Request failed: " .. (err or "unknown error"))
        return nil, err
    end
    host:print("Response received: " .. #body .. " bytes")
''',
    },
    "http_post": {
        "label": "HTTP POST Request",
        "description": "Make an HTTP POST request with JSON body",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "https://api.example.com/endpoint"},
            {"key": "body_desc", "label": "Body description", "placeholder": "key = value, ..."},
        ],
        "template": '''
    local post_data = host:json_encode({{ {body_desc} }})
    local body, err = host:http_post("{url}", post_data, 15)
    if not body then
        host:print("POST failed: " .. (err or "unknown error"))
        return nil, err
    end
    host:print("POST response: " .. #body .. " bytes")
''',
    },
    "json_parse": {
        "label": "Parse JSON Response",
        "description": "Decode a JSON string into a Lua table",
        "fields": [],
        "template": '''
    local data, err = host:json_decode(body)
    if not data then
        return nil, "JSON parse error: " .. (err or "unknown")
    end
''',
    },
    "http_get_json": {
        "label": "GET + Parse JSON (Full)",
        "description": "Complete HTTP GET with JSON parsing and error handling",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "https://api.example.com/search?q="},
            {"key": "query_param", "label": "Append query?", "placeholder": "yes"},
        ],
        "template": '''
    local url = "{url}"
    if query and query ~= "" then
        url = url .. host:url_encode(query)
    end

    local body, err = host:http_get(url, 15)
    if not body then
        return nil, "HTTP error: " .. (err or "unknown")
    end

    local data, err = host:json_decode(body)
    if not data then
        return nil, "JSON parse error: " .. (err or "unknown")
    end

    host:print("Got " .. tostring(#data) .. " results")
''',
    },
    "config_check": {
        "label": "Check Config Value",
        "description": "Read and validate a user-configured API key",
        "fields": [
            {"key": "config_key", "label": "Config key", "placeholder": "api_key"},
        ],
        "template": '''
    local api_key = host:get_config("{config_key}")
    if not api_key or api_key == "" then
        return nil, "Please configure '{config_key}' in plugin settings."
    end
''',
    },
    "format_output": {
        "label": "Format Output Lines",
        "description": "Build formatted output with multiple lines",
        "fields": [],
        "template": '''
    local lines = {}
    lines[#lines + 1] = "=== Results ==="
    lines[#lines + 1] = ""
    -- Add your formatted lines here:
    -- lines[#lines + 1] = "Key:   " .. tostring(value)
    lines[#lines + 1] = ""
    lines[#lines + 1] = "==============="
    return table.concat(lines, "\\n")
''',
    },
    "error_handling": {
        "label": "Error Handling (pcall)",
        "description": "Wrap code in pcall for safe execution",
        "fields": [],
        "template": '''
    local ok, result = pcall(function()
        -- Your code here
        return "success"
    end)
    if not ok then
        host:log("Error: " .. tostring(result), "error")
        return nil, "Internal error: " .. tostring(result)
    end
''',
    },
    "file_cache": {
        "label": "File-based Cache",
        "description": "Cache results to a file in the plugin directory",
        "fields": [
            {"key": "cache_file", "label": "Cache filename", "placeholder": "cache.json"},
        ],
        "template": '''
    -- Try to read from cache
    local cached = host:read_file("{cache_file}")
    if cached then
        local data = host:json_decode(cached)
        if data then
            host:print("Loaded from cache")
            return host:json_encode(data)
        end
    end

    -- ... fetch fresh data ...

    -- Save to cache
    host:write_file("{cache_file}", host:json_encode(fresh_data))
''',
    },
    "iterate_results": {
        "label": "Iterate Over Results",
        "description": "Loop through a table of results and format output",
        "fields": [],
        "template": '''
    local output = {}
    for i, item in ipairs(results) do
        output[#output + 1] = string.format(
            "%d. %s — %s",
            i,
            tostring(item.name or "N/A"),
            tostring(item.value or "N/A")
        )
    end
    return table.concat(output, "\\n")
''',
    },
    "hash_data": {
        "label": "Hash Data",
        "description": "Hash input text with a chosen algorithm",
        "fields": [
            {"key": "algorithm", "label": "Algorithm", "placeholder": "sha256"},
        ],
        "template": '''
    local hash_result = host:hash(query, "{algorithm}")
    host:print("{algorithm} hash: " .. tostring(hash_result))
''',
    },
}

# Dynamic tips that rotate in the status bar
LUA_TIPS = [
    "host:print() outputs text to the UI — use it for progress updates",
    "Return nil, 'error message' to signal errors to the user",
    "host:http_get(url, timeout) returns body or nil, error",
    "host:json_decode(str) converts JSON to a Lua table",
    "host:get_config('key') reads user-configured plugin settings",
    "Use host:url_encode(query) before inserting into URLs",
    "host:cache_get/cache_set provide in-memory session cache",
    "Files via host:read_file/write_file are sandboxed to plugin dir",
    "host:sleep(seconds) max 60s — use sparingly",
    "host:hash(text, 'sha256') hashes text with any supported algorithm",
    "Use local variables to avoid polluting the sandbox environment",
    "table.concat(lines, '\\n') is the best way to build multiline output",
    "Lua arrays are 1-based: first element is t[1], not t[0]",
    "host:log(msg, 'warn') logs to app log + plugin output",
    "pcall(func) catches errors without crashing the plugin",
    "string.format('%s has %d items', name, count) for formatting",
    "Lua patterns: %d=digit, %a=letter, %w=alphanumeric, %s=space",
    "host:get_platform() returns 'Windows', 'Linux', or 'Darwin'",
]


# ============================================================================
# Lua Syntax Checker
# ============================================================================

def check_lua_syntax(source: str) -> list[dict]:
    """
    Check Lua source code for common syntax issues.
    Returns a list of {line, message, severity} dicts.
    """
    issues = []
    lines = source.split('\n')

    # Track block balance
    block_openers = 0
    block_closers = 0
    paren_depth = 0
    bracket_depth = 0
    in_multiline_string = False
    in_multiline_comment = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Handle multi-line comments
        if in_multiline_comment:
            if "]]" in stripped:
                in_multiline_comment = False
            continue
        if "--[[" in stripped:
            if "]]" not in stripped.split("--[[", 1)[1]:
                in_multiline_comment = True
            continue

        # Handle multi-line strings
        if in_multiline_string:
            if "]]" in stripped:
                in_multiline_string = False
            continue
        if "[[" in stripped and "--" not in stripped.split("[[")[0]:
            if "]]" not in stripped.split("[[", 1)[1]:
                in_multiline_string = True
            continue

        # Skip single-line comments
        code = stripped.split("--")[0] if "--" in stripped else stripped
        if not code:
            continue

        # Strip string literals to avoid false keyword matches inside strings
        code_no_strings = re.sub(r'"[^"]*"', '""', code)
        code_no_strings = re.sub(r"'[^']*'", "''", code_no_strings)

        # Count block openers/closers using string-stripped code
        openers_on_line = 0
        for w in re.findall(r'\b(function|if|for|while|repeat|do)\b', code_no_strings):
            if w == "do":
                if not re.search(r'\b(for|while)\b', code_no_strings):
                    openers_on_line += 1
            elif w == "if":
                if not re.search(r'\belseif\b', code_no_strings):
                    openers_on_line += 1
            else:
                openers_on_line += 1

        closers_on_line = len(re.findall(r'\bend\b', code_no_strings))
        if re.search(r'\buntil\b', code_no_strings):
            closers_on_line += 1

        # For single-line blocks (e.g. "if x then return end"), pairs cancel out
        net = openers_on_line - closers_on_line
        if net > 0:
            block_openers += net
        elif net < 0:
            block_closers += abs(net)

        # Parentheses / brackets balance per line
        paren_depth += code.count('(') - code.count(')')
        bracket_depth += code.count('{') - code.count('}')

        # Check for common mistakes (use code_no_strings to avoid false positives)

        # Assignment in condition (= instead of ==)
        if_match = re.match(r'.*\bif\b\s+(.+?)\s+\bthen\b', code_no_strings)
        if if_match:
            cond = if_match.group(1)
            if re.search(r'(?<!=)(?<!~)(?<!<)(?<!>)=(?!=)', cond):
                issues.append({
                    "line": i,
                    "message": "Possible assignment in condition (use '==' for comparison)",
                    "severity": "warning",
                })

        # Missing 'then' after 'if'
        if re.search(r'\bif\b', code_no_strings) and not re.search(r'\bthen\b', code_no_strings):
            if not code_no_strings.rstrip().endswith(',') and not code_no_strings.rstrip().endswith('('):
                issues.append({
                    "line": i,
                    "message": "Missing 'then' after 'if' condition",
                    "severity": "error",
                })

        # 'elseif' without 'then'
        if re.search(r'\belseif\b', code_no_strings) and not re.search(r'\bthen\b', code_no_strings):
            issues.append({
                "line": i,
                "message": "Missing 'then' after 'elseif'",
                "severity": "error",
            })

        # Using '!=' instead of '~='
        if '!=' in code_no_strings:
            issues.append({
                "line": i,
                "message": "Lua uses '~=' for not-equal, not '!='",
                "severity": "error",
            })

        # Using '++' or '+='
        if '++' in code_no_strings or '+=' in code_no_strings or '-=' in code_no_strings:
            issues.append({
                "line": i,
                "message": "Lua doesn't support '++', '+=', '-='. Use: x = x + 1",
                "severity": "error",
            })

        # Using '//' for comments
        if code_no_strings.lstrip().startswith('//'):
            issues.append({
                "line": i,
                "message": "Lua uses '--' for comments, not '//'",
                "severity": "error",
            })

        # Empty function body
        if re.match(r'\s*function\b.*\bend\b\s*$', code_no_strings):
            if 'return' not in code_no_strings and 'print' not in code_no_strings:
                issues.append({
                    "line": i,
                    "message": "Empty function body — did you mean to add code?",
                    "severity": "warning",
                })

        # host. instead of host:
        if 'host.' in code_no_strings and 'host:' not in code_no_strings:
            if re.search(r'host\.\w+\s*\(', code_no_strings):
                issues.append({
                    "line": i,
                    "message": "Use 'host:method()' (colon syntax), not 'host.method()'",
                    "severity": "warning",
                })

    # Check final balances
    if block_openers > block_closers:
        diff = block_openers - block_closers
        issues.append({
            "line": len(lines),
            "message": f"Missing {diff} 'end' statement(s) — unclosed block(s)",
            "severity": "error",
        })
    elif block_closers > block_openers:
        diff = block_closers - block_openers
        issues.append({
            "line": len(lines),
            "message": f"Extra {diff} 'end' statement(s) — no matching block opener",
            "severity": "error",
        })

    if paren_depth != 0:
        issues.append({
            "line": len(lines),
            "message": f"Unbalanced parentheses (depth: {paren_depth})",
            "severity": "error",
        })

    if bracket_depth != 0:
        issues.append({
            "line": len(lines),
            "message": f"Unbalanced curly braces (depth: {bracket_depth})",
            "severity": "error",
        })

    # Check for required plugin structure
    if "return plugin" not in source and "return plugin\n" not in source:
        if source.strip() and "local plugin" in source:
            issues.append({
                "line": len(lines),
                "message": "Missing 'return plugin' at the end of the file",
                "severity": "warning",
            })

    return issues


# ============================================================================
# OS-dependent code templates
# ============================================================================

def generate_plugin_template(plugin_name: str, plugin_type: str,
                             author: str, description: str,
                             target_os: list[str]) -> str:
    """Generate a Lua plugin template based on metadata and target OS."""

    os_comment = ""
    os_check = ""
    if target_os:
        os_list = ", ".join(f'"{o}"' for o in target_os)
        os_comment = f"-- Target OS: {', '.join(target_os)}\n"
        if len(target_os) < 3:
            os_names = " or ".join(f'"{o}"' for o in target_os)
            os_check = f'''
    -- OS check
    local platform = host:get_platform()
    local supported = {{ {os_list} }}
    local ok = false
    for _, os_name in ipairs(supported) do
        if platform:lower():find(os_name:lower()) then ok = true; break end
    end
    if not ok then
        return nil, "This plugin only supports: " .. table.concat(supported, ", ")
    end
'''

    safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_name).lower()

    func_name = {
        "search": "search",
        "processor": "process",
        "formatter": "format",
        "passive_scanner": "scan",
    }.get(plugin_type, "search")

    func_param = {
        "search": "query",
        "processor": "data",
        "formatter": "data",
        "passive_scanner": "target",
    }.get(plugin_type, "query")

    func_body = os_check + f'''
    if not {func_param} or {func_param} == "" then
        return nil, "Input cannot be empty."
    end

    host:print("Running {plugin_name}...")
    host:print("Input: " .. {func_param})

    -- TODO: Add your logic here

    return "Done!"'''

    # For search type, also add the search alias
    extra_func = ""
    if plugin_type == "processor":
        extra_func = "\n-- Alias: also works when called as 'search'\nplugin.search = plugin.process\n"
    elif plugin_type == "formatter":
        extra_func = "\n-- Alias: also works when called as 'search'\nplugin.search = plugin.format\n"
    elif plugin_type == "passive_scanner":
        extra_func = "\n-- Alias: also works when called as 'search'\nplugin.search = plugin.scan\n"

    return f'''{os_comment}local plugin = {{
    id          = "{safe_id}",
    name        = "{plugin_name}",
    description = "{description}",
    author      = "{author}",
    version     = "1.0",
    type        = "{plugin_type}",

    -- User-configurable settings (shown in plugin settings UI)
    config_schema = {{
        -- {{ key = "api_key", label = "API Key", type = "string", default = "" }},
    }},
}}

function plugin.{func_name}({func_param}, options){func_body}
end
{extra_func}
return plugin
'''


# ============================================================================
# Snippet Insert Dialog
# ============================================================================

class SnippetInsertDialog(QDialog):
    """Dialog to configure and insert a code snippet."""

    def __init__(self, parent, snippet_key: str):
        super().__init__(parent)
        snippet = CODE_SNIPPETS[snippet_key]
        self.snippet = snippet
        self.setWindowTitle(snippet["label"])
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(snippet["description"]))

        self._field_widgets = {}
        if snippet["fields"]:
            form = QFormLayout()
            for field in snippet["fields"]:
                w = QLineEdit()
                w.setPlaceholderText(field.get("placeholder", ""))
                form.addRow(field["label"] + ":", w)
                self._field_widgets[field["key"]] = w
            layout.addLayout(form)

        # Preview
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 10))
        self.preview.setMaximumHeight(200)
        self.preview.setStyleSheet(
            "background-color: #282c34; color: #abb2bf; border: 1px solid #3e4451;"
        )
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.preview)

        # Update preview on field changes
        for w in self._field_widgets.values():
            w.textChanged.connect(self._update_preview)
        self._update_preview()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_preview(self):
        self.preview.setText(self.get_code())

    def get_code(self) -> str:
        code = self.snippet["template"]
        for key, widget in self._field_widgets.items():
            value = widget.text() or widget.placeholderText()
            code = code.replace(f"{{{key}}}", value)
        return code


# ============================================================================
# Main Plugin Builder Window
# ============================================================================

class PluginBuilderWindow(QDialog):
    """
    Lua Plugin Builder — a full code editor for creating Lua plugins.

    Features:
    - Syntax highlighting
    - Line numbers
    - Code snippets with configurable fields
    - Lua syntax checker
    - OS-dependent template generation
    - Dynamic tips
    """

    def __init__(self, parent=None, plugin_path=None, translator=None):
        super().__init__(parent)
        self.translator = translator
        self.plugin_path = plugin_path  # path to existing .lua file for editing
        self.setMinimumSize(1000, 700)
        self.setWindowOpacity(0.92)

        self.stacked_widget = QStackedWidget(self)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stacked_widget)

        self._create_meta_page()
        self._create_editor_page()
        self.retranslate_ui()

        if self.plugin_path and os.path.exists(self.plugin_path):
            self._load_existing_plugin()
        else:
            self.stacked_widget.setCurrentIndex(0)

    def retranslate_ui(self):
        t = self.translator
        self.setWindowTitle(t.get("lua_builder_title"))
        self.meta_continue_btn.setText(t.get("continue"))
        self.meta_cancel_btn.setText(t.get("cancel"))
        self.btn_save.setText(t.get("save_plugin"))
        self.btn_check_syntax.setText(t.get("lua_check_syntax"))
        self.btn_snippets.setText(t.get("lua_insert_snippet"))
        self.btn_open_file.setText(t.get("lua_open_file"))

    # ------------------------------------------------------------------
    # Page 1: Metadata
    # ------------------------------------------------------------------

    def _create_meta_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Lua Plugin Builder")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()

        self.meta_name = QLineEdit()
        self.meta_name.setPlaceholderText("My Awesome Plugin")
        form.addRow("Plugin Name:", self.meta_name)

        self.meta_author = QLineEdit()
        self.meta_author.setPlaceholderText("Your Name")
        form.addRow("Author:", self.meta_author)

        self.meta_description = QTextEdit()
        self.meta_description.setFixedHeight(80)
        self.meta_description.setPlaceholderText("What does this plugin do?")
        form.addRow("Description:", self.meta_description)

        self.meta_type = QComboBox()
        self.meta_type.addItem("Search — query external sources", "search")
        self.meta_type.addItem("Processor — transform/enrich data", "processor")
        self.meta_type.addItem("Formatter — format/export results", "formatter")
        self.meta_type.addItem("Passive Scanner — analyze input", "passive_scanner")
        form.addRow("Plugin Type:", self.meta_type)

        # OS checkboxes
        os_widget = QWidget()
        os_layout = QHBoxLayout(os_widget)
        os_layout.setContentsMargins(0, 0, 0, 0)
        self.os_checks = {}
        for os_name in ["Windows", "Linux", "macOS"]:
            cb = QCheckBox(os_name)
            cb.setChecked(True)
            self.os_checks[os_name] = cb
            os_layout.addWidget(cb)
        form.addRow("Target OS:", os_widget)

        layout.addLayout(form)

        btn_box = QDialogButtonBox()
        self.meta_continue_btn = btn_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.meta_cancel_btn = btn_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._go_to_editor)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.stacked_widget.addWidget(page)

    def _go_to_editor(self):
        name = self.meta_name.text().strip()
        if not name:
            return

        target_os = [n for n, cb in self.os_checks.items() if cb.isChecked()]
        code = generate_plugin_template(
            plugin_name=name,
            plugin_type=self.meta_type.currentData(),
            author=self.meta_author.text().strip() or "Unknown",
            description=self.meta_description.toPlainText().strip(),
            target_os=target_os,
        )

        self.editor.setPlainText(code)
        self._current_filename = re.sub(r'[^a-zA-Z0-9_]', '_', name).lower() + ".lua"
        self.setWindowTitle(f"Plugin Builder — {self._current_filename}")
        self.stacked_widget.setCurrentIndex(1)
        self._show_random_tip()

    # ------------------------------------------------------------------
    # Page 2: Code Editor
    # ------------------------------------------------------------------

    def _create_editor_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Toolbar
        toolbar = QHBoxLayout()

        self.btn_snippets = QPushButton()
        self.btn_snippets.setMenu(self._build_snippets_menu())
        toolbar.addWidget(self.btn_snippets)

        self.btn_check_syntax = QPushButton()
        self.btn_check_syntax.clicked.connect(self._check_syntax)
        toolbar.addWidget(self.btn_check_syntax)

        self.btn_open_file = QPushButton()
        self.btn_open_file.clicked.connect(self._open_lua_file)
        toolbar.addWidget(self.btn_open_file)

        toolbar.addStretch()

        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self._save_plugin)
        toolbar.addWidget(self.btn_save)

        layout.addLayout(toolbar)

        # Splitter: editor | issues panel
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Code editor
        self.editor = LuaCodeEditor()
        self._highlighter = LuaSyntaxHighlighter(self.editor.document())
        splitter.addWidget(self.editor)

        # Issues / output panel
        self.issues_area = QTextEdit()
        self.issues_area.setReadOnly(True)
        self.issues_area.setMaximumHeight(150)
        self.issues_area.setStyleSheet(
            "QTextEdit { background-color: #1e2127; color: #abb2bf;"
            " border: 1px solid #3e4451; border-radius: 4px; font-size: 12px; }"
        )
        self.issues_area.setFont(QFont("Consolas", 10))
        splitter.addWidget(self.issues_area)

        splitter.setSizes([500, 150])
        layout.addWidget(splitter)

        # Tip bar
        self.tip_label = QLabel()
        self.tip_label.setWordWrap(True)
        self.tip_label.setStyleSheet(
            "color: #5c6370; font-style: italic; padding: 4px;"
        )
        layout.addWidget(self.tip_label)

        self._current_filename = "new_plugin.lua"
        self.stacked_widget.addWidget(page)

    def _build_snippets_menu(self) -> QMenu:
        menu = QMenu(self)
        for key, snippet in CODE_SNIPPETS.items():
            action = menu.addAction(snippet["label"])
            action.setToolTip(snippet["description"])
            action.triggered.connect(lambda checked, k=key: self._insert_snippet(k))
        return menu

    def _insert_snippet(self, snippet_key: str):
        snippet = CODE_SNIPPETS[snippet_key]
        if snippet["fields"]:
            dlg = SnippetInsertDialog(self, snippet_key)
            if dlg.exec():
                self.editor.insert_snippet(dlg.get_code())
        else:
            self.editor.insert_snippet(snippet["template"])
        self._show_random_tip()

    # ------------------------------------------------------------------
    # Syntax Checker
    # ------------------------------------------------------------------

    def _check_syntax(self):
        source = self.editor.toPlainText()
        issues = check_lua_syntax(source)

        self.issues_area.clear()
        if not issues:
            self.issues_area.setHtml(
                '<span style="color: #98c379;">&#10004; No issues found. Code looks good!</span>'
            )
            return

        html_parts = []
        for issue in issues:
            color = "#e06c75" if issue["severity"] == "error" else "#e5c07b"
            icon = "&#10006;" if issue["severity"] == "error" else "&#9888;"
            html_parts.append(
                f'<span style="color:{color};">{icon} Line {issue["line"]}: {issue["message"]}</span>'
            )
        self.issues_area.setHtml("<br>".join(html_parts))

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _open_lua_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Lua Plugin", "lua_plugins", "Lua Files (*.lua);;All Files (*)"
        )
        if filepath:
            self._load_file(filepath)

    def _load_existing_plugin(self):
        self._load_file(self.plugin_path)
        self.stacked_widget.setCurrentIndex(1)

    def _load_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self._current_filename = os.path.basename(filepath)
            self.plugin_path = filepath
            self.setWindowTitle(f"Plugin Builder — {self._current_filename}")
            self._show_random_tip()
        except Exception as e:
            self.issues_area.setText(f"Error loading file: {e}")

    def _save_plugin(self):
        source = self.editor.toPlainText()

        # Run syntax check first
        issues = check_lua_syntax(source)
        errors = [i for i in issues if i["severity"] == "error"]
        if errors:
            self._check_syntax()
            reply = QMessageBox.question(
                self, "Syntax Errors",
                f"Found {len(errors)} error(s). Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Determine save path
        lua_dir = "lua_plugins"
        os.makedirs(lua_dir, exist_ok=True)

        if self.plugin_path and os.path.exists(self.plugin_path):
            save_path = self.plugin_path
        else:
            save_path = os.path.join(lua_dir, self._current_filename)

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Lua Plugin", save_path, "Lua Files (*.lua)"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(source)
            self.plugin_path = filepath
            self._current_filename = os.path.basename(filepath)
            self.setWindowTitle(f"Plugin Builder — {self._current_filename}")
            self.issues_area.setHtml(
                f'<span style="color: #98c379;">&#10004; Saved to {filepath}</span>'
            )
            self.accept()
        except Exception as e:
            self.issues_area.setHtml(
                f'<span style="color: #e06c75;">&#10006; Error saving: {e}</span>'
            )

    # ------------------------------------------------------------------
    # Tips
    # ------------------------------------------------------------------

    def _show_random_tip(self):
        tip = random.choice(LUA_TIPS)
        self.tip_label.setText(f"Tip: {tip}")
