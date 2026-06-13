from __future__ import annotations

from app.edumem0.extractor import MemoryExtractor
from app.edumem0.retriever import MemoryRetriever
from app.edumem0.store import EduMemoryStore
from app.edumem0.updater import MemoryUpdater
from app.schemas.app_protocol import AppEvent, EduMemoryItem


class EduMem0Client:
    def __init__(self) -> None:
        self.store = EduMemoryStore()
        self.extractor = MemoryExtractor()
        self.retriever = MemoryRetriever(self.store)
        self.updater = MemoryUpdater(self.store)

    def add(self, item: EduMemoryItem) -> EduMemoryItem:
        return self.updater.write(item)

    def search(
        self,
        student_id: str,
        query: str | None = None,
        memory_types: list[str] | None = None,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        limit: int = 10,
    ) -> list[EduMemoryItem]:
        return self.store.search(
            student_id,
            query=query,
            memory_types=memory_types,
            course_id=course_id,
            knowledge_point_id=knowledge_point_id,
            limit=limit,
        )

    def extract_from_chat(self, student_id: str, message: str, course_id: str | None = None) -> list[EduMemoryItem]:
        memories = self.extractor.from_chat(student_id, message, course_id=course_id)
        return [self.add(item) for item in memories]

    def record_app_event(self, event: AppEvent) -> EduMemoryItem:
        return self.updater.from_app_event(event)

    def get_profile_context(self, student_id: str, course_id: str | None = None) -> list[EduMemoryItem]:
        return self.retriever.get_profile_context(student_id, course_id=course_id)

    def get_dashboard_context(self, student_id: str, course_id: str | None = None) -> list[EduMemoryItem]:
        return self.retriever.get_dashboard_context(student_id, course_id=course_id)
