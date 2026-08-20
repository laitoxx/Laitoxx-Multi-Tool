"""Classical ciphers exposed by the transformer."""

from __future__ import annotations

import math
import string

ENIGMA_ROTORS = {
    "I": ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"),
    "II": ("AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"),
    "III": ("BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
    "IV": ("ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"),
    "V": ("VZBRGITYUPSDNHLXAWMJQOFECK", "Z"),
}
ENIGMA_REFLECTORS = {"B": "YRUHQSLDPXNGOKMIEBFZCWVJAT", "C": "FVPJIAOYEDRZXWGCTKUQSBNMHL"}


def caesar(text: str, shift: int) -> str:
    output = []
    for char in text:
        if "A" <= char <= "Z":
            output.append(chr((ord(char) - 65 + shift) % 26 + 65))
        elif "a" <= char <= "z":
            output.append(chr((ord(char) - 97 + shift) % 26 + 97))
        else:
            output.append(char)
    return "".join(output)


def rot18(text: str) -> str:
    return "".join(
        chr((ord(char) - 48 + 5) % 10 + 48) if char.isascii() and char.isdigit() else caesar(char, 13) for char in text
    )


def rot47(text: str) -> str:
    return "".join(chr(33 + (ord(char) - 33 + 47) % 94) if 33 <= ord(char) <= 126 else char for char in text)


def atbash(text: str) -> str:
    output = []
    for char in text:
        if "A" <= char <= "Z":
            output.append(chr(155 - ord(char)))
        elif "a" <= char <= "z":
            output.append(chr(219 - ord(char)))
        else:
            output.append(char)
    return "".join(output)


def affine(action: str, text: str, options: dict) -> str:
    a, b = int(options.get("a", 5)), int(options.get("b", 8))
    if math.gcd(a, 26) != 1:
        raise ValueError("Affine A must be coprime with 26")
    inverse = pow(a, -1, 26)
    output = []
    for char in text:
        if char.isascii() and char.isalpha():
            base = 65 if char.isupper() else 97
            value = ord(char) - base
            converted = (a * value + b) % 26 if action == "encode" else inverse * (value - b) % 26
            output.append(chr(base + converted))
        else:
            output.append(char)
    return "".join(output)


def vigenere(action: str, text: str, options: dict) -> str:
    key = "".join(char for char in str(options.get("key", "SECRET")).upper() if char in string.ascii_uppercase)
    if not key:
        raise ValueError("Vigenere key must contain A-Z")
    output, index = [], 0
    for char in text:
        if char.isascii() and char.isalpha():
            shift = ord(key[index % len(key)]) - 65
            output.append(caesar(char, shift if action == "encode" else -shift))
            index += 1
        else:
            output.append(char)
    return "".join(output)


def baconian(action: str, text: str, options: dict) -> str:
    symbols = str(options.get("symbols", "AB"))
    if len(symbols) != 2 or symbols[0] == symbols[1]:
        raise ValueError("Baconian notation requires two distinct symbols")
    if action == "encode":
        chunks = []
        for char in text.upper():
            if "A" <= char <= "Z":
                bits = f"{ord(char) - 65:05b}"
                chunks.append("".join(symbols[int(bit)] for bit in bits))
            elif char.isspace():
                chunks.append("/")
        return " ".join(chunks)
    output = []
    for chunk in text.replace("/", " / ").split():
        if chunk == "/":
            output.append(" ")
        elif len(chunk) == 5 and all(char in symbols for char in chunk):
            value = int("".join("0" if char == symbols[0] else "1" for char in chunk), 2)
            output.append(chr(65 + value) if value < 26 else "?")
    return "".join(output)


def rail_fence(action: str, text: str, options: dict) -> str:
    rails = int(options.get("rails", 3))
    if rails < 2 or rails >= max(2, len(text)):
        return text
    pattern = list(range(rails)) + list(range(rails - 2, 0, -1))
    indices = [pattern[index % len(pattern)] for index in range(len(text))]
    if action == "encode":
        return "".join(text[index] for rail in range(rails) for index, value in enumerate(indices) if value == rail)
    counts = [indices.count(rail) for rail in range(rails)]
    buckets, offset = [], 0
    for count in counts:
        buckets.append(list(text[offset : offset + count]))
        offset += count
    return "".join(buckets[rail].pop(0) for rail in indices)


def scytale(action: str, text: str, options: dict) -> str:
    columns = max(1, int(options.get("columns", 3)))
    if action == "encode":
        return "".join(text[offset::columns] for offset in range(columns))
    rows, remainder = divmod(len(text), columns)
    sizes = [rows + (1 if column < remainder else 0) for column in range(columns)]
    chunks, offset = [], 0
    for size in sizes:
        chunks.append(text[offset : offset + size])
        offset += size
    return "".join(
        chunks[column][row] for row in range(rows + 1) for column in range(columns) if row < len(chunks[column])
    )


def playfair(action: str, text: str, options: dict) -> str:
    key = "".join(char for char in str(options.get("key", "SECRET")).upper() if char in string.ascii_uppercase).replace(
        "J", "I"
    )
    alphabet = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
    square = "".join(dict.fromkeys(key + alphabet))
    positions = {char: divmod(index, 5) for index, char in enumerate(square)}
    cleaned = "".join(char for char in text.upper().replace("J", "I") if char in alphabet)
    if action == "encode":
        pairs, index = [], 0
        while index < len(cleaned):
            first = cleaned[index]
            second = cleaned[index + 1] if index + 1 < len(cleaned) else "X"
            if first == second:
                second = "X"
                index += 1
            else:
                index += 2
            pairs.append((first, second))
    else:
        if len(cleaned) % 2:
            raise ValueError("Playfair ciphertext length must be even")
        pairs = list(zip(cleaned[::2], cleaned[1::2], strict=True))
    direction = 1 if action == "encode" else -1
    output = []
    for first, second in pairs:
        row1, col1 = positions[first]
        row2, col2 = positions[second]
        if row1 == row2:
            output.extend((square[row1 * 5 + (col1 + direction) % 5], square[row2 * 5 + (col2 + direction) % 5]))
        elif col1 == col2:
            output.extend((square[((row1 + direction) % 5) * 5 + col1], square[((row2 + direction) % 5) * 5 + col2]))
        else:
            output.extend((square[row1 * 5 + col2], square[row2 * 5 + col1]))
    return "".join(output)


def enigma(_action: str, text: str, options: dict) -> str:
    names = str(options.get("rotors", "I II III")).upper().replace(",", " ").split()
    if len(names) != 3 or any(name not in ENIGMA_ROTORS for name in names):
        raise ValueError("Enigma rotors must be three values from I II III IV V")
    positions_text = str(options.get("positions", "AAA")).upper().replace(" ", "")
    rings_text = str(options.get("rings", "AAA")).upper().replace(" ", "")
    if len(positions_text) != 3 or len(rings_text) != 3 or not positions_text.isalpha() or not rings_text.isalpha():
        raise ValueError("Enigma positions and rings must contain three letters")
    positions = [ord(char) - 65 for char in positions_text]
    rings = [ord(char) - 65 for char in rings_text]
    plugboard = {char: char for char in string.ascii_uppercase}
    for pair in str(options.get("plugboard", "")).upper().split():
        if len(pair) != 2 or any(char not in string.ascii_uppercase for char in pair):
            raise ValueError("Plugboard pairs must look like AB CD")
        first, second = pair
        if plugboard[first] != first or plugboard[second] != second:
            raise ValueError("Plugboard letter is used more than once")
        plugboard[first], plugboard[second] = second, first
    reflector = ENIGMA_REFLECTORS.get(str(options.get("reflector", "B")).upper())
    if reflector is None:
        raise ValueError("Enigma reflector must be B or C")

    def through(value: int, rotor_index: int, reverse: bool = False) -> int:
        wiring = ENIGMA_ROTORS[names[rotor_index]][0]
        shifted = (value + positions[rotor_index] - rings[rotor_index]) % 26
        mapped = wiring.index(chr(65 + shifted)) if reverse else ord(wiring[shifted]) - 65
        return (mapped - positions[rotor_index] + rings[rotor_index]) % 26

    output = []
    for character in text.upper():
        if character not in string.ascii_uppercase:
            output.append(character)
            continue
        middle_at_notch = chr(65 + positions[1]) in ENIGMA_ROTORS[names[1]][1]
        right_at_notch = chr(65 + positions[2]) in ENIGMA_ROTORS[names[2]][1]
        if middle_at_notch:
            positions[0] = (positions[0] + 1) % 26
        if middle_at_notch or right_at_notch:
            positions[1] = (positions[1] + 1) % 26
        positions[2] = (positions[2] + 1) % 26
        value = ord(plugboard[character]) - 65
        for rotor_index in (2, 1, 0):
            value = through(value, rotor_index)
        value = ord(reflector[value]) - 65
        for rotor_index in (0, 1, 2):
            value = through(value, rotor_index, True)
        output.append(plugboard[chr(65 + value)])
    return "".join(output)
