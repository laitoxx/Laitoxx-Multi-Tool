"""Public entry point for the Text Cipher transformation engine."""

from __future__ import annotations

from laitoxx.features.utilities.shared_utils import Color

from .text_cipher_engine import SPECS, transform
from .text_cipher_tables import _LEET, _LEET_REV

_DEFAULT_OPTIONS = {
    "encoding": "utf-8",
    "separator": " ",
    "space": "%20",
    "line_break": 0,
    "quote": '"',
    "source_radix": 10,
    "radix": 36,
    "shift": 3,
    "a": 5,
    "b": 8,
    "key": "SECRET",
    "symbols": "AB",
    "columns": 3,
    "rails": 3,
    "style": "bold",
    "rotors": "I II III",
    "rings": "AAA",
    "positions": "AAA",
    "reflector": "B",
    "plugboard": "",
    "script": "romaji",
}


def _transform_all(text: str) -> str:
    """Render every applicable output, mirroring DenCode's result overview."""
    encoded, decoded = [], []
    for spec in SPECS:
        try:
            result = transform(spec.identifier, "encode", text, dict(_DEFAULT_OPTIONS))
            encoded.append(f"{spec.label}\n{result}")
        except Exception:
            pass
        if spec.reversible:
            try:
                result = transform(spec.identifier, "decode", text, dict(_DEFAULT_OPTIONS))
                decoded.append(f"{spec.label}\n{result}")
            except Exception:
                pass
    return "DECODED\n\n" + "\n\n".join(decoded) + "\n\nENCODED / TRANSFORMED\n\n" + "\n\n".join(encoded)


def _transform(mode: str, action: str, text: str, shift: int = 3, **options) -> str:
    """Apply one transformation or render the all-method overview."""
    if mode == "all":
        return _transform_all(text)
    if mode == "leet":
        table = _LEET if action.lower() == "encode" else _LEET_REV
        return "".join(table.get(char.lower() if action.lower() == "encode" else char, char) for char in text)
    options.setdefault("shift", shift)
    try:
        return transform(mode, action, text, options)
    except ValueError as error:
        if str(error).startswith("Unknown mode:"):
            return f"[unknown mode: {mode}]"
        return f"[error: {error}]"
    except Exception as error:
        return f"[error: {error}]"


def text_cipher_tool(data=None):
    if data:
        mode = str(data.get("mode", "")).strip().lower()
        action = str(data.get("action", "encode")).strip().lower()
        text = str(data.get("text", ""))
        options = dict(data.get("options", {}))
        for name in (
            "shift",
            "encoding",
            "separator",
            "space",
            "line_break",
            "quote",
            "source_radix",
            "radix",
            "a",
            "b",
            "key",
            "symbols",
            "columns",
            "rails",
        ):
            if name in data:
                options[name] = data[name]
    else:
        print(f"\n{Color.DARK_RED}Text Cipher\n")
        for index, spec in enumerate(SPECS, 1):
            print(f"  [{index}] {spec.category} / {spec.label}")
        try:
            mode = SPECS[int(input("Select mode: ").strip()) - 1].identifier
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
        action = input("Action [encode/decode]: ").strip().lower() or "encode"
        text = input("Enter text: ")
        options = {}
    if not text:
        print("No text provided.")
        return
    result = _transform(mode, action, text, **options)
    print(f"\nResult · {mode} · {action}\n{result}")
