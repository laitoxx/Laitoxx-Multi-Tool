"""Runtime audit for the combined Telegram → TONgue workflow."""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from laitoxx.features.osint.tongue import service
from laitoxx.features.osint.tongue.service import TongueOptions, detect_target_kind
from laitoxx.features.osint.tongue.telegram_discovery import (
    discover_telegram,
    discovery_report,
    normalize_telegram_target,
)
from laitoxx.interfaces.gui.tongue_window import TongueWindow


class FakeWeb:
    def get_text(self, _url):
        address = "0:" + "A" * 64
        return (
            "<html><head><meta property='og:title' content='Demo User'>"
            "<meta property='og:description' content='Public profile'></head>"
            f"<body><a href='https://t.me/nft/PlushPepe-123'>Gift</a>{address}</body></html>",
            "https://t.me/demo_user",
            200,
        )


def discovery_boundaries() -> None:
    assert normalize_telegram_target("@demo_user") == ("demo_user", "username")
    assert normalize_telegram_target("https://t.me/demo_user") == ("demo_user", "username")
    assert normalize_telegram_target("123456") == ("123456", "id")
    assert detect_target_kind("@demo_user") == "telegram"
    assert detect_target_kind("https://t.me/demo_user") == "telegram"
    assert detect_target_kind("https://t.me/nft/PlushPepe-123") == "gift"

    import laitoxx.features.osint.tongue.telegram_discovery as module

    original = module._paketlib_lookup
    module._paketlib_lookup = lambda _username: ({"name": "Demo User"}, None)
    try:
        found = discover_telegram("@demo_user", web=FakeWeb())
    finally:
        module._paketlib_lookup = original
    assert found["profile"]["title"] == "Demo User"
    assert found["gift_candidates"] == ["plushpepe-123"]
    assert found["ton_candidates"][0]["address"].startswith("0:")
    report = discovery_report(found)
    assert len(report["graph"]["nodes"]) == 3
    assert len(report["graph"]["edges"]) == 2
    print("PASS telegram_discovery_boundaries")


def telegram_only_investigation() -> None:
    fake = {
        "query": "@demo_user",
        "target": "demo_user",
        "kind": "username",
        "status": "found",
        "message": "Public Telegram discovery completed",
        "profile": {"username": "@demo_user", "title": "Demo User"},
        "gift_candidates": [],
        "ton_candidates": [],
        "sources": [{"name": "fixture", "status": "fetched"}],
    }
    original = service.discover_telegram
    service.discover_telegram = lambda *_args, **_kwargs: fake
    try:
        with tempfile.TemporaryDirectory() as directory:
            report = service.run_investigation(
                TongueOptions(target="@demo_user", output_dir=directory, recursive=False)
            )
    finally:
        service.discover_telegram = original
    assert report["tongue"]["target_kind"] == "telegram"
    assert report["summary"]["seed"] == "@demo_user"
    print("PASS telegram_only_investigation")


def gui_pivot() -> None:
    app = QApplication.instance() or QApplication([])
    window = TongueWindow()
    assert window.kind_combo.findData("telegram") >= 0
    window.report = discovery_report(
        {
            "target": "demo_user",
            "status": "found",
            "profile": {"username": "@demo_user", "title": "Demo User"},
            "gift_candidates": ["plushpepe-123"],
            "ton_candidates": [],
            "sources": [],
        }
    )
    window._populate_report()
    gift_row = next(
        row for row in range(window.entities.rowCount()) if window.entities.item(row, 0).text() == "telegram_gift"
    )
    window._investigate_entity_row(gift_row, 1)
    assert window.target_input.text() == "plushpepe-123"
    assert window.kind_combo.currentData() == "gift"
    window.close()
    app.processEvents()
    print("PASS gui_pivot")


def main() -> int:
    discovery_boundaries()
    telegram_only_investigation()
    gui_pivot()
    print("combined Telegram and TONgue runtime audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
