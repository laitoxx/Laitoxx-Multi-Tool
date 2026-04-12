"""
Password Generator — cryptographically secure random passwords.

Options
-------
  length        — number of characters (default 16)
  count         — how many passwords to generate (default 1)
  use_upper     — include uppercase letters A-Z
  use_lower     — include lowercase letters a-z
  use_digits    — include digits 0-9
  use_symbols   — include symbols (!@#$%^&*...)
  custom_chars  — if set, ONLY these characters are used (overrides use_* flags)
  exclude_chars — characters to remove from the final pool (applied last)

GUI  → password_generator_tool({
           "length": 20, "count": 5,
           "use_upper": True, "use_lower": True,
           "use_digits": True, "use_symbols": False,
           "custom_chars": "",
           "exclude_chars": "O0lI1",
       })
CLI  → password_generator_tool()
"""

import secrets
import string as _string

from ..shared_utils import Color

_UPPER   = _string.ascii_uppercase
_LOWER   = _string.ascii_lowercase
_DIGITS  = _string.digits
_SYMBOLS = "!@#$%^&*()-_=+[]{}|;:',.<>?/`~"


def _build_pool(use_upper, use_lower, use_digits, use_symbols,
                custom_chars, exclude_chars) -> str:
    if custom_chars:
        pool = custom_chars
    else:
        pool = ""
        if use_upper:   pool += _UPPER
        if use_lower:   pool += _LOWER
        if use_digits:  pool += _DIGITS
        if use_symbols: pool += _SYMBOLS

    if exclude_chars:
        pool = ''.join(c for c in pool if c not in exclude_chars)

    # Deduplicate but preserve order
    seen = set()
    deduped = []
    for c in pool:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return ''.join(deduped)


def _generate_one(pool: str, length: int) -> str:
    return ''.join(secrets.choice(pool) for _ in range(length))


def password_generator_tool(data=None):
    if data:
        length        = int(data.get("length", 16))
        count         = int(data.get("count", 1))
        use_upper     = bool(data.get("use_upper", True))
        use_lower     = bool(data.get("use_lower", True))
        use_digits    = bool(data.get("use_digits", True))
        use_symbols   = bool(data.get("use_symbols", True))
        custom_chars  = data.get("custom_chars", "").strip()
        exclude_chars = data.get("exclude_chars", "").strip()
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
              f" Password Generator\n")
        try:
            length = int(input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                f" Length [{Color.WHITE}16{Color.DARK_RED}]: "
            ).strip() or 16)
            count = int(input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                f" Count [{Color.WHITE}1{Color.DARK_RED}]: "
            ).strip() or 1)
        except ValueError:
            length, count = 16, 1

        custom_chars = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Only these chars (leave empty for presets): {Color.RESET}"
        ).strip()

        use_upper = use_lower = use_digits = use_symbols = True
        if not custom_chars:
            def _ask(q):
                return input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                             f" {q} [Y/n]: {Color.RESET}").strip().lower() != 'n'
            use_upper   = _ask("Include uppercase (A-Z)?")
            use_lower   = _ask("Include lowercase (a-z)?")
            use_digits  = _ask("Include digits (0-9)?")
            use_symbols = _ask("Include symbols (!@#...)?")

        exclude_chars = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Exclude chars (e.g. O0lI1, leave empty for none): {Color.RESET}"
        ).strip()

    pool = _build_pool(use_upper, use_lower, use_digits, use_symbols,
                       custom_chars, exclude_chars)

    if not pool:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Character pool is empty — check your settings.")
        return

    if length < 1:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Length must be at least 1.")
        return

    count = max(1, min(count, 100))

    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Password Generator {Color.DARK_RED}]"
          + "─" * 20)
    print(f"{Color.DARK_GRAY}  Pool size: {Color.WHITE}{len(pool)} chars"
          f"  {Color.DARK_GRAY}Length: {Color.WHITE}{length}"
          f"  {Color.DARK_GRAY}Count: {Color.WHITE}{count}")
    if exclude_chars:
        print(f"{Color.DARK_GRAY}  Excluded:  {Color.YELLOW}{exclude_chars}")
    print(f"{Color.DARK_RED}├" + "─" * 40)

    passwords = [_generate_one(pool, length) for _ in range(count)]
    for pw in passwords:
        print(f"{Color.DARK_GRAY}  {Color.WHITE}{pw}")

    print(f"{Color.DARK_RED}└" + "─" * 45)
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
          f" {count} password(s) generated.")
