from __future__ import annotations

from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import EduMemoryItem


class Mem0CompatibleAdapter:
    """Small adapter exposing add/search/update/delete-shaped operations for EduMem0."""

    def __init__(self, client: EduMem0Client | None = None) -> None:
        self.client = client or EduMem0Client()

    def add(self, item: EduMemoryItem) -> EduMemoryItem:
        return self.client.add(item)

    def search(self, student_id: str, query: str | None = None, limit: int = 10) -> list[EduMemoryItem]:
        return self.client.search(student_id, query=query, limit=limit)

    def update(self, item: EduMemoryItem) -> EduMemoryItem:
        item.version += 1
        return self.client.add(item)

    def delete(self, student_id: str, memory_id: str) -> bool:
        store = self.client.store.store
        store.execute("DELETE FROM edu_memories WHERE student_id=? AND id=?", (student_id, memory_id))
        return True
