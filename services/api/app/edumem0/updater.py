from __future__ import annotations

from app.edumem0.confidence_policy import ConfidencePolicy
from app.edumem0.conflict_resolver import ConflictResolver
from app.edumem0.decay_policy import DecayPolicy
from app.edumem0.store import EduMemoryStore
from app.schemas.app_protocol import AppEvent, EduMemoryItem, utc_now


# Human-readable Chinese labels for canvas/app events — shown in the memory evidence chain.
# Avoids dumping raw payload dicts and English identifiers that users can't read.
_EVENT_LABELS: dict[str, str] = {
    "layout.drag": "在画布上调整了一个学习 App 的位置",
    "layout.group": "把多个学习 App 整理成了一组",
    "layout.save": "保存了当前的画布布局",
    "app.create": "在画布上新建了一个学习 App",
    "app.delete": "移除了画布上的一个学习 App",
    "app.open": "打开了一个学习 App",
    "app.focus": "聚焦查看了一个学习 App",
    "app.fullscreen": "全屏查看了一个学习 App",
    "app.minimize": "收起了一个学习 App",
    "tutor.explain": "请导师讲解了一个学习 App 的内容",
    "quiz.submit": "提交了一道练习题",
    "parameter_change": "调整了互动演示里的参数",
    "custom.preview": "预览了一个互动演示",
    "image.generate": "生成了一张教学图片",
    "notes.save": "保存了一段学习笔记",
}


def humanize_app_event(event: AppEvent) -> str:
    """Turn a raw app event into a natural Chinese sentence for the memory evidence chain."""
    label = _EVENT_LABELS.get(event.event_type, "与一个学习 App 进行了交互")
    payload = event.payload if isinstance(event.payload, dict) else {}
    position = payload.get("position") if isinstance(payload.get("position"), dict) else None
    if event.event_type == "layout.drag" and position:
        try:
            x = round(float(position.get("x", 0)))
            y = round(float(position.get("y", 0)))
            return f"{label}（移动到约 {x}, {y}）"
        except (TypeError, ValueError):
            return label
    return label


class MemoryUpdater:
    def __init__(self, store: EduMemoryStore | None = None) -> None:
        self.store = store or EduMemoryStore()
        self.confidence = ConfidencePolicy()
        self.conflict = ConflictResolver()
        self.decay = DecayPolicy()

    def write(self, item: EduMemoryItem) -> EduMemoryItem:
        item = self.apply_repetition_policy(item)
        item = self.apply_conflict_policy(item)
        return self.store.add(item)

    def apply_repetition_policy(self, item: EduMemoryItem) -> EduMemoryItem:
        existing = self.store.search(item.student_id, memory_types=[item.memory_type], course_id=item.course_id, limit=100)
        repeated_count = 1 + sum(1 for old in existing if self.same_signal(old, item))
        if repeated_count > 1:
            item.confidence = max(item.confidence, self.confidence.score(item.evidence_type, repeated_count=repeated_count))
            item.structured_payload = {
                **item.structured_payload,
                "repeated_evidence_count": repeated_count,
            }
        return item

    def apply_conflict_policy(self, item: EduMemoryItem) -> EduMemoryItem:
        for old in self.store.search(item.student_id, course_id=item.course_id, limit=100):
            if old.id == item.id or not self.conflict.detect(old, item):
                continue
            decision = self.conflict.resolve(old, item)
            old.confidence = decision.old_confidence_after
            old.structured_payload = {
                **old.structured_payload,
                "conflict_decision": decision.model_dump(mode="json"),
                "superseded_by": item.id,
            }
            old.tags = sorted(set([*old.tags, "conflict"]))
            old.updated_at = utc_now()
            self.store.add(old)
            item.confidence = decision.new_confidence_after
            item.structured_payload = {
                **item.structured_payload,
                "conflict_decision": decision.model_dump(mode="json"),
                "conflicts_with": old.id,
            }
            item.tags = sorted(set([*item.tags, "conflict"]))
            break
        return item

    def same_signal(self, old: EduMemoryItem, new: EduMemoryItem) -> bool:
        if old.content.strip().lower() == new.content.strip().lower():
            return True
        old_payload = old.structured_payload
        new_payload = new.structured_payload
        if old.memory_type == "profile":
            return old_payload.get("dimensions") == new_payload.get("dimensions")
        if old.knowledge_point_id and old.knowledge_point_id == new.knowledge_point_id:
            return bool(set(old.tags).intersection(new.tags))
        return False

    def from_app_event(self, event: AppEvent) -> EduMemoryItem:
        if event.event_type == "notes.save":
            content = str(event.payload.get("content") or "").strip()
            topic = str(event.payload.get("topic") or event.payload.get("title") or "学习笔记").strip()
            item = EduMemoryItem(
                student_id=event.student_id,
                course_id=event.course_id,
                knowledge_point_id=event.payload.get("knowledge_point_id") or event.payload.get("knowledgePointId"),
                memory_type="session_notes",
                content=f"用户保存了学习笔记：{topic}。{content[:240]}",
                structured_payload={
                    "app_id": event.app_id,
                    "course_id": event.course_id,
                    "conversation_id": event.conversation_id,
                    "topic": topic,
                    "content": content,
                },
                confidence=self.confidence.score("app_interaction", repeated_count=1),
                importance=0.76,
                decay_rate=0.01,
                evidence_type="notes_app",
                source_event_id=event.event_id,
                source_agent="notes_skill",
                tags=["session_notes", "notes.save", topic],
            )
            return self.write(item)
        memory_type = "spatial_layout" if event.event_type in {"layout.drag", "layout.group", "layout.save"} else "app_interaction"
        evidence_type = "spatial_layout" if memory_type == "spatial_layout" else "app_interaction"
        item = EduMemoryItem(
            student_id=event.student_id,
            course_id=event.course_id,
            knowledge_point_id=event.payload.get("knowledge_point_id") or event.payload.get("knowledgePointId"),
            memory_type=memory_type,
            content=humanize_app_event(event),
            structured_payload={
                "app_id": event.app_id,
                "course_id": event.course_id,
                "conversation_id": event.conversation_id,
                "event_type": event.event_type,
                "payload": event.payload,
            },
            confidence=self.confidence.score(evidence_type),
            importance=0.7,
            decay_rate=self.decay.rate_for_type(memory_type),
            evidence_type=evidence_type,
            source_event_id=event.event_id,
            source_agent="memory_agent",
            tags=[memory_type, event.event_type],
        )
        return self.write(item)
