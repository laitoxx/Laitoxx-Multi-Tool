"""Advanced username OSINT entry point for GUI and CLI usage."""

from __future__ import annotations

from .avatar_downloader import AvatarDownloader
from .checker import UsernameChecker
from .models import CATEGORY_ICONS, SITE_CATEGORIES, CheckResult, SiteEntry
from .nickname_generator import NicknameGenerator
from .portrait_generator import DigitalPortrait
from .site_db import SiteDB


def username_osint_tool(data=None):
    """
    CLI / TOOL_REGISTRY entry point.

    When called from the GUI with ``data`` dict, uses ``data["username"]``.
    When called from CLI (data is None), prompts for input.
    """
    if data and isinstance(data, dict):
        username = data.get("username", "").strip()
    elif data and isinstance(data, str):
        username = data.strip()
    else:
        username = input("Enter username: ").strip()

    if not username:
        print("[ERROR] Username cannot be empty.")
        return

    # Load the validated standard provider profile.
    db = SiteDB()
    db.load()
    sites = db.select("standard")
    print(f"\nChecking '{username}' on {len(sites)} platforms...\n")

    found_count = 0

    def _progress(checked, total, result):
        nonlocal found_count
        if result.is_found:
            found_count += 1
            print(f"  [FOUND] {result.site_name:<25}{result.url} [{result.status}]")
        print(
            f"\r  Progress: {checked}/{total}  Found: {found_count}",
            end="",
        )

    checker = UsernameChecker(sites, max_workers=50, progress_callback=_progress)
    results = checker.check_username(username)

    found = [r for r in results if r.is_found]
    print(f"\n\n{'-' * 50}")

    if not found:
        print(f"[INFO] No accounts found for '{username}'.")
        return

    # Generate the evidence summary.
    portrait = DigitalPortrait(username, results)
    print(portrait.to_text())

    # Generate candidate nickname variants without claiming identity.
    gen = NicknameGenerator(username, max_variants=50)
    variants = gen.generate_all()
    if len(variants) > 1:
        print("\n[INFO] Top similar nicknames to investigate:")
        for v in variants[:20]:
            if v.lower() != username.lower():
                print(f"    - {v}")


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
