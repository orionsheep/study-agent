from __future__ import annotations


class CourseParser:
    def parse_markdown(self, text: str) -> dict:
        sections = [line.strip("# ") for line in text.splitlines() if line.startswith("#")]
        return {"text": text, "sections": sections}
