from __future__ import annotations

from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import EduMemoryItem


class Mem0CompatibleAdapter:
    """为 EduMem0 提供 add/search/update/delete 形态的薄适配层。

    注意:类名里的 "Mem0" 只是历史命名,本系统并非真正的 Mem0 向量记忆库,
    也不调用 Mem0 云 API。EduMem0 是基于 edu_memories 关系表 + 关键词检索的
    自研记忆层。若需真正的语义向量记忆,应改接 Hermes MemoryProvider(见
    .runtime/hermes/plugins/edumem0/)或启用 mem0 云 provider。
    """

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
