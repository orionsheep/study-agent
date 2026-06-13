from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


MemoryType = Literal[
    "profile",
    "mastery",
    "misconception",
    "resource_preference",
    "learning_event",
    "learning_path",
    "agent_state",
    "spatial_layout",
    "app_interaction",
    "resource_feedback",
    "session_summary",
    "tutor_pedagogy",
]

EvidenceType = Literal[
    "chat",
    "quiz",
    "resource_feedback",
    "app_interaction",
    "spatial_layout",
    "teacher_confirmed",
    "system_inferred",
    "verifier_result",
]


class EduMemoryItem(BaseModel):
    id: str | None = None
    student_id: str
    course_id: str | None = None
    knowledge_point_id: str | None = None
    memory_type: MemoryType
    content: str
    structured_payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1, default=0.5)
    importance: float = Field(ge=0, le=1, default=0.5)
    decay_rate: float = Field(ge=0, default=0.0)
    evidence_type: EvidenceType
    source_event_id: str | None = None
    source_agent: str | None = None
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_until: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MemorySearchRequest(BaseModel):
    student_id: str
    course_id: str | None = None
    knowledge_point_id: str | None = None
    memory_types: list[MemoryType] = Field(default_factory=list)
    query: str | None = None
    limit: int = 10


class MemoryConflictDecision(BaseModel):
    old_memory_id: str
    new_evidence: EduMemoryItem
    decision: Literal["keep_old", "replace_old", "merge", "mark_conflict"]
    old_confidence_after: float
    new_confidence_after: float
    explanation: str
