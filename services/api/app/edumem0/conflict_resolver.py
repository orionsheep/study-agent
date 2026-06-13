from __future__ import annotations

from app.edumem0.schemas import MemoryConflictDecision
from app.schemas.app_protocol import EduMemoryItem


class ConflictResolver:
    def detect(self, old_memory: EduMemoryItem, new_evidence: EduMemoryItem) -> bool:
        old_text = old_memory.content.lower()
        new_text = new_evidence.content.lower()
        pairs = [
            ("good at calculus", "calculus errors"),
            ("喜欢图解", "不喜欢图解"),
            ("掌握", "错误"),
            ("weak", "correct streak"),
            ("数学推导弱", "推导正确率提升"),
        ]
        return any(left in old_text and right in new_text for left, right in pairs)

    def resolve(self, old_memory: EduMemoryItem, new_evidence: EduMemoryItem) -> MemoryConflictDecision:
        if not self.detect(old_memory, new_evidence):
            return MemoryConflictDecision(
                old_memory_id=old_memory.id,
                new_evidence=new_evidence.model_dump(),
                decision="merge",
                old_confidence_after=old_memory.confidence,
                new_confidence_after=new_evidence.confidence,
                explanation="新证据与旧记忆互补，合并进入同一证据链。",
            )
        if new_evidence.confidence >= old_memory.confidence:
            return MemoryConflictDecision(
                old_memory_id=old_memory.id,
                new_evidence=new_evidence.model_dump(),
                decision="replace_old",
                old_confidence_after=round(old_memory.confidence * 0.55, 3),
                new_confidence_after=new_evidence.confidence,
                explanation="新证据更强且更新，降低旧记忆置信度并采用新判断。",
            )
        return MemoryConflictDecision(
            old_memory_id=old_memory.id,
            new_evidence=new_evidence.model_dump(),
            decision="mark_conflict",
            old_confidence_after=round(old_memory.confidence * 0.75, 3),
            new_confidence_after=round(new_evidence.confidence * 0.75, 3),
            explanation="证据冲突但强度接近，保留双方并等待后续验证。",
        )
