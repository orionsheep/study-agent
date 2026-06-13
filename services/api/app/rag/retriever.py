from __future__ import annotations

from app.database.store import LearningStore, get_store


class CourseRetriever:
    def __init__(self, store: LearningStore | None = None) -> None:
        self.store = store or get_store()

    def retrieve(self, topic: str, limit: int = 3, course_id: str | None = None, *, min_score: float = 6.0) -> list[dict]:
        return self.store.retrieve_chunks(topic, limit=limit, course_id=course_id, min_score=min_score)

    def context_with_refs(self, topic: str, limit: int = 3, course_id: str | None = None) -> dict:
        chunks = self.retrieve(topic, limit=limit, course_id=course_id)
        source_refs = [chunk["source_ref"] for chunk in chunks]
        return {
            "topic": topic,
            "course_id": course_id,
            "context": "\n".join(chunk["content"] for chunk in chunks),
            "source_refs": source_refs,
            "chunks": chunks,
            "has_relevant_context": bool(chunks),
            "retrieval_policy": "relevance_gated_no_fallback",
            "retrieval_note": (
                "RAG evidence is included only when the query has explicit lexical anchors "
                "or high semantic relevance; otherwise the tutor should answer from the model normally."
            ),
        }
