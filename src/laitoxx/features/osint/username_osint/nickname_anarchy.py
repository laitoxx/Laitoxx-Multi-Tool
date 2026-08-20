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


class AnarchyVariantsMixin:
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
        last = last_name.lower().strip()
        m = middle_name.lower().strip()
        fi = f[0] if f else ""  # first initial
        li = last[0] if last else ""  # last initial
        mi = m[0] if m else ""  # middle initial

        # --- 24 format plugins ---

        # 1. first
        if f:
            results.add(f)

        # 2. firstlast
        if f and last:
            results.add(f + last)

        # 3. first.last
        if f and last:
            results.add(f + "." + last)

        # 4. firstlast[8] - truncated to 8 chars
        if f and last:
            results.add((f + last)[:8])

        # 5. first[4]last[4] - 4 chars of each
        if f and last:
            results.add(f[:4] + last[:4])

        # 6. firstl - first name + last initial
        if f and li:
            results.add(f + li)

        # 7. f.last - first initial + dot + last
        if fi and last:
            results.add(fi + "." + last)

        # 8. flast - first initial + last
        if fi and last:
            results.add(fi + last)

        # 9. lfirst - last + first (reversed)
        if last and f:
            results.add(last + f)

        # 10. last.first - last + dot + first
        if last and f:
            results.add(last + "." + f)

        # 11. lastf - last + first initial
        if last and fi:
            results.add(last + fi)

        # 12. last
        if last:
            results.add(last)

        # 13. last.f - last + dot + first initial
        if last and fi:
            results.add(last + "." + fi)

        # 14. last.first
        if last and f:
            results.add(last + "." + f)

        # 15. FLast - capitalized first initial + last
        if fi and last:
            results.add(fi.upper() + last.capitalize())

        # 16. first1 - first + single digit (0-9)
        if f:
            for d in range(10):
                results.add(f + str(d))

        # 17. fl - first initial + last initial
        if fi and li:
            results.add(fi + li)

        # 18. fmlast - first initial + middle initial + last
        if fi and mi and last:
            results.add(fi + mi + last)

        # 19. firstmiddlelast - all three concatenated
        if f and m and last:
            results.add(f + m + last)

        # 20. fml - first + middle + last initials
        if fi and mi and li:
            results.add(fi + mi + li)

        # 21. FL - uppercase first + last initials
        if fi and li:
            results.add(fi.upper() + li.upper())

        # 22. FirstLast - capitalized each
        if f and last:
            results.add(f.capitalize() + last.capitalize())

        # 23. First.Last - capitalized with dot
        if f and last:
            results.add(f.capitalize() + "." + last.capitalize())

        # 24. Last - just capitalized last
        if last:
            results.add(last.capitalize())

        # --- Extra: digit range patterns (%D, %DD) ---
        if f and last:
            base_fl = f + last
            # Single digit: 0-9
            for d in range(10):
                results.add(base_fl + str(d))
            # Double digit: 00-99 (sample, not all 100)
            for dd in [0, 1, 11, 22, 33, 42, 55, 66, 69, 77, 88, 99]:
                results.add(base_fl + f"{dd:02d}")

        # --- Extra: separator variants for key patterns ---
        if f and last:
            for sep in [".", "-", "_"]:
                results.add(f + sep + last)
                results.add(last + sep + f)
                results.add(fi + sep + last)
                results.add(last + sep + fi)

        return list(results)
