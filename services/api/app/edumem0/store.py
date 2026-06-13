from __future__ import annotations

from app.database.store import LearningStore, get_store
from app.schemas.app_protocol import EduMemoryItem


class EduMemoryStore:
    def __init__(self, store: LearningStore | None = None) -> None:
        self.store = store or get_store()

    def add(self, item: EduMemoryItem) -> EduMemoryItem:
        return self.store.create_memory(item)

    def search(
        self,
        student_id: str,
        query: str | None = None,
        memory_types: list[str] | None = None,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        limit: int = 10,
    ) -> list[EduMemoryItem]:
        return self.store.search_memories(
            student_id,
            query=query,
            memory_types=memory_types,
            course_id=course_id,
            knowledge_point_id=knowledge_point_id,
            limit=limit,
        )

    def list_for_student(self, student_id: str, course_id: str | None = None, limit: int = 50) -> list[EduMemoryItem]:
        return self.store.list_memories(student_id, course_id=course_id, limit=limit)
