"""
Lua Plugin Builder - code editor with syntax highlighting, code snippets,
syntax checking, and OS-dependent template generation.
"""

import re

# ============================================================================
# Lua Syntax Highlighter
# ============================================================================


def check_lua_syntax(source: str) -> list[dict]:
    """
    Check Lua source code for common syntax issues.
    Returns a list of {line, message, severity} dicts.
    """
    issues = []
    lines = source.split("\n")

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
        for w in re.findall(r"\b(function|if|for|while|repeat|do)\b", code_no_strings):
            if w == "do":
                if not re.search(r"\b(for|while)\b", code_no_strings):
                    openers_on_line += 1
            elif w == "if":
                if not re.search(r"\belseif\b", code_no_strings):
                    openers_on_line += 1
            else:
                openers_on_line += 1

        closers_on_line = len(re.findall(r"\bend\b", code_no_strings))
        if re.search(r"\buntil\b", code_no_strings):
            closers_on_line += 1

        # For single-line blocks (e.g. "if x then return end"), pairs cancel out
        net = openers_on_line - closers_on_line
        if net > 0:
            block_openers += net
        elif net < 0:
            block_closers += abs(net)

        # Parentheses / brackets balance per line
        paren_depth += code.count("(") - code.count(")")
        bracket_depth += code.count("{") - code.count("}")

        # Check for common mistakes (use code_no_strings to avoid false positives)

        # Assignment in condition (= instead of ==)
        if_match = re.match(r".*\bif\b\s+(.+?)\s+\bthen\b", code_no_strings)
        if if_match:
            cond = if_match.group(1)
            if re.search(r"(?<!=)(?<!~)(?<!<)(?<!>)=(?!=)", cond):
                issues.append(
                    {
                        "line": i,
                        "message": "Possible assignment in condition (use '==' for comparison)",
                        "severity": "warning",
                    }
                )

        # Missing 'then' after 'if'
        if re.search(r"\bif\b", code_no_strings) and not re.search(r"\bthen\b", code_no_strings):
            if not code_no_strings.rstrip().endswith(",") and not code_no_strings.rstrip().endswith("("):
                issues.append(
                    {
                        "line": i,
                        "message": "Missing 'then' after 'if' condition",
                        "severity": "error",
                    }
                )

        # 'elseif' without 'then'
        if re.search(r"\belseif\b", code_no_strings) and not re.search(r"\bthen\b", code_no_strings):
            issues.append(
                {
                    "line": i,
                    "message": "Missing 'then' after 'elseif'",
                    "severity": "error",
                }
            )

        # Using '!=' instead of '~='
        if "!=" in code_no_strings:
            issues.append(
                {
                    "line": i,
                    "message": "Lua uses '~=' for not-equal, not '!='",
                    "severity": "error",
                }
            )

        # Using '++' or '+='
        if "++" in code_no_strings or "+=" in code_no_strings or "-=" in code_no_strings:
            issues.append(
                {
                    "line": i,
                    "message": "Lua doesn't support '++', '+=', '-='. Use: x = x + 1",
                    "severity": "error",
                }
            )

        # Using '//' for comments
        if code_no_strings.lstrip().startswith("//"):
            issues.append(
                {
                    "line": i,
                    "message": "Lua uses '--' for comments, not '//'",
                    "severity": "error",
                }
            )

        # Empty function body
        if re.match(r"\s*function\b.*\bend\b\s*$", code_no_strings):
            if "return" not in code_no_strings and "print" not in code_no_strings:
                issues.append(
                    {
                        "line": i,
                        "message": "Empty function body - did you mean to add code?",
                        "severity": "warning",
                    }
                )

        # host. instead of host:
        if "host." in code_no_strings and "host:" not in code_no_strings:
            if re.search(r"host\.\w+\s*\(", code_no_strings):
                issues.append(
                    {
                        "line": i,
                        "message": "Use 'host:method()' (colon syntax), not 'host.method()'",
                        "severity": "warning",
                    }
                )

    # Check final balances
    if block_openers > block_closers:
        diff = block_openers - block_closers
        issues.append(
            {
                "line": len(lines),
                "message": f"Missing {diff} 'end' statement(s) - unclosed block(s)",
                "severity": "error",
            }
        )
    elif block_closers > block_openers:
        diff = block_closers - block_openers
        issues.append(
            {
                "line": len(lines),
                "message": f"Extra {diff} 'end' statement(s) - no matching block opener",
                "severity": "error",
            }
        )

    if paren_depth != 0:
        issues.append(
            {
                "line": len(lines),
                "message": f"Unbalanced parentheses (depth: {paren_depth})",
                "severity": "error",
            }
        )

    if bracket_depth != 0:
        issues.append(
            {
                "line": len(lines),
                "message": f"Unbalanced curly braces (depth: {bracket_depth})",
                "severity": "error",
            }
        )

    # Check for required plugin structure
    if "return plugin" not in source and "return plugin\n" not in source:
        if source.strip() and "local plugin" in source:
            issues.append(
                {
                    "line": len(lines),
                    "message": "Missing 'return plugin' at the end of the file",
                    "severity": "warning",
                }
            )

    return issues
