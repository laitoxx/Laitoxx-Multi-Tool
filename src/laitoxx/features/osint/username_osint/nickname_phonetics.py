"""
nickname_generator.py - Forensic nickname generation engine.

Implements criminalistic methods for generating probable alternative
usernames based on psychological patterns and algorithmic transformations.

Ported techniques:
  - Username-Anarchy: 24 format plugins (Ruby → Python)
  - Research #2: Leetspeak, homoglyphs, Soundex, Metaphone, Levenshtein
  - Name databases: Facebook top-10K, forum names
"""

from __future__ import annotations

import re


class PhoneticVariantsMixin:
    @staticmethod
    def soundex(name: str) -> str:
        """Classic Soundex algorithm (returns 4-char code)."""
        if not name:
            return ""
        name = name.upper()
        code = name[0]
        mapping = {
            "B": "1",
            "F": "1",
            "P": "1",
            "V": "1",
            "C": "2",
            "G": "2",
            "J": "2",
            "K": "2",
            "Q": "2",
            "S": "2",
            "X": "2",
            "Z": "2",
            "D": "3",
            "T": "3",
            "L": "4",
            "M": "5",
            "N": "5",
            "R": "6",
        }
        prev = mapping.get(name[0], "0")
        for ch in name[1:]:
            digit = mapping.get(ch, "0")
            if digit != "0" and digit != prev:
                code += digit
            prev = digit if digit != "0" else prev
            if len(code) >= 4:
                break
        return (code + "000")[:4]

    @staticmethod
    def metaphone(name: str) -> str:
        """Simplified Metaphone algorithm."""
        if not name:
            return ""
        name = name.upper()
        name = re.sub(r"[^A-Z]", "", name)
        if not name:
            return ""

        # Drop duplicate adjacent letters
        result = name[0]
        for ch in name[1:]:
            if ch != result[-1]:
                result += ch
        name = result

        # Simple consonant mapping
        trans = {
            "PH": "F",
            "CK": "K",
            "SCH": "SK",
            "GH": "F",
            "KN": "N",
            "WR": "R",
            "AE": "E",
            "GN": "N",
            "MB": "M",
            "PN": "N",
        }
        for old, new in trans.items():
            name = name.replace(old, new)

        # Drop vowels except leading
        if len(name) > 1:
            name = name[0] + re.sub(r"[AEIOU]", "", name[1:])

        return name[:6]

    def phonetic_group(self) -> tuple[str, str]:
        """Return (soundex_code, metaphone_code) for this username."""
        alpha_part = re.sub(r"[^a-zA-Z]", "", self.username)
        return self.soundex(alpha_part), self.metaphone(alpha_part)

    @staticmethod
    def levenshtein(a: str, b: str) -> int:
        """Compute Levenshtein edit distance between two strings."""
        if len(a) < len(b):
            return PhoneticVariantsMixin.levenshtein(b, a)
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                cost = 0 if ca == cb else 1
                curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
            prev = curr
        return prev[-1]

    def levenshtein_neighbors(self, wordlist: list[str], max_distance: int = 2) -> list[str]:
        """Find words from *wordlist* within *max_distance* edits of this username."""
        target = self.username.lower()
        return [w for w in wordlist if self.levenshtein(target, w.lower()) <= max_distance]

    def similarity_score(self, other: str) -> float:
        """
        Compute a normalized similarity score (0.0-1.0) between this
        username and another, combining multiple signals.
        """
        a = self.username.lower()
        b = other.lower()

        # 1. Levenshtein similarity
        max_len = max(len(a), len(b), 1)
        lev_sim = 1.0 - (self.levenshtein(a, b) / max_len)

        # 2. Soundex match
        sa = self.soundex(re.sub(r"[^a-zA-Z]", "", a))
        sb = self.soundex(re.sub(r"[^a-zA-Z]", "", b))
        soundex_match = 1.0 if sa == sb and sa else 0.0

        # 3. Metaphone match
        ma = self.metaphone(re.sub(r"[^a-zA-Z]", "", a))
        mb = self.metaphone(re.sub(r"[^a-zA-Z]", "", b))
        metaphone_match = 1.0 if ma == mb and ma else 0.0

        # 4. Common substring ratio
        common = 0
        for length in range(min(len(a), len(b)), 2, -1):
            for start in range(len(a) - length + 1):
                sub = a[start : start + length]
                if sub in b:
                    common = length
                    break
            if common:
                break
        substr_ratio = common / max_len

        # 5. Same base (strip numbers)
        base_a = re.sub(r"\d+", "", a)
        base_b = re.sub(r"\d+", "", b)
        base_match = 1.0 if base_a == base_b and base_a else 0.0

        # Weighted combination
        score = lev_sim * 0.30 + soundex_match * 0.15 + metaphone_match * 0.15 + substr_ratio * 0.20 + base_match * 0.20
        return round(min(score, 1.0), 3)
