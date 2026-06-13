from __future__ import annotations

from app.database.store import LearningStore, get_store


class KnowledgeGraphBuilder:
    def __init__(self, store: LearningStore | None = None) -> None:
        self.store = store or get_store()

    def graph(self, course_id: str = "ai-course") -> dict:
        return self.store.knowledge_graph(course_id)
