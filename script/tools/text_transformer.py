"""
Text Transformer — encode / decode / transform text in various formats.

Modes
-----
  leet       — L33t sp34k substitution
  morse      — Morse code encode/decode
  binary     — UTF-8 text ↔ binary string (space-separated bytes)
  hex        — UTF-8 text ↔ hex string
  rot13      — ROT-13 cipher
  caesar     — Caesar cipher (shift 1-25, encode/decode)
  base64     — Base64 encode/decode
  url        — URL-encode/decode
  reverse    — Reverse the string
  upper      — UPPERCASE
  lower      — lowercase

GUI  → text_transformer_tool({"mode": "hex",    "action": "encode", "text": "hello"})
       text_transformer_tool({"mode": "caesar",  "action": "decode", "text": "...", "shift": 13})
CLI  → text_transformer_tool()
"""

import base64
import codecs
from urllib.parse import quote, unquote

from ..shared_utils import Color

# ── Morse table ────────────────────────────────────────────────────────────────
_MORSE_ENC = {
    'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---',
    'K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-',
    'U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..',
    '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....','6':'-....','7':'--...',
    '8':'---..','9':'----.','.':'.-.-.-',',':'--..--','?':'..--..','!':'-.-.--','/':'-..-.','(':'-.--.',
    ')':'-.--.-','&':'.-...','=':'-...-','+':'.-.-.','_':'..--.-','"':'.-..-.','$':'...-..-','@':'.--.-.','  ':' ',
}
_MORSE_DEC = {v: k for k, v in _MORSE_ENC.items()}

# ── Leet table ─────────────────────────────────────────────────────────────────
_LEET = {'a':'4','e':'3','g':'9','i':'1','o':'0','s':'5','t':'7','b':'8','l':'|','z':'2'}
_LEET_REV = {v: k for k, v in _LEET.items()}

# ── helpers ────────────────────────────────────────────────────────────────────

def _encode_morse(text: str) -> str:
    result = []
    for ch in text.upper():
        if ch == ' ':
            result.append('/')
        elif ch in _MORSE_ENC:
            result.append(_MORSE_ENC[ch])
        else:
            result.append('?')
    return ' '.join(result)


def _decode_morse(text: str) -> str:
    result = []
    for word in text.strip().split(' / '):
        chars = []
        for code in word.split():
            chars.append(_MORSE_DEC.get(code, '?'))
        result.append(''.join(chars))
    return ' '.join(result)


def _caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if ch.isupper():
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        elif ch.islower():
            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))
        else:
            out.append(ch)
    return ''.join(out)


# ── dispatch ───────────────────────────────────────────────────────────────────

def _error_result(exc: Exception) -> str:
    return f"[error: {exc}]"


def _transform_leet(action: str, text: str, _shift: int) -> str:
    if action == "encode":
        return ''.join(_LEET.get(c.lower(), c) for c in text)
    return ''.join(_LEET_REV.get(c, c) for c in text)


def _transform_morse(action: str, text: str, _shift: int) -> str:
    return _encode_morse(text) if action == "encode" else _decode_morse(text)


def _transform_binary(action: str, text: str, _shift: int) -> str:
    if action == "encode":
        return ' '.join(f'{b:08b}' for b in text.encode('utf-8'))
    try:
        return bytes(int(b, 2) for b in text.split()).decode('utf-8')
    except Exception as e:
        return _error_result(e)


def _transform_hex(action: str, text: str, _shift: int) -> str:
    if action == "encode":
        return text.encode('utf-8').hex()
    try:
        return bytes.fromhex(text.replace(' ', '')).decode('utf-8')
    except Exception as e:
        return _error_result(e)


def _transform_rot13(_action: str, text: str, _shift: int) -> str:
    return codecs.encode(text, 'rot_13')


def _transform_caesar(action: str, text: str, shift: int) -> str:
    s = shift if action == "encode" else -shift
    return _caesar(text, s)


def _transform_base64(action: str, text: str, _shift: int) -> str:
    if action == "encode":
        return base64.b64encode(text.encode('utf-8')).decode()
    try:
        padded = text + '=' * (-len(text) % 4)
        return base64.b64decode(padded).decode('utf-8')
    except Exception as e:
        return _error_result(e)


def _transform_url(action: str, text: str, _shift: int) -> str:
    return quote(text, safe='') if action == "encode" else unquote(text)


def _transform_reverse(_action: str, text: str, _shift: int) -> str:
    return text[::-1]


def _transform_upper(_action: str, text: str, _shift: int) -> str:
    return text.upper()


def _transform_lower(_action: str, text: str, _shift: int) -> str:
    return text.lower()


_TRANSFORMS = {
    "leet": _transform_leet,
    "morse": _transform_morse,
    "binary": _transform_binary,
    "hex": _transform_hex,
    "rot13": _transform_rot13,
    "caesar": _transform_caesar,
    "base64": _transform_base64,
    "url": _transform_url,
    "reverse": _transform_reverse,
    "upper": _transform_upper,
    "lower": _transform_lower,
}


def _transform(mode: str, action: str, text: str, shift: int = 3) -> str:
    handler = _TRANSFORMS.get(mode)
    if not handler:
        return f"[unknown mode: {mode}]"
    return handler(action.lower(), text, shift)


_MODES = ["leet", "morse", "binary", "hex", "rot13", "caesar", "base64", "url", "reverse", "upper", "lower"]
_HAS_ACTION = {"leet", "morse", "binary", "hex", "caesar", "base64", "url"}

def text_transformer_tool(data=None):
    if data:
        mode   = data.get("mode", "").strip().lower()
        action = data.get("action", "encode").strip().lower()
        text   = data.get("text", "")
        shift  = int(data.get("shift", 3))
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
              f" Text Transformer\n")
        for i, m in enumerate(_MODES, 1):
            print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}{i}{Color.DARK_GRAY}]{Color.DARK_RED} {m}")
        print()

        try:
            sel = int(input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                f" Select mode: "
            ).strip()) - 1
            mode = _MODES[sel]
        except (ValueError, IndexError):
            print(f"{Color.RED}Invalid selection.")
            return

        action = "encode"
        shift  = 3
        if mode in _HAS_ACTION:
            action = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                f" Action [encode/decode]: "
            ).strip().lower() or "encode"

        if mode == "caesar":
            try:
                shift = int(input(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                    f" Shift (1-25): "
                ).strip())
            except ValueError:
                shift = 3

        text = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Enter text: {Color.RESET}"
        )

    if not text:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No text provided.")
        return

    result = _transform(mode, action, text, shift)

    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Result · {mode}"
          + (f" · {action}" if mode in _HAS_ACTION else "")
          + f" {Color.DARK_RED}]" + "─" * max(0, 30 - len(mode)))
    print(f"{Color.WHITE}{result}")
    print(f"{Color.DARK_RED}└" + "─" * 45)
