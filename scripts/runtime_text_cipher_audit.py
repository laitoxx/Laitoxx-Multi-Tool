"""Round-trip and GUI audit for the DenCode-style transformer."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from laitoxx.features.utilities.text_cipher import _transform
from laitoxx.features.utilities.text_cipher_engine import SPECS, transform
from laitoxx.interfaces.gui.dialog_text_cipher import TextCipherDialog


def roundtrips() -> None:
    sample = "Hello, мир!"
    for mode in (
        "binary",
        "hex",
        "html",
        "url",
        "base32",
        "base45",
        "base64",
        "ascii85",
        "quoted_printable",
        "literal",
    ):
        encoded = transform(mode, "encode", sample, {"encoding": "utf-8"})
        assert transform(mode, "decode", encoded, {"encoding": "utf-8"}) == sample, mode
    assert transform("punycode", "decode", transform("punycode", "encode", "пример.рф")) == "пример.рф"
    assert transform("morse", "decode", transform("morse", "encode", "HELLO WORLD")) == "HELLO WORLD"
    assert transform("braille", "decode", transform("braille", "encode", "Hello 123!")) == "Hello 123!"
    assert transform("hieroglyphs", "encode", "AB") == "𓄿𓃀"
    print("PASS string_roundtrips")


def ciphers_and_numbers() -> None:
    for mode, options, sample in (
        ("caesar", {"shift": 19}, "Attack at dawn!"),
        ("affine", {"a": 5, "b": 8}, "AFFINE CIPHER"),
        ("vigenere", {"key": "SECRET"}, "ATTACK AT DAWN"),
        ("rail_fence", {"rails": 3}, "WEAREDISCOVEREDFLEEATONCE"),
        ("scytale", {"columns": 4}, "SCYTALE CIPHER"),
    ):
        encoded = transform(mode, "encode", sample, options)
        assert transform(mode, "decode", encoded, options) == sample, mode
    assert transform(
        "playfair", "decode", transform("playfair", "encode", "HIDETHEGOLD", {"key": "PLAYFAIR"}), {"key": "PLAYFAIR"}
    ).startswith("HIDETHEGOLD")
    assert transform("num_hex", "encode", "255", {"source_radix": 10}) == "FF"
    assert transform("num_dec", "encode", "FF", {"source_radix": 16}) == "255"
    assert transform("roman", "decode", transform("roman", "encode", "2026")) == "2026"
    assert transform("unix_time", "decode", "0") == "1970-01-01T00:00:00Z"
    assert transform("md2", "encode", "abc") == "da853b0d3f88d99b30283a69e6ded6bb"
    mikaka = transform("jis_keyboard", "encode", "this is a secret message")
    assert mikaka == "かくにと にと ち といそすいか もいととちきい"
    assert transform("jis_keyboard", "encode", mikaka) == "this is a secret message"
    enigma = transform("enigma", "encode", "HELLOWORLD")
    assert transform("enigma", "decode", enigma) == "HELLOWORLD"
    assert transform("rgb_hex", "encode", "rebeccapurple") == "#663399"
    assert transform("english_number", "decode", transform("english_number", "encode", "2026")) == "2026"
    assert transform("kanji_number", "decode", transform("kanji_number", "encode", "2026")) == "2026"
    print("PASS ciphers_and_numbers")


def facade_and_gui() -> None:
    assert len(SPECS) >= 60
    assert _transform("rot13", "encode", _transform("rot13", "encode", "Hello")) == "Hello"
    assert _transform("hex", "decode", "not hex").startswith("[error:")
    overview = _transform("all", "encode", "Hello")
    assert "DECODED" in overview and "ENCODED / TRANSFORMED" in overview and "Base64" in overview
    app = QApplication.instance() or QApplication([])
    dialog = TextCipherDialog()
    assert dialog.windowTitle() == "Text Cipher"
    dialog.search_input.setText("base64")
    dialog.text_input.setPlainText("Hello")
    QTest.qWait(180)
    app.processEvents()
    assert dialog.mode_combo.currentData() == "base64"
    assert dialog.preview.toPlainText() == "SGVsbG8="
    dialog._swap_direction()
    QTest.qWait(180)
    assert dialog.text_input.toPlainText() == "SGVsbG8="
    assert dialog.preview.toPlainText() == "Hello"
    dialog.close()
    print("PASS facade_and_gui")


def main() -> int:
    roundtrips()
    ciphers_and_numbers()
    facade_and_gui()
    print(f"text cipher runtime audit passed: modes={len(SPECS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
