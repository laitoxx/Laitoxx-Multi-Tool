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

from .nickname_anarchy import AnarchyVariantsMixin
from .nickname_discovery import NicknameDiscoveryMixin
from .nickname_edits import NicknameEditMixin
from .nickname_names import NameVariantsMixin
from .nickname_phonetics import PhoneticVariantsMixin


class NicknameGenerator(
    NicknameEditMixin, AnarchyVariantsMixin, NameVariantsMixin, PhoneticVariantsMixin, NicknameDiscoveryMixin
):
    """
    Generate probable alternative usernames using forensic techniques.

    Techniques implemented:
    - Leetspeak substitutions
    - Homoglyph substitutions (Latin ↔ Cyrillic lookalikes)
    - Common prefix/suffix patterns
    - Separator variations
    - Character transposition / deletion / insertion
    - Numeric pattern augmentation
    - Phonetic matching (Soundex, Metaphone)
    - Levenshtein distance neighbors
    - Name permutations (first+last, initials, etc.)
    - Username-Anarchy 24 format plugins
    - String decomposition (splitting username into name components)
    """

    # ---- Substitution tables ----
    LEET_MAP: dict[str, list[str]] = {
        "a": ["4", "@"],
        "b": ["8"],
        "e": ["3"],
        "g": ["9", "6"],
        "i": ["1", "!"],
        "l": ["1", "|"],
        "o": ["0"],
        "s": ["5", "$"],
        "t": ["7", "+"],
        "z": ["2"],
    }

    HOMOGLYPH_MAP: dict[str, list[str]] = {
        # Latin to Cyrillic lookalikes.
        "a": ["\u0430"],
        "c": ["\u0441"],
        "e": ["\u0435"],
        "o": ["\u043e"],
        "p": ["\u0440"],
        "x": ["\u0445"],
        "y": ["\u0443"],
        "H": ["\u041d"],
        "M": ["\u041c"],
        "T": ["\u0422"],
        "B": ["\u0412"],
        "K": ["\u041a"],
    }

    COMMON_PREFIXES = [
        "the",
        "real",
        "official",
        "its",
        "im",
        "i_am",
        "iam",
        "x",
        "xx",
        "mr",
        "ms",
        "dr",
        "not",
        "true",
        "just",
        "hey",
        "dark",
        "cool",
        "pro",
        "neo",
        "cyber",
    ]

    COMMON_SUFFIXES = [
        "official",
        "real",
        "hd",
        "tv",
        "yt",
        "gaming",
        "dev",
        "pro",
        "master",
        "boss",
        "king",
        "queen",
        "xo",
        "xx",
        "x",
        "777",
        "666",
        "228",
        "1337",
        "01",
        "69",
        "420",
        "007",
    ]

    SEPARATORS = ["", ".", "-", "_"]

    COMMON_NUMBERS = [
        "0",
        "1",
        "2",
        "3",
        "5",
        "7",
        "11",
        "13",
        "23",
        "42",
        "69",
        "77",
        "88",
        "99",
        "100",
        "101",
        "123",
        "228",
        "313",
        "321",
        "333",
        "404",
        "420",
        "666",
        "777",
        "1337",
    ]

    BIRTH_YEARS = [str(y) for y in range(1985, 2010)]
    BIRTH_YEARS_SHORT = [str(y)[2:] for y in range(1985, 2010)]

    def __init__(self, username: str, max_variants: int = 500):
        self.username = username.strip()
        self.max_variants = max_variants

    # ------------------------------------------------------------------
    # Leetspeak
    # ------------------------------------------------------------------
    def leetspeak_variants(self) -> list[str]:
        """Generate leetspeak substitutions (single-char replacements)."""
        results = set()
        lower = self.username.lower()
        for i, ch in enumerate(lower):
            for sub in self.LEET_MAP.get(ch, []):
                variant = lower[:i] + sub + lower[i + 1 :]
                results.add(variant)
        # Full leet
        full_leet = lower
        for ch, subs in self.LEET_MAP.items():
            full_leet = full_leet.replace(ch, subs[0])
        if full_leet != lower:
            results.add(full_leet)
        return list(results)

    # ------------------------------------------------------------------
    # Homoglyphs
    # ------------------------------------------------------------------
    def homoglyph_variants(self) -> list[str]:
        """Replace Latin chars with Cyrillic lookalikes."""
        results = set()
        for i, ch in enumerate(self.username):
            for sub in self.HOMOGLYPH_MAP.get(ch, []):
                variant = self.username[:i] + sub + self.username[i + 1 :]
                results.add(variant)
        return list(results)

    # ------------------------------------------------------------------
    # Prefix / Suffix
    # ------------------------------------------------------------------
    def prefix_suffix_variants(self) -> list[str]:
        results = set()
        base = self.username.lower()
        for sep in self.SEPARATORS:
            for pfx in self.COMMON_PREFIXES:
                results.add(pfx + sep + base)
            for sfx in self.COMMON_SUFFIXES:
                results.add(base + sep + sfx)
        return list(results)

    # ------------------------------------------------------------------
    # Separator variations
    # ------------------------------------------------------------------
    def separator_variants(self) -> list[str]:
        """Replace or insert separators between word boundaries."""
        results = set()
        # Split by existing separators
        parts = re.split(r"[._\-]", self.username)
        if len(parts) > 1:
            for sep in self.SEPARATORS:
                results.add(sep.join(parts))
        # Insert separators at camelCase boundaries
        parts_camel = re.sub(r"([a-z])([A-Z])", r"\1_\2", self.username).lower().split("_")
        if len(parts_camel) > 1:
            for sep in self.SEPARATORS:
                results.add(sep.join(parts_camel))
        # Insert separators between letters and digits
        parts_num = re.split(r"(\d+)", self.username)
        if len(parts_num) > 1:
            for sep in self.SEPARATORS:
                results.add(sep.join(p for p in parts_num if p))
        results.discard(self.username)
        return list(results)

    # ------------------------------------------------------------------
    # Numeric augmentation
    # ------------------------------------------------------------------
    def numeric_variants(self) -> list[str]:
        """Append/prepend common numbers and birth years."""
        results = set()
        base = self.username.lower()
        # Strip trailing numbers to find base
        base_no_num = re.sub(r"\d+$", "", base)
        trailing_num = re.search(r"(\d+)$", base)

        for num in self.COMMON_NUMBERS + self.BIRTH_YEARS_SHORT + self.BIRTH_YEARS:
            results.add(base_no_num + num)
            results.add(num + base_no_num)

        # If username already has trailing number, try other numbers
        if trailing_num:
            existing = trailing_num.group(1)
            for num in self.COMMON_NUMBERS:
                if num != existing:
                    results.add(base_no_num + num)

        results.discard(self.username.lower())
        return list(results)

    # ------------------------------------------------------------------
    # Transposition
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Case variations
    # ------------------------------------------------------------------

    # ==================================================================
    # USERNAME-ANARCHY FORMAT PLUGINS (ported from Ruby)
    # ==================================================================

    # ==================================================================
    # STRING DECOMPOSITION (Social-Analyzer style)
    # ==================================================================

    # ------------------------------------------------------------------
    # Name permutations (original + expanded with Anarchy patterns)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Phonetic algorithms
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Levenshtein distance
    # ------------------------------------------------------------------

    # ==================================================================
    # Alt-account correlation helpers (Research #2)
    # ==================================================================

    # ------------------------------------------------------------------
    # Master generator
    # ------------------------------------------------------------------
