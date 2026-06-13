from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.edumem0.client import EduMem0Client
from app.database.store import get_store


class ProfileAgentInput(BaseModel):
    student_id: str
    course_id: str = "ai-course"
    message: str


class ProfileAgentOutput(AgentOutput):
    dimensions: dict


class ProfileAgent:
    name = "profile_agent"

    def run(self, data: ProfileAgentInput) -> ProfileAgentOutput:
        client = EduMem0Client()
        memories = client.extract_from_chat(data.student_id, data.message, course_id=data.course_id)
        store = get_store()
        profile = store.get_profile(data.student_id, course_id=data.course_id)
        for memory in memories:
            memory.course_id = memory.course_id or data.course_id
            dims = memory.structured_payload.get("dimensions", {})
            for key, value in dims.items():
                if key == "preferred_resources" and isinstance(value, list):
                    existing = profile.get(key, [])
                    profile[key] = sorted(set(existing + value))
                else:
                    profile[key] = value
        store.save_profile(data.student_id, profile, course_id=data.course_id)
        return ProfileAgentOutput(
            summary="已更新学习画像，并写入 EduMem0 证据链。",
            payload={"profile": profile, "memories": [item.model_dump() for item in memories]},
            trace=["extracted_dimensions", "persisted_profile_memory"],
            dimensions=profile,
        )
