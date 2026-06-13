from __future__ import annotations

import math


class DeterministicEmbedder:
    def embed(self, text: str) -> list[float]:
        length = max(1, len(text))
        vowels = sum(1 for char in text.lower() if char in "aeiou")
        cjk = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        return [round(math.log(length + 1), 4), round(vowels / length, 4), round(cjk / length, 4)]
