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


class NicknameDiscoveryMixin:
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
            all_variants.update(self.name_permutations(first_name, last_name, middle_name))

        # String decomposition → auto-detect name parts → generate more
        if not first_name and not last_name:
            pairs = self.decompose_username()
            for f, last in pairs[:5]:  # limit to top 5 decompositions
                all_variants.update(self.anarchy_formats(f, last))

        # Remove empty and original
        all_variants.discard("")

        # Sort: original first, then by length, then alphabetically
        original = self.username.lower()
        sorted_variants = sorted(
            all_variants,
            key=lambda v: (v.lower() != original, len(v), v.lower()),
        )

        return sorted_variants[: self.max_variants]
