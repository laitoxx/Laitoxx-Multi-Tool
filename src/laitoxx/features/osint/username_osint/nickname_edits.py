"""Elementary transposition, deletion, and case variants."""


class NicknameEditMixin:
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

    def deletion_variants(self) -> list[str]:
        """Delete one character at a time."""
        results = set()
        for i in range(len(self.username)):
            variant = self.username[:i] + self.username[i + 1 :]
            if variant:
                results.add(variant.lower())
        return list(results)

    def case_variants(self) -> list[str]:
        results = set()
        results.add(self.username.lower())
        results.add(self.username.upper())
        results.add(self.username.capitalize())
        results.add(self.username.swapcase())
        results.discard(self.username)
        return list(results)
