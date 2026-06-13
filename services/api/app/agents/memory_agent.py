from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import AppEvent


class MemoryAgentInput(BaseModel):
    student_id: str
    course_id: str = "ai-course"
    message: str | None = None
    app_event: dict | None = None


class MemoryAgent:
    name = "memory_agent"

    def run(self, data: MemoryAgentInput) -> AgentOutput:
        client = EduMem0Client()
        if data.message:
            memories = client.extract_from_chat(data.student_id, data.message, course_id=data.course_id)
        elif data.app_event:
            data.app_event["course_id"] = data.course_id
            memories = [client.record_app_event(AppEvent.model_validate(data.app_event))]
        else:
            memories = []
        return AgentOutput(summary="记忆已更新。", payload={"memories": [item.model_dump() for item in memories]}, trace=["applied_memory_policy", "persisted_memory"])
