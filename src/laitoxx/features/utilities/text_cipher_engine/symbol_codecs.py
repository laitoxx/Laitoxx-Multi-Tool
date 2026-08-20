"""Symbol alphabets and decorative Unicode text."""

from __future__ import annotations

import string

HIEROGLYPHS = dict(
    zip(
        string.ascii_uppercase,
        (
            "𓄿",
            "𓃀",
            "𓎡",
            "𓂧",
            "𓇋",
            "𓆑",
            "𓎼",
            "𓉔",
            "𓇋",
            "𓆓",
            "𓎡",
            "𓃭",
            "𓅓",
            "𓈖",
            "𓍯",
            "𓊪",
            "𓈎",
            "𓂋",
            "𓋴",
            "𓏏",
            "𓏲",
            "𓆑",
            "𓅱",
            "𓎡𓋴",
            "𓇌",
            "𓊃",
        ),
        strict=True,
    )
)
HIEROGLYPH_DECODE = {value: key for key, value in HIEROGLYPHS.items()}
HIEROGLYPH_DECODE.update(
    {"𓂝": "A", "𓂽": "D", "𓎽": "G", "𓅼": "G", "𓎛": "H", "𓐝": "M", "𓋔": "N", "𓈙": "S", "𓍿": "T", "𓏭": "Y"}
)
BRAILLE_LETTERS = dict(zip(string.ascii_lowercase, "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵", strict=True))
BRAILLE_PUNCTUATION = {" ": "⠀", ",": "⠂", ";": "⠆", ":": "⠒", ".": "⠲", "!": "⠖", "?": "⠦", "-": "⠤", "'": "⠄"}
BRAILLE_REVERSE = {
    **{value: key for key, value in BRAILLE_LETTERS.items()},
    **{value: key for key, value in BRAILLE_PUNCTUATION.items()},
}
DIGIT_TO_BRAILLE = dict(zip("1234567890", "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚", strict=True))
BRAILLE_TO_DIGIT = {value: key for key, value in DIGIT_TO_BRAILLE.items()}


def hieroglyphs(action: str, text: str, _options: dict) -> str:
    if action == "encode":
        return "".join(HIEROGLYPHS.get(char.upper(), char) for char in text)
    output, index = [], 0
    keys = sorted(HIEROGLYPH_DECODE, key=len, reverse=True)
    while index < len(text):
        match = next((symbol for symbol in keys if text.startswith(symbol, index)), None)
        if match:
            output.append(HIEROGLYPH_DECODE[match])
            index += len(match)
        else:
            output.append(text[index])
            index += 1
    return "".join(output)


def braille(action: str, text: str, _options: dict) -> str:
    if action == "encode":
        output, number_mode = [], False
        for char in text:
            if char.isascii() and char.isdigit():
                if not number_mode:
                    output.append("⠼")
                output.append(DIGIT_TO_BRAILLE[char])
                number_mode = True
                continue
            number_mode = False
            if char.isascii() and char.isupper():
                output.extend(("⠠", BRAILLE_LETTERS[char.lower()]))
            else:
                output.append(BRAILLE_LETTERS.get(char.lower(), BRAILLE_PUNCTUATION.get(char, char)))
        return "".join(output)
    output, capital, number = [], False, False
    for char in text:
        if char == "⠠":
            capital = True
            continue
        if char == "⠼":
            number = True
            continue
        if number and char in BRAILLE_TO_DIGIT:
            output.append(BRAILLE_TO_DIGIT[char])
            continue
        number = False
        decoded = BRAILLE_REVERSE.get(char, char)
        output.append(decoded.upper() if capital else decoded)
        capital = False
    return "".join(output)


STYLE_OFFSETS = {
    "script": (0x1D49C, 0x1D4B6, None),
    "script_bold": (0x1D4D0, 0x1D4EA, None),
    "bold": (0x1D400, 0x1D41A, 0x1D7CE),
    "bold_italic": (0x1D468, 0x1D482, None),
    "italic": (0x1D434, 0x1D44E, None),
    "fraktur": (0x1D504, 0x1D51E, None),
    "double_struck": (0x1D538, 0x1D552, 0x1D7D8),
    "sans": (0x1D5A0, 0x1D5BA, 0x1D7E2),
    "sans_bold": (0x1D5D4, 0x1D5EE, 0x1D7EC),
    "sans_italic": (0x1D608, 0x1D622, None),
    "sans_bold_italic": (0x1D63C, 0x1D656, None),
    "monospace": (0x1D670, 0x1D68A, 0x1D7F6),
    "circled": (0x24B6, 0x24D0, 0x2460),
    "negative_circled": (0x1F150, 0x1F150, 0x2775),
    "squared": (0x1F130, 0x1F130, None),
    "negative_squared": (0x1F170, 0x1F170, None),
}
STYLE_EXCEPTIONS = {
    "script": {
        "B": "ℬ",
        "E": "ℰ",
        "F": "ℱ",
        "H": "ℋ",
        "I": "ℐ",
        "L": "ℒ",
        "M": "ℳ",
        "R": "ℛ",
        "e": "ℯ",
        "g": "ℊ",
        "o": "ℴ",
    },
    "italic": {"h": "ℎ"},
    "fraktur": {"C": "ℭ", "H": "ℌ", "I": "ℑ", "R": "ℜ", "Z": "ℨ"},
    "double_struck": {"C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ", "R": "ℝ", "Z": "ℤ"},
}
SMALL_CAPS = dict(zip(string.ascii_lowercase, "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘꞯʀꜱᴛᴜᴠᴡxʏᴢ", strict=True))

ROMAJI_KANA = {
    "kya": "きゃ",
    "kyu": "きゅ",
    "kyo": "きょ",
    "sha": "しゃ",
    "shu": "しゅ",
    "sho": "しょ",
    "cha": "ちゃ",
    "chu": "ちゅ",
    "cho": "ちょ",
    "nya": "にゃ",
    "nyu": "にゅ",
    "nyo": "にょ",
    "hya": "ひゃ",
    "hyu": "ひゅ",
    "hyo": "ひょ",
    "mya": "みゃ",
    "myu": "みゅ",
    "myo": "みょ",
    "rya": "りゃ",
    "ryu": "りゅ",
    "ryo": "りょ",
    "gya": "ぎゃ",
    "gyu": "ぎゅ",
    "gyo": "ぎょ",
    "ja": "じゃ",
    "ju": "じゅ",
    "jo": "じょ",
    "shi": "し",
    "chi": "ち",
    "tsu": "つ",
    "fu": "ふ",
}
for consonant, row in (
    ("", "あいうえお"),
    ("k", "かきくけこ"),
    ("s", "さしすせそ"),
    ("t", "たちつてと"),
    ("n", "なにぬねの"),
    ("h", "はひふへほ"),
    ("m", "まみむめも"),
    ("y", "やいゆえよ"),
    ("r", "らりるれろ"),
    ("w", "わゐうゑを"),
    ("g", "がぎぐげご"),
    ("z", "ざじずぜぞ"),
    ("d", "だぢづでど"),
    ("b", "ばびぶべぼ"),
    ("p", "ぱぴぷぺぽ"),
):
    for vowel, kana_char in zip("aiueo", row, strict=True):
        ROMAJI_KANA.setdefault(consonant + vowel, kana_char)
ROMAJI_KANA["n"] = "ん"
KANA_ROMAJI = {value: key for key, value in ROMAJI_KANA.items()}
KANA_ROMAJI.update({"し": "shi", "ち": "chi", "つ": "tsu", "ふ": "fu"})
JIS_ENGLISH = "123#4$5%6&7'8(9)0-^|qweErtyuiop@[{asdfghjkl;:]}zZxcvbnm,<.>/?\\"
JIS_JAPANESE = "ぬふあぁうぅえぇおぉやゃゆゅよょわほへーたていぃすかんなにらせ゛゜「ちとしはきくまのりれけむ」つっさそひこみもね、る。め・ろ"
JIS_MAP = dict(zip(JIS_ENGLISH, JIS_JAPANESE, strict=True))
JIS_REVERSE = {value: key for key, value in JIS_MAP.items()}


def styled(_action: str, text: str, options: dict) -> str:
    style = str(options.get("style", "bold"))
    if style == "small_caps":
        return "".join(SMALL_CAPS.get(char, char) for char in text)
    upper, lower, digits = STYLE_OFFSETS.get(style, STYLE_OFFSETS["bold"])
    exceptions = STYLE_EXCEPTIONS.get(style, {})
    output = []
    for char in text:
        if char in exceptions:
            output.append(exceptions[char])
        elif "A" <= char <= "Z":
            output.append(chr(upper + ord(char) - 65))
        elif "a" <= char <= "z":
            source = char.upper() if style in {"negative_circled", "squared", "negative_squared"} else char
            output.append(chr(lower + ord(source) - (65 if source.isupper() else 97)))
        elif digits is not None and "0" <= char <= "9":
            if style == "circled":
                output.append("⓪" if char == "0" else chr(digits + ord(char) - 49))
            elif style == "negative_circled":
                output.append("⓿" if char == "0" else chr(digits + ord(char) - 48))
            else:
                output.append(chr(digits + ord(char) - 48))
        else:
            output.append(char)
    return "".join(output)


def kana_romaji(_action: str, text: str, options: dict) -> str:
    script = str(options.get("script", "romaji")).lower()
    if script == "romaji":
        source = "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in text)
        output, index = [], 0
        keys = sorted(KANA_ROMAJI, key=len, reverse=True)
        while index < len(source):
            match = next((key for key in keys if source.startswith(key, index)), None)
            if match:
                output.append(KANA_ROMAJI[match])
                index += len(match)
            else:
                output.append(source[index])
                index += 1
        return "".join(output)
    source = text.lower()
    output, index = [], 0
    keys = sorted(ROMAJI_KANA, key=len, reverse=True)
    while index < len(source):
        if index + 1 < len(source) and source[index] == source[index + 1] and source[index] not in "aeioun":
            output.append("っ")
            index += 1
            continue
        match = next((key for key in keys if source.startswith(key, index)), None)
        if match:
            output.append(ROMAJI_KANA[match])
            index += len(match)
        else:
            output.append(source[index])
            index += 1
    result = "".join(output)
    return (
        "".join(chr(ord(char) + 0x60) if "ぁ" <= char <= "ゖ" else char for char in result)
        if script == "katakana"
        else result
    )


def jis_keyboard(_action: str, text: str, options: dict) -> str:
    lenient = str(options.get("mode", "strict")).lower() == "lenient"
    output = []
    for character in text:
        lookup = character
        if lenient and character.isascii() and character.isupper() and character not in {"E", "Z"}:
            lookup = character.lower()
        if lenient and "ァ" <= character <= "ヶ":
            lookup = chr(ord(character) - 0x60)
        if lookup in JIS_MAP:
            output.append(JIS_MAP[lookup])
        elif lookup in JIS_REVERSE:
            output.append(JIS_REVERSE[lookup])
        else:
            output.append(character)
    return "".join(output)
