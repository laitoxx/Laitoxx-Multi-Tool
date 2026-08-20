"""Number, date and digest converters."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction

DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ROMAN = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)
ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
KANJI_DIGITS = "零一二三四五六七八九"


def parse_number(text: str, radix: int) -> int:
    cleaned = text.strip().replace("_", "")
    return int(cleaned, radix)


def format_number(value: int, radix: int) -> str:
    if not 2 <= radix <= 36:
        raise ValueError("Radix must be between 2 and 36")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    output = []
    while value:
        value, digit = divmod(value, radix)
        output.append(DIGITS[digit])
    return sign + "".join(reversed(output))


def number(mode: str, text: str, options: dict) -> str:
    source_radix = int(options.get("source_radix", 10))
    target_radix = {"num_bin": 2, "num_oct": 8, "num_dec": 10, "num_hex": 16}.get(mode, int(options.get("radix", 10)))
    return format_number(parse_number(text, source_radix), target_radix)


def fraction(text: str) -> str:
    value = Fraction(Decimal(text.strip()))
    return f"{value.numerator}/{value.denominator}"


def roman(action: str, text: str) -> str:
    if action == "decode":
        source, total, index = text.strip().upper(), 0, 0
        for value, symbol in ROMAN:
            while source[index : index + len(symbol)] == symbol:
                total += value
                index += len(symbol)
        if index != len(source):
            raise ValueError("Invalid Roman numeral")
        return str(total)
    value = int(text)
    if not 0 < value < 4000:
        raise ValueError("Roman numerals support 1..3999")
    output = []
    for number_value, symbol in ROMAN:
        count, value = divmod(value, number_value)
        output.append(symbol * count)
    return "".join(output)


def _english_under_1000(value: int) -> str:
    parts = []
    if value >= 100:
        parts.extend((ONES[value // 100], "hundred"))
        value %= 100
    if value >= 20:
        parts.append(TENS[value // 10] + ("-" + ONES[value % 10] if value % 10 else ""))
    elif value:
        parts.append(ONES[value])
    return " ".join(parts)


def english_number(action: str, text: str) -> str:
    if action == "decode":
        tokens = text.lower().replace("-", " ").replace(",", " ").split()
        small = {word: index for index, word in enumerate(ONES)} | {
            word: index * 10 for index, word in enumerate(TENS) if word
        }
        total = current = 0
        for token in tokens:
            if token in small:
                current += small[token]
            elif token == "hundred":
                current *= 100
            elif token in {"thousand", "million", "billion", "trillion"}:
                scale = {"thousand": 10**3, "million": 10**6, "billion": 10**9, "trillion": 10**12}[token]
                total += current * scale
                current = 0
            elif token not in {"and", "negative"}:
                raise ValueError(f"Unknown English number word: {token}")
        value = total + current
        return str(-value if "negative" in tokens else value)
    value = int(text.strip())
    if value == 0:
        return "zero"
    sign, value = ("negative ", -value) if value < 0 else ("", value)
    groups = []
    for scale, name in ((10**12, "trillion"), (10**9, "billion"), (10**6, "million"), (10**3, "thousand"), (1, "")):
        count, value = divmod(value, scale)
        if count:
            groups.append(_english_under_1000(count) + (" " + name if name else ""))
    return sign + " ".join(groups)


def kanji_number(action: str, text: str) -> str:
    if action == "decode":
        digit = {char: index for index, char in enumerate(KANJI_DIGITS)}
        units = {"十": 10, "百": 100, "千": 1000}
        large = {"万": 10**4, "億": 10**8, "兆": 10**12}
        total = section = number_value = 0
        for char in text.strip():
            if char in digit:
                number_value = digit[char]
            elif char in units:
                section += (number_value or 1) * units[char]
                number_value = 0
            elif char in large:
                total += (section + number_value) * large[char]
                section = number_value = 0
            else:
                raise ValueError(f"Unknown Kanji numeral: {char}")
        return str(total + section + number_value)
    value = int(text.strip())
    if value == 0:
        return "零"
    if value < 0 or value >= 10**16:
        raise ValueError("Kanji conversion supports 0..9999999999999999")

    def group(number_value: int) -> str:
        result = []
        for unit, symbol in ((1000, "千"), (100, "百"), (10, "十"), (1, "")):
            count, number_value = divmod(number_value, unit)
            if count:
                if count != 1 or unit == 1:
                    result.append(KANJI_DIGITS[count])
                result.append(symbol)
        return "".join(result)

    output = []
    for scale, symbol in ((10**12, "兆"), (10**8, "億"), (10**4, "万"), (1, "")):
        count, value = divmod(value, scale)
        if count:
            output.extend((group(count), symbol))
    return "".join(output)


def unix_time(action: str, text: str) -> str:
    if action == "decode":
        return datetime.fromtimestamp(float(text), UTC).isoformat().replace("+00:00", "Z")
    normalized = text.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return str(int(parsed.timestamp()))


def digest(mode: str, text: str, options: dict) -> str:
    encoding = str(options.get("encoding", "utf-8"))
    data = text.encode(encoding)
    if mode == "md2":
        try:
            from Cryptodome.Hash import MD2
        except ImportError as error:
            raise RuntimeError("MD2 requires pycryptodomex; rerun the project installer") from error
        return MD2.new(data).hexdigest()
    algorithm = {
        "sha1": "sha1",
        "sha256": "sha256",
        "sha384": "sha384",
        "sha512": "sha512",
        "md5": "md5",
        "sha3_256": "sha3_256",
    }.get(mode, str(options.get("hash_function", "sha3_256")))
    if algorithm not in {"sha1", "sha256", "sha384", "sha512", "md5", "sha3_224", "sha3_256", "sha3_384", "sha3_512"}:
        raise ValueError("Unsupported SHA-3 function")
    return hashlib.new(algorithm, data).hexdigest()
