"""Stable operation catalog and dispatch."""

from __future__ import annotations

import codecs
from collections.abc import Callable
from dataclasses import dataclass

from ..text_cipher_tables import _MORSE_DEC, _MORSE_ENC
from . import ciphers, dates_colors, numbers_hashes, string_codecs, symbol_codecs, text_ops

Handler = Callable[[str, str, dict], str]


@dataclass(frozen=True, slots=True)
class TransformSpec:
    identifier: str
    label: str
    category: str
    reversible: bool = False
    parameters: tuple[str, ...] = ()


def _morse(action: str, text: str, _options: dict) -> str:
    if action == "encode":
        return " ".join("/" if char == " " else _MORSE_ENC.get(char.upper(), "?") for char in text)
    return " ".join("".join(_MORSE_DEC.get(code, "?") for code in word.split()) for word in text.strip().split(" / "))


def _simple(mode: str) -> Handler:
    return lambda _action, text, _options: text_ops.case(mode, text)


HANDLERS: dict[str, Handler] = {
    "binary": string_codecs.binary,
    "hex": string_codecs.hexadecimal,
    "html": string_codecs.html_escape,
    "url": string_codecs.url,
    "punycode": string_codecs.punycode,
    "base32": lambda action, text, options: string_codecs.base_codec("base32", action, text, options),
    "base45": string_codecs.base45,
    "base64": lambda action, text, options: string_codecs.base_codec("base64", action, text, options),
    "ascii85": lambda action, text, options: string_codecs.base_codec("ascii85", action, text, options),
    "quoted_printable": string_codecs.quoted_printable,
    "unicode_escape": string_codecs.unicode_escape,
    "literal": string_codecs.literal,
    "morse": _morse,
    "braille": symbol_codecs.braille,
    "hieroglyphs": symbol_codecs.hieroglyphs,
    "styled": symbol_codecs.styled,
    "kana_romaji": symbol_codecs.kana_romaji,
    "jis_keyboard": symbol_codecs.jis_keyboard,
    "nfc": lambda action, text, options: string_codecs.normalize("NFC", action, text, options),
    "nfd": lambda action, text, options: string_codecs.normalize("NFD", action, text, options),
    "nfkc": lambda action, text, options: string_codecs.normalize("NFKC", action, text, options),
    "nfkd": lambda action, text, options: string_codecs.normalize("NFKD", action, text, options),
    "halfwidth": lambda action, text, options: string_codecs.width("halfwidth", action, text, options),
    "fullwidth": lambda action, text, options: string_codecs.width("fullwidth", action, text, options),
    "rot13": lambda _action, text, _options: codecs.encode(text, "rot_13"),
    "rot18": lambda _action, text, _options: ciphers.rot18(text),
    "rot47": lambda _action, text, _options: ciphers.rot47(text),
    "atbash": lambda _action, text, _options: ciphers.atbash(text),
    "caesar": lambda action, text, options: ciphers.caesar(
        text, int(options.get("shift", 3)) * (1 if action == "encode" else -1)
    ),
    "affine": ciphers.affine,
    "vigenere": ciphers.vigenere,
    "playfair": ciphers.playfair,
    "enigma": ciphers.enigma,
    "baconian": ciphers.baconian,
    "rail_fence": ciphers.rail_fence,
    "scytale": ciphers.scytale,
    "roman": lambda action, text, _options: numbers_hashes.roman(action, text),
    "fraction": lambda _action, text, _options: numbers_hashes.fraction(text),
    "english_number": lambda action, text, _options: numbers_hashes.english_number(action, text),
    "kanji_number": lambda action, text, _options: numbers_hashes.kanji_number(action, text),
    "unix_time": lambda action, text, _options: numbers_hashes.unix_time(action, text),
    "crc32": string_codecs.crc32,
}

for operation in (
    "upper_camel",
    "lower_camel",
    "upper_snake",
    "lower_snake",
    "upper_kebab",
    "lower_kebab",
    "upper",
    "lower",
    "swapcase",
    "capitalize",
    "alternating",
    "reverse",
    "line_sort",
    "line_sort_desc",
    "dedupe_lines",
):
    HANDLERS[operation] = _simple(operation)
for operation in ("num_bin", "num_oct", "num_dec", "num_hex", "num_nary"):
    HANDLERS[operation] = lambda _action, text, options, selected=operation: numbers_hashes.number(
        selected, text, options
    )
for operation in ("md2", "md5", "sha1", "sha256", "sha384", "sha512", "sha3", "sha3_256"):
    HANDLERS[operation] = lambda _action, text, options, selected=operation: numbers_hashes.digest(
        selected, text, options
    )
for operation in ("unix_time", "w3c_date", "iso_date", "iso_week", "iso_ordinal", "rfc2822", "ctime", "japanese_era"):
    HANDLERS[operation] = lambda action, text, options, selected=operation: dates_colors.date_format(
        selected, action, text, options
    )
for operation in ("color_name", "rgb_hex", "rgb", "hsl", "hwb", "lab", "lch", "oklab", "oklch", "cmyk"):
    HANDLERS[operation] = lambda action, text, options, selected=operation: dates_colors.color(
        selected, action, text, options
    )


def _spec(identifier: str, label: str, category: str, reversible: bool = False, *parameters: str) -> TransformSpec:
    return TransformSpec(identifier, label, category, reversible, parameters)


SPECS = [
    _spec("binary", "Binary String", "String encoding", True, "encoding", "separator"),
    _spec("hex", "Hexadecimal String", "String encoding", True, "encoding", "separator"),
    _spec("html", "HTML Escape", "String encoding", True),
    _spec("url", "URL Encoding", "String encoding", True, "encoding", "space"),
    _spec("punycode", "Punycode IDN", "String encoding", True),
    _spec("base32", "Base32", "String encoding", True, "encoding"),
    _spec("base45", "Base45", "String encoding", True, "encoding"),
    _spec("base64", "Base64", "String encoding", True, "encoding", "line_break"),
    _spec("ascii85", "Ascii85", "String encoding", True, "encoding"),
    _spec("quoted_printable", "Quoted-printable", "String encoding", True, "encoding"),
    _spec("unicode_escape", "Unicode Escape", "String encoding", True),
    _spec("literal", "String Literal", "String encoding", True, "quote"),
    _spec("morse", "Morse Code", "String encoding", True),
    _spec("braille", "Braille (UEB Grade 1)", "String encoding", True),
    _spec("hieroglyphs", "Egyptian Hieroglyphs", "String encoding", True),
    _spec("styled", "Unicode Styled Text", "Text", False, "style"),
    _spec("kana_romaji", "Japanese Kana / Romaji", "Text", False, "script"),
    *[
        _spec(identifier, label, "Text")
        for identifier, label in (
            ("upper_camel", "UpperCamelCase"),
            ("lower_camel", "lowerCamelCase"),
            ("upper_snake", "UPPER_SNAKE_CASE"),
            ("lower_snake", "lower_snake_case"),
            ("upper_kebab", "UPPER-KEBAB-CASE"),
            ("lower_kebab", "lower-kebab-case"),
            ("upper", "Upper Case"),
            ("lower", "Lower Case"),
            ("swapcase", "Swap Case"),
            ("capitalize", "Capitalize"),
            ("alternating", "aLtErNaTiNg CaPs"),
            ("halfwidth", "Half Width"),
            ("fullwidth", "Full Width"),
            ("nfc", "Unicode NFC"),
            ("nfd", "Unicode NFD"),
            ("nfkc", "Unicode NFKC"),
            ("nfkd", "Unicode NFKD"),
            ("reverse", "Reverse"),
            ("line_sort", "Line Sort (ascending)"),
            ("line_sort_desc", "Line Sort (descending)"),
            ("dedupe_lines", "Remove Duplicate Lines"),
        )
    ],
    *[
        _spec(identifier, label, "Numbers", identifier in {"roman", "english_number", "kanji_number"}, *(parameters))
        for identifier, label, parameters in (
            ("num_dec", "Num to Dec", ("source_radix",)),
            ("num_bin", "Num to Bin", ("source_radix",)),
            ("num_oct", "Num to Oct", ("source_radix",)),
            ("num_hex", "Num to Hex", ("source_radix",)),
            ("num_nary", "Num to N-ary", ("source_radix", "radix")),
            ("fraction", "Num to Fraction", ()),
            ("english_number", "Num / English Words", ()),
            ("kanji_number", "Num / Kanji", ()),
            ("roman", "Roman Numerals", ()),
        )
    ],
    *[
        _spec(identifier, label, "Date", identifier == "unix_time")
        for identifier, label in (
            ("unix_time", "UNIX Time / ISO8601"),
            ("w3c_date", "W3C-DTF Date"),
            ("iso_date", "ISO8601 Date"),
            ("iso_week", "ISO8601 Week Date"),
            ("iso_ordinal", "ISO8601 Ordinal Date"),
            ("rfc2822", "RFC2822 Date"),
            ("ctime", "ctime Date"),
            ("japanese_era", "Japanese Era"),
        )
    ],
    *[
        _spec(identifier, label, "Color")
        for identifier, label in (
            ("color_name", "Color Name"),
            ("rgb_hex", "RGB Color (Hex)"),
            ("rgb", "RGB Color"),
            ("hsl", "HSL Color"),
            ("hwb", "HWB Color"),
            ("lab", "Lab Color"),
            ("lch", "LCH Color"),
            ("oklab", "Oklab Color"),
            ("oklch", "Oklch Color"),
            ("cmyk", "CMYK Color"),
        )
    ],
    _spec("caesar", "Caesar", "Cipher", True, "shift"),
    _spec("rot13", "ROT13", "Cipher"),
    _spec("rot18", "ROT18", "Cipher"),
    _spec("rot47", "ROT47", "Cipher"),
    _spec("atbash", "Atbash", "Cipher"),
    _spec("jis_keyboard", "JIS Keyboard (Mikaka)", "Cipher", False, "mode"),
    _spec("affine", "Affine", "Cipher", True, "a", "b"),
    _spec("vigenere", "Vigenere", "Cipher", True, "key"),
    _spec("playfair", "Playfair", "Cipher", True, "key"),
    _spec("baconian", "Baconian", "Cipher", True, "symbols"),
    _spec("enigma", "Enigma I", "Cipher", False, "rotors", "rings", "positions", "reflector", "plugboard"),
    _spec("scytale", "Scytale", "Cipher", True, "columns"),
    _spec("rail_fence", "Rail Fence", "Cipher", True, "rails"),
    *[
        _spec(identifier, label, "Hash", False, *("hash_function",) if identifier == "sha3" else ())
        for identifier, label in (
            ("md2", "MD2"),
            ("md5", "MD5"),
            ("sha1", "SHA-1"),
            ("sha256", "SHA-256"),
            ("sha384", "SHA-384"),
            ("sha512", "SHA-512"),
            ("sha3", "SHA-3"),
            ("crc32", "CRC32"),
        )
    ],
]
SPEC_BY_ID = {spec.identifier: spec for spec in SPECS}


def transform(identifier: str, action: str, text: str, options: dict | None = None) -> str:
    handler = HANDLERS.get(identifier)
    if handler is None:
        raise ValueError(f"Unknown mode: {identifier}")
    return handler(action.lower(), text, options or {})
