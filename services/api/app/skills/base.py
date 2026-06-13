from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.rag.retriever import CourseRetriever
from app.safety.verifier import ResourceVerifier
from app.schemas.app_protocol import LearningResource


class SkillInput(BaseModel):
    student_id: str = "demo-student"
    course_id: str = "ai-course"
    topic: str = "梯度下降"
    profile: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


class SkillOutput(BaseModel):
    skill_name: str
    resource: LearningResource | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    trace: list[str] = Field(default_factory=list)


class BaseResourceSkill:
    skill_name = "base_skill"
    resource_type = "document"

    def __init__(self) -> None:
        self.retriever = CourseRetriever()
        self.verifier = ResourceVerifier()

    def source_refs(self, topic: str) -> list[dict[str, Any]]:
        return self.retriever.context_with_refs(topic)["source_refs"]

    def validate(self, output: SkillOutput) -> bool:
        if output.resource:
            result = self.verifier.verify(output.resource)
            output.resource.quality_check = result
            return result.passed
        return True
