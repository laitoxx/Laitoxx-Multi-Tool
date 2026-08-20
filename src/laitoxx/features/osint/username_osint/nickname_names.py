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


class NameVariantsMixin:
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
        last = last_name.lower().strip()
        fi = f[0] if f else ""
        li = last[0] if last else ""

        for sep in self.SEPARATORS:
            if f and last:
                results.add(f + sep + last)
                results.add(last + sep + f)
                results.add(fi + sep + last)
                results.add(f + sep + li)
                results.add(fi + sep + li)
                results.add(last + sep + fi)
                results.add(li + sep + f)
                for num in self.BIRTH_YEARS_SHORT[:10] + self.COMMON_NUMBERS[:10]:
                    results.add(f + sep + last + num)
                    results.add(last + sep + f + num)
                    results.add(fi + last + num)
            elif f:
                results.add(f)
                for num in self.BIRTH_YEARS_SHORT[:10] + self.COMMON_NUMBERS[:10]:
                    results.add(f + num)
            elif last:
                results.add(last)
                for num in self.BIRTH_YEARS_SHORT[:10] + self.COMMON_NUMBERS[:10]:
                    results.add(last + num)

        # Username-Anarchy formats
        results.update(self.anarchy_formats(first_name, last_name, middle_name))

        return list(results)
