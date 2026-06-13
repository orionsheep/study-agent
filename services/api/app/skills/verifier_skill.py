from __future__ import annotations

from app.safety.verifier import ResourceVerifier
from app.schemas.app_protocol import LearningResource
from app.skills.base import SkillInput, SkillOutput


class VerifierSkill:
    skill_name = "verifier_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        resource_data = data.payload.get("resource")
        if resource_data:
            resource = LearningResource.model_validate(resource_data)
            result = ResourceVerifier().verify(resource)
            return SkillOutput(skill_name=self.skill_name, payload={"result": result.model_dump()}, trace=["checked_schema", "checked_source_refs", "checked_safety"])
        return SkillOutput(skill_name=self.skill_name, payload={"result": {"passed": False, "issues": ["resource_missing"]}}, trace=["resource_missing"])
