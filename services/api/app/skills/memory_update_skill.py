from __future__ import annotations

from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import AppEvent
from app.skills.base import SkillInput, SkillOutput


class MemoryUpdateSkill:
    skill_name = "memory_update_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        client = EduMem0Client()
        if data.payload.get("message"):
            memories = client.extract_from_chat(data.student_id, data.payload["message"])
            return SkillOutput(skill_name=self.skill_name, payload={"memories": [item.model_dump() for item in memories]}, trace=["extracted_chat_memory"])
        if data.payload.get("app_event"):
            memory = client.record_app_event(AppEvent.model_validate(data.payload["app_event"]))
            return SkillOutput(skill_name=self.skill_name, payload={"memory": memory.model_dump()}, trace=["recorded_app_event_memory"])
        return SkillOutput(skill_name=self.skill_name, payload={"memories": []}, trace=["no_memory_payload"])
