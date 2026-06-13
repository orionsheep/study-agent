from __future__ import annotations

from pathlib import Path


class DocumentLoader:
    def load_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")
