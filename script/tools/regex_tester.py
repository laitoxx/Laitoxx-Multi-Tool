"""
Regex Tester — test a regular expression against a block of text.

Output
------
  - All matches with span (line:col) and captured groups
  - Named groups
  - Match count summary
  - Flags used

GUI  → regex_tester_tool({"pattern": r"\\d+", "text": "abc 123 def 456",
                           "flags": ["IGNORECASE", "MULTILINE"]})
CLI  → regex_tester_tool()
"""

import re

from ..shared_utils import Color

_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE":  re.MULTILINE,
    "DOTALL":     re.DOTALL,
    "VERBOSE":    re.VERBOSE,
    "ASCII":      re.ASCII,
}


def regex_tester_tool(data=None):
    if data:
        pattern     = data.get("pattern", "")
        text        = data.get("text", "")
        flag_names  = data.get("flags", [])
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
              f" Regex Tester\n")
        pattern = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Regex pattern: {Color.RESET}"
        )
        print(f"{Color.DARK_GRAY}  Flags (comma-separated): IGNORECASE, MULTILINE, DOTALL, VERBOSE, ASCII")
        flag_input = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Flags (leave empty for none): {Color.RESET}"
        ).strip()
        flag_names = [f.strip().upper() for f in flag_input.split(',') if f.strip()]

        print(f"{Color.DARK_GRAY}  Enter test text (type END on a new line to finish):")
        lines = []
        while True:
            ln = input()
            if ln.strip() == "END":
                break
            lines.append(ln)
        text = '\n'.join(lines)

    if not pattern:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No pattern provided.")
        return
    if not text:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No text provided.")
        return

    flags = re.RegexFlag(0)
    valid_flags = []
    for name in flag_names:
        if name in _FLAG_MAP:
            flags |= _FLAG_MAP[name]
            valid_flags.append(name)

    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Invalid regex: {e}")
        return

    lines_list = text.splitlines()
    line_starts = []
    pos = 0
    for line in lines_list:
        line_starts.append(pos)
        pos += len(line) + 1  # +1 for '\n'

    def _pos_to_linecol(idx: int):
        ln = 0
        for i, start in enumerate(line_starts):
            if start <= idx:
                ln = i
            else:
                break
        col = idx - line_starts[ln]
        return ln + 1, col + 1

    matches = list(compiled.finditer(text))

    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Regex Tester {Color.DARK_RED}]" + "─" * 26)
    print(f"{Color.DARK_GRAY}  Pattern:  {Color.WHITE}{pattern}")
    print(f"{Color.DARK_GRAY}  Flags:    {Color.WHITE}{', '.join(valid_flags) if valid_flags else 'none'}")
    print(f"{Color.DARK_RED}├─[ {Color.LIGHT_RED}Matches ({len(matches)}) {Color.DARK_RED}]" + "─" * 26)

    if not matches:
        print(f"{Color.DARK_GRAY}  - {Color.YELLOW}No matches found.")
    else:
        for i, m in enumerate(matches, 1):
            line_no, col_no = _pos_to_linecol(m.start())
            print(f"\n{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}{i}{Color.DARK_GRAY}]"
                  f"{Color.DARK_RED} line {line_no}:{col_no}"
                  f"  span ({m.start()},{m.end()})")
            print(f"{Color.DARK_GRAY}      match : {Color.WHITE}{repr(m.group(0))}")

            if m.lastindex:
                for gi in range(1, m.lastindex + 1):
                    gval = m.group(gi)
                    print(f"{Color.DARK_GRAY}      group {gi}: {Color.LIGHT_BLUE}{repr(gval)}")

            if m.groupdict():
                for gname, gval in m.groupdict().items():
                    print(f"{Color.DARK_GRAY}      {Color.LIGHT_RED}{gname}{Color.DARK_GRAY}: {Color.LIGHT_BLUE}{repr(gval)}")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
          f" {len(matches)} match(es) found.")
