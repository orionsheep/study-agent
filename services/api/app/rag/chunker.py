from __future__ import annotations


class TextChunker:
    def chunk(self, text: str, size: int = 420) -> list[str]:
        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) > size and current:
                chunks.append(current)
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append(current)
        return chunks
