"""
username_osint — Advanced username OSINT package for LAITOXX.

Entry point for TOOL_REGISTRY integration and CLI usage.
"""
from __future__ import annotations

import os
import sys

# Ensure parent packages are importable when running from CLI
_pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from .models import CheckResult, SiteEntry, SITE_CATEGORIES, CATEGORY_ICONS
from .site_db import SiteDB
from .checker import UsernameChecker
from .nickname_generator import NicknameGenerator
from .portrait_generator import DigitalPortrait
from .avatar_downloader import AvatarDownloader


def username_osint_tool(data=None):
    """
    CLI / TOOL_REGISTRY entry point.

    When called from the GUI with ``data`` dict, uses ``data["username"]``.
    When called from CLI (data is None), prompts for input.
    """
    from script.shared_utils import Color

    if data and isinstance(data, dict):
        username = data.get("username", "").strip()
    elif data and isinstance(data, str):
        username = data.strip()
    else:
        username = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}\u26e7{Color.DARK_GRAY}]"
            f"{Color.DARK_RED} Enter username: {Color.RESET}"
        ).strip()

    if not username:
        print(f"{Color.DARK_GRAY}[{Color.RED}\u2716{Color.DARK_GRAY}]{Color.RED} Username cannot be empty.")
        return

    # Load site database
    db = SiteDB()
    sites = db.load()
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}\u26e7{Color.DARK_GRAY}]"
        f"{Color.LIGHT_BLUE} Checking '{username}' on {len(sites)} platforms...\n"
    )

    found_count = 0

    def _progress(checked, total, result):
        nonlocal found_count
        if result.is_found:
            found_count += 1
            print(
                f"  {Color.LIGHT_GREEN}\u2714{Color.WHITE} {result.site_name:<25}"
                f"{Color.LIGHT_BLUE}{result.url}"
            )
        print(
            f"\r{Color.DARK_GRAY}  Progress: {checked}/{total}  "
            f"Found: {found_count}",
            end="",
        )

    checker = UsernameChecker(sites, max_workers=50, progress_callback=_progress)
    results = checker.check_username(username)

    found = [r for r in results if r.is_found]
    print(f"\n\n{Color.DARK_GRAY}{'─' * 50}")

    if not found:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}\u2716{Color.DARK_GRAY}]{Color.RED}"
            f" No accounts found for '{username}'."
        )
        return

    # Generate portrait
    portrait = DigitalPortrait(username, results)
    print(portrait.to_text())

    # Generate nickname variants
    gen = NicknameGenerator(username, max_variants=50)
    variants = gen.generate_all()
    if len(variants) > 1:
        print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}\u2139{Color.DARK_GRAY}]"
              f"{Color.WHITE} Top similar nicknames to investigate:")
        for v in variants[:20]:
            if v.lower() != username.lower():
                print(f"    {Color.DARK_GRAY}\u2022 {Color.WHITE}{v}")


__all__ = [
    "username_osint_tool",
    "CheckResult",
    "SiteEntry",
    "SiteDB",
    "UsernameChecker",
    "NicknameGenerator",
    "DigitalPortrait",
    "AvatarDownloader",
    "SITE_CATEGORIES",
    "CATEGORY_ICONS",
]
