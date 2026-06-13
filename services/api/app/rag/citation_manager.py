from __future__ import annotations


class CitationManager:
    def source_ref(self, document_id: str, chunk_id: str, course_id: str, section: str, confidence: float = 0.9) -> dict:
        return {
            "document_id": document_id,
            "chunk_id": chunk_id,
            "course_id": course_id,
            "chapter": "人工智能导论",
            "section": section,
            "quote_span": [0, 24],
            "confidence": confidence,
        }
