"""
nickname_generator.py — Forensic nickname generation engine.

Implements criminalistic methods for generating probable alternative
usernames based on psychological patterns and algorithmic transformations.

Ported techniques:
  - Username-Anarchy: 24 format plugins (Ruby → Python)
  - Research #2: Leetspeak, homoglyphs, Soundex, Metaphone, Levenshtein
  - Name databases: Facebook top-10K, forum names
"""
from __future__ import annotations

import itertools
import os
import re
from typing import Optional


class NicknameGenerator:
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
        # Latin → Cyrillic lookalikes
        "a": ["\u0430"],  # а
        "c": ["\u0441"],  # с
        "e": ["\u0435"],  # е
        "o": ["\u043e"],  # о
        "p": ["\u0440"],  # р
        "x": ["\u0445"],  # х
        "y": ["\u0443"],  # у
        "H": ["\u041d"],  # Н
        "M": ["\u041c"],  # М
        "T": ["\u0422"],  # Т
        "B": ["\u0412"],  # В
        "K": ["\u041a"],  # К
    }

    COMMON_PREFIXES = [
        "the", "real", "official", "its", "im", "i_am", "iam",
        "x", "xx", "mr", "ms", "dr", "not", "true", "just",
        "hey", "dark", "cool", "pro", "neo", "cyber",
    ]

    COMMON_SUFFIXES = [
        "official", "real", "hd", "tv", "yt", "gaming",
        "dev", "pro", "master", "boss", "king", "queen",
        "xo", "xx", "x", "777", "666", "228", "1337",
        "01", "69", "420", "007",
    ]

    SEPARATORS = ["", ".", "-", "_"]

    COMMON_NUMBERS = [
        "0", "1", "2", "3", "5", "7", "11", "13", "23", "42",
        "69", "77", "88", "99", "100", "101", "123", "228", "313",
        "321", "333", "404", "420", "666", "777", "1337",
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
                variant = lower[:i] + sub + lower[i + 1:]
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
                variant = self.username[:i] + sub + self.username[i + 1:]
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
    def transposition_variants(self) -> list[str]:
        """Swap adjacent characters (common typos)."""
        results = set()
        chars = list(self.username.lower())
        for i in range(len(chars) - 1):
            swapped = chars[:]
            swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
            results.add("".join(swapped))
        results.discard(self.username.lower())
        return list(results)

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------
    def deletion_variants(self) -> list[str]:
        """Delete one character at a time."""
        results = set()
        for i in range(len(self.username)):
            variant = self.username[:i] + self.username[i + 1:]
            if variant:
                results.add(variant.lower())
        return list(results)

    # ------------------------------------------------------------------
    # Case variations
    # ------------------------------------------------------------------
    def case_variants(self) -> list[str]:
        results = set()
        results.add(self.username.lower())
        results.add(self.username.upper())
        results.add(self.username.capitalize())
        results.add(self.username.swapcase())
        results.discard(self.username)
        return list(results)

    # ==================================================================
    # USERNAME-ANARCHY FORMAT PLUGINS (ported from Ruby)
    # ==================================================================

    def anarchy_formats(
        self,
        first_name: str = "",
        last_name: str = "",
        middle_name: str = "",
    ) -> list[str]:
        """
        Generate usernames using all 24 Username-Anarchy format plugins.

        Ported from Ruby's format_anna() method. Each plugin produces
        one or more username variants from name components.
        """
        if not first_name and not last_name:
            return []

        results = set()
        f = first_name.lower().strip()
        l = last_name.lower().strip()
        m = middle_name.lower().strip()
        fi = f[0] if f else ""   # first initial
        li = l[0] if l else ""   # last initial
        mi = m[0] if m else ""   # middle initial

        # --- 24 format plugins ---

        # 1. first
        if f:
            results.add(f)

        # 2. firstlast
        if f and l:
            results.add(f + l)

        # 3. first.last
        if f and l:
            results.add(f + "." + l)

        # 4. firstlast[8] — truncated to 8 chars
        if f and l:
            results.add((f + l)[:8])

        # 5. first[4]last[4] — 4 chars of each
        if f and l:
            results.add(f[:4] + l[:4])

        # 6. firstl — first name + last initial
        if f and li:
            results.add(f + li)

        # 7. f.last — first initial + dot + last
        if fi and l:
            results.add(fi + "." + l)

        # 8. flast — first initial + last
        if fi and l:
            results.add(fi + l)

        # 9. lfirst — last + first (reversed)
        if l and f:
            results.add(l + f)

        # 10. l.first — last + dot + first
        if l and f:
            results.add(l + "." + f)

        # 11. lastf — last + first initial
        if l and fi:
            results.add(l + fi)

        # 12. last
        if l:
            results.add(l)

        # 13. last.f — last + dot + first initial
        if l and fi:
            results.add(l + "." + fi)

        # 14. last.first
        if l and f:
            results.add(l + "." + f)

        # 15. FLast — capitalized first initial + last
        if fi and l:
            results.add(fi.upper() + l.capitalize())

        # 16. first1 — first + single digit (0–9)
        if f:
            for d in range(10):
                results.add(f + str(d))

        # 17. fl — first initial + last initial
        if fi and li:
            results.add(fi + li)

        # 18. fmlast — first initial + middle initial + last
        if fi and mi and l:
            results.add(fi + mi + l)

        # 19. firstmiddlelast — all three concatenated
        if f and m and l:
            results.add(f + m + l)

        # 20. fml — first + middle + last initials
        if fi and mi and li:
            results.add(fi + mi + li)

        # 21. FL — uppercase first + last initials
        if fi and li:
            results.add(fi.upper() + li.upper())

        # 22. FirstLast — capitalized each
        if f and l:
            results.add(f.capitalize() + l.capitalize())

        # 23. First.Last — capitalized with dot
        if f and l:
            results.add(f.capitalize() + "." + l.capitalize())

        # 24. Last — just capitalized last
        if l:
            results.add(l.capitalize())

        # --- Extra: digit range patterns (%D, %DD) ---
        if f and l:
            base_fl = f + l
            # Single digit: 0-9
            for d in range(10):
                results.add(base_fl + str(d))
            # Double digit: 00-99 (sample, not all 100)
            for dd in [0, 1, 11, 22, 33, 42, 55, 66, 69, 77, 88, 99]:
                results.add(base_fl + f"{dd:02d}")

        # --- Extra: separator variants for key patterns ---
        if f and l:
            for sep in [".", "-", "_"]:
                results.add(f + sep + l)
                results.add(l + sep + f)
                results.add(fi + sep + l)
                results.add(l + sep + fi)

        return list(results)

    # ==================================================================
    # STRING DECOMPOSITION (Social-Analyzer style)
    # ==================================================================

    def decompose_username(self) -> list[tuple[str, str]]:
        """
        Try to decompose a username into (first, last) name pairs.

        Splits on separators, camelCase, and common patterns.
        Returns list of (first, last) tuples.
        """
        pairs: list[tuple[str, str]] = []
        uname = self.username

        # Split by separators
        for sep in [".", "-", "_", " "]:
            if sep in uname:
                parts = uname.split(sep)
                if len(parts) == 2:
                    pairs.append((parts[0], parts[1]))
                    pairs.append((parts[1], parts[0]))  # reversed
                elif len(parts) >= 3:
                    pairs.append((parts[0], parts[-1]))
                    pairs.append((parts[0], "".join(parts[1:])))

        # CamelCase split
        camel_parts = re.findall(r"[A-Z][a-z]+", uname)
        if len(camel_parts) == 2:
            pairs.append((camel_parts[0].lower(), camel_parts[1].lower()))
            pairs.append((camel_parts[1].lower(), camel_parts[0].lower()))

        # Initial + name: e.g. "jsmith" → ("j", "smith") if len > 4
        alpha_only = re.sub(r"\d+", "", uname).lower()
        if len(alpha_only) > 3:
            pairs.append((alpha_only[0], alpha_only[1:]))
            # Try splitting at various positions
            for i in range(2, min(len(alpha_only) - 1, 6)):
                p1, p2 = alpha_only[:i], alpha_only[i:]
                if len(p1) >= 2 and len(p2) >= 2:
                    pairs.append((p1, p2))

        return pairs

    # ------------------------------------------------------------------
    # Name permutations (original + expanded with Anarchy patterns)
    # ------------------------------------------------------------------
    def name_permutations(
        self,
        first_name: str = "",
        last_name: str = "",
        middle_name: str = "",
    ) -> list[str]:
        """Generate username patterns from real name components."""
        if not first_name and not last_name:
            return []

        results = set()

        # Original basic permutations
        f = first_name.lower().strip()
        l = last_name.lower().strip()
        fi = f[0] if f else ""
        li = l[0] if l else ""

        for sep in self.SEPARATORS:
            if f and l:
                results.add(f + sep + l)
                results.add(l + sep + f)
                results.add(fi + sep + l)
                results.add(f + sep + li)
                results.add(fi + sep + li)
                results.add(l + sep + fi)
                results.add(li + sep + f)
                for num in self.BIRTH_YEARS_SHORT[:10] + self.COMMON_NUMBERS[:10]:
                    results.add(f + sep + l + num)
                    results.add(l + sep + f + num)
                    results.add(fi + l + num)
            elif f:
                results.add(f)
                for num in self.BIRTH_YEARS_SHORT[:10] + self.COMMON_NUMBERS[:10]:
                    results.add(f + num)
            elif l:
                results.add(l)
                for num in self.BIRTH_YEARS_SHORT[:10] + self.COMMON_NUMBERS[:10]:
                    results.add(l + num)

        # Username-Anarchy formats
        results.update(self.anarchy_formats(first_name, last_name, middle_name))

        return list(results)

    # ------------------------------------------------------------------
    # Phonetic algorithms
    # ------------------------------------------------------------------
    @staticmethod
    def soundex(name: str) -> str:
        """Classic Soundex algorithm (returns 4-char code)."""
        if not name:
            return ""
        name = name.upper()
        code = name[0]
        mapping = {
            "B": "1", "F": "1", "P": "1", "V": "1",
            "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
            "D": "3", "T": "3",
            "L": "4",
            "M": "5", "N": "5",
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
            "PH": "F", "CK": "K", "SCH": "SK", "GH": "F",
            "KN": "N", "WR": "R", "AE": "E", "GN": "N",
            "MB": "M", "PN": "N",
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

    # ------------------------------------------------------------------
    # Levenshtein distance
    # ------------------------------------------------------------------
    @staticmethod
    def levenshtein(a: str, b: str) -> int:
        """Compute Levenshtein edit distance between two strings."""
        if len(a) < len(b):
            return NicknameGenerator.levenshtein(b, a)
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
        return [
            w for w in wordlist
            if self.levenshtein(target, w.lower()) <= max_distance
        ]

    # ==================================================================
    # Alt-account correlation helpers (Research #2)
    # ==================================================================

    def similarity_score(self, other: str) -> float:
        """
        Compute a normalized similarity score (0.0–1.0) between this
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
                sub = a[start:start + length]
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
        score = (
            lev_sim * 0.30
            + soundex_match * 0.15
            + metaphone_match * 0.15
            + substr_ratio * 0.20
            + base_match * 0.20
        )
        return round(min(score, 1.0), 3)

    def find_alt_accounts(
        self,
        candidates: list[str],
        threshold: float = 0.55,
    ) -> list[tuple[str, float]]:
        """
        From a list of candidate usernames, find probable alt-accounts
        by computing similarity scores and filtering above threshold.
        """
        scored = []
        for c in candidates:
            if c.lower() == self.username.lower():
                continue
            sim = self.similarity_score(c)
            if sim >= threshold:
                scored.append((c, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Master generator
    # ------------------------------------------------------------------
    def generate_all(
        self,
        first_name: str = "",
        last_name: str = "",
        middle_name: str = "",
    ) -> list[str]:
        """
        Generate all probable nickname variants using all techniques.

        Returns a deduplicated, sorted list capped at ``max_variants``.
        """
        all_variants: set[str] = set()
        all_variants.add(self.username)
        all_variants.add(self.username.lower())

        # Apply all generators
        for gen_method in [
            self.leetspeak_variants,
            self.homoglyph_variants,
            self.prefix_suffix_variants,
            self.separator_variants,
            self.numeric_variants,
            self.transposition_variants,
            self.deletion_variants,
            self.case_variants,
        ]:
            all_variants.update(gen_method())

        # Name permutations (includes Anarchy formats)
        if first_name or last_name:
            all_variants.update(
                self.name_permutations(first_name, last_name, middle_name)
            )

        # String decomposition → auto-detect name parts → generate more
        if not first_name and not last_name:
            pairs = self.decompose_username()
            for f, l in pairs[:5]:  # limit to top 5 decompositions
                all_variants.update(self.anarchy_formats(f, l))

        # Remove empty and original
        all_variants.discard("")

        # Sort: original first, then by length, then alphabetically
        original = self.username.lower()
        sorted_variants = sorted(
            all_variants,
            key=lambda v: (v.lower() != original, len(v), v.lower()),
        )

        return sorted_variants[:self.max_variants]
