"""Text casing and line operations."""

from __future__ import annotations

import re


def words(text: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.findall(r"[^\W_]+", expanded, flags=re.UNICODE)


def case(mode: str, text: str) -> str:
    parts = words(text)
    if mode == "upper_camel":
        return "".join(part[:1].upper() + part[1:].lower() for part in parts)
    if mode == "lower_camel":
        value = case("upper_camel", text)
        return value[:1].lower() + value[1:]
    if mode == "upper_snake":
        return "_".join(parts).upper()
    if mode == "lower_snake":
        return "_".join(parts).lower()
    if mode == "upper_kebab":
        return "-".join(parts).upper()
    if mode == "lower_kebab":
        return "-".join(parts).lower()
    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    if mode == "swapcase":
        return text.swapcase()
    if mode == "capitalize":
        return text.title()
    if mode == "alternating":
        offset = 1 if text[:1].isupper() else 0
        count = 0
        output = []
        for character in text:
            if character.isalpha():
                output.append(character.upper() if (count + offset) % 2 else character.lower())
                count += 1
            else:
                output.append(character)
        return "".join(output)
    if mode == "reverse":
        return text[::-1]
    if mode == "line_sort":
        return "\n".join(sorted(text.splitlines(), reverse=False))
    if mode == "line_sort_desc":
        return "\n".join(sorted(text.splitlines(), reverse=True))
    if mode == "dedupe_lines":
        return "\n".join(dict.fromkeys(text.splitlines()))
    raise ValueError(f"Unknown text operation: {mode}")
