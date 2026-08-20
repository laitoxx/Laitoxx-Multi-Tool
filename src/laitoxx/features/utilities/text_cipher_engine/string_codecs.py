"""Byte/string encodings and Unicode transformations."""

from __future__ import annotations

import ast
import base64
import binascii
import html
import quopri
import re
import unicodedata
from urllib.parse import quote_from_bytes, unquote_to_bytes

BASE45_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def _encoding(options: dict) -> str:
    selected = str(options.get("encoding", "utf-8")).lower()
    return {"utf-16": "utf-16-be", "utf-32": "utf-32-be"}.get(selected, selected)


def binary(action: str, text: str, options: dict) -> str:
    encoding = _encoding(options)
    if action == "encode":
        separator = str(options.get("separator", " "))
        return separator.join(f"{byte:08b}" for byte in text.encode(encoding))
    bits = "".join(character for character in text if character in "01")
    if not bits or len(bits) % 8:
        raise ValueError("Binary input must contain complete 8-bit bytes")
    return bytes(int(bits[index : index + 8], 2) for index in range(0, len(bits), 8)).decode(encoding)


def hexadecimal(action: str, text: str, options: dict) -> str:
    encoding = _encoding(options)
    if action == "encode":
        separator = str(options.get("separator", ""))
        case = str(options.get("case", "lower"))
        output = separator.join(f"{byte:02x}" for byte in text.encode(encoding))
        return output.upper() if case == "upper" else output
    cleaned = "".join(character for character in text if character in "0123456789abcdefABCDEF")
    if not cleaned:
        raise ValueError("Hex input contains no hexadecimal bytes")
    return bytes.fromhex(cleaned).decode(encoding)


def html_escape(action: str, text: str, options: dict) -> str:
    if action == "decode":
        return html.unescape(text)
    quote = bool(options.get("quotes", True))
    return html.escape(text, quote=quote)


def url(action: str, text: str, options: dict) -> str:
    encoding = _encoding(options)
    if action == "encode":
        result = quote_from_bytes(text.encode(encoding), safe="-._~")
        return result.replace("%20", "+") if options.get("space") == "+" else result
    source = text.replace("+", " ") if options.get("space") == "+" else text
    return unquote_to_bytes(source).decode(encoding)


def punycode(action: str, text: str, _options: dict) -> str:
    labels = text.split(".")
    if action == "encode":
        return ".".join(label.encode("idna").decode("ascii") for label in labels)
    return ".".join(label.encode("ascii").decode("idna") for label in labels)


def base_codec(kind: str, action: str, text: str, options: dict) -> str:
    data = text.encode(_encoding(options))
    if action == "encode":
        functions = {
            "base32": base64.b32encode,
            "base64": base64.b64encode,
            "ascii85": base64.a85encode,
        }
        output = functions[kind](data).decode("ascii")
        width = int(options.get("line_break", 0) or 0)
        return "\n".join(output[i : i + width] for i in range(0, len(output), width)) if width else output
    cleaned = "".join(text.split())
    if kind == "base32":
        raw = base64.b32decode(cleaned + "=" * (-len(cleaned) % 8), casefold=True)
    elif kind == "base64":
        raw = base64.b64decode(cleaned + "=" * (-len(cleaned) % 4), validate=True)
    else:
        raw = base64.a85decode(cleaned, adobe=cleaned.startswith("<~"))
    return raw.decode(_encoding(options))


def base45(action: str, text: str, options: dict) -> str:
    if action == "encode":
        source = text.encode(_encoding(options))
        output = []
        for index in range(0, len(source), 2):
            chunk = source[index : index + 2]
            value = chunk[0] if len(chunk) == 1 else chunk[0] * 256 + chunk[1]
            output.extend((BASE45_ALPHABET[value % 45], BASE45_ALPHABET[(value // 45) % 45]))
            if len(chunk) == 2:
                output.append(BASE45_ALPHABET[value // 2025])
        return "".join(output)
    values = [BASE45_ALPHABET.index(character) for character in text]
    output = bytearray()
    index = 0
    while index < len(values):
        size = 3 if len(values) - index >= 3 else 2
        if size < 2:
            raise ValueError("Invalid Base45 length")
        value = values[index] + values[index + 1] * 45 + (values[index + 2] * 2025 if size == 3 else 0)
        if value > (65535 if size == 3 else 255):
            raise ValueError("Invalid Base45 value")
        output.extend(value.to_bytes(2 if size == 3 else 1, "big"))
        index += size
    return output.decode(_encoding(options))


def quoted_printable(action: str, text: str, options: dict) -> str:
    encoding = _encoding(options)
    if action == "encode":
        return quopri.encodestring(text.encode(encoding), quotetabs=True).decode("ascii")
    return quopri.decodestring(text).decode(encoding)


def unicode_escape(action: str, text: str, options: dict) -> str:
    if action == "decode":
        pattern = r"\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|[\\'\"abfnrtv0])"
        return re.sub(pattern, lambda match: bytes(match.group(), "ascii").decode("unicode_escape"), text)
    style = options.get("format", "python")
    output = []
    for character in text:
        code = ord(character)
        if 32 <= code < 127 and character != "\\":
            output.append(character)
        elif style == "codepoint":
            output.append(f"U+{code:04X}")
        else:
            output.append(f"\\u{code:04x}" if code <= 0xFFFF else f"\\U{code:08x}")
    return "".join(output)


def literal(action: str, text: str, options: dict) -> str:
    if action == "decode":
        value = ast.literal_eval(text.strip())
        if not isinstance(value, str):
            raise ValueError("Input is not a string literal")
        return value
    quote = str(options.get("quote", '"'))
    escaped = text.encode("unicode_escape").decode("ascii").replace(quote, "\\" + quote)
    return f"{quote}{escaped}{quote}"


def normalize(form: str, _action: str, text: str, _options: dict) -> str:
    return unicodedata.normalize(form, text)


def width(mode: str, _action: str, text: str, _options: dict) -> str:
    if mode == "halfwidth":
        return unicodedata.normalize("NFKC", text)
    return "".join(
        "\u3000" if char == " " else chr(ord(char) + 0xFEE0) if "!" <= char <= "~" else char for char in text
    )


def crc32(_action: str, text: str, options: dict) -> str:
    return f"{binascii.crc32(text.encode(_encoding(options))) & 0xFFFFFFFF:08x}"
