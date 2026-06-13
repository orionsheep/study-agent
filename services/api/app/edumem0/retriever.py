from __future__ import annotations

from app.edumem0.store import EduMemoryStore
from app.schemas.app_protocol import EduMemoryItem


class MemoryRetriever:
    def __init__(self, store: EduMemoryStore | None = None) -> None:
        self.store = store or EduMemoryStore()

    def get_profile_context(self, student_id: str, course_id: str | None = None) -> list[EduMemoryItem]:
        return self.store.search(student_id, memory_types=["profile"], course_id=course_id, limit=12)

    def get_planner_context(self, student_id: str, course_id: str, topic: str) -> list[EduMemoryItem]:
        return self.store.search(
            student_id,
            query=topic,
            memory_types=["profile", "mastery", "misconception", "learning_path"],
            course_id=course_id,
            limit=16,
        )

    def get_tutor_context(self, student_id: str, app_id: str | None = None, course_id: str | None = None) -> list[EduMemoryItem]:
        query = app_id if app_id else None
        return self.store.search(
            student_id,
            query=query,
            memory_types=["profile", "app_interaction", "misconception", "session_summary"],
            course_id=course_id,
            limit=16,
        )

    def get_resource_generation_context(self, student_id: str, course_id: str, topic: str) -> list[EduMemoryItem]:
        return self.store.search(
            student_id,
            query=topic,
            memory_types=["profile", "resource_preference", "mastery"],
            course_id=course_id,
            limit=16,
        )

    def get_dashboard_context(self, student_id: str, course_id: str | None = None) -> list[EduMemoryItem]:
        return self.store.list_for_student(student_id, course_id=course_id, limit=30)

    def get_canvas_context(self, student_id: str, conversation_id: str, course_id: str | None = None) -> list[EduMemoryItem]:
        return self.store.search(
            student_id,
            query=conversation_id,
            memory_types=["spatial_layout", "app_interaction"],
            course_id=course_id,
            limit=20,
        )
