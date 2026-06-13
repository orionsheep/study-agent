from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.safety.verifier import ResourceVerifier
from app.schemas.app_protocol import LearningResource


class VerifierAgentInput(BaseModel):
    resource: dict


class VerifierAgent:
    name = "verifier_agent"

    def run(self, data: VerifierAgentInput) -> AgentOutput:
        resource = LearningResource.model_validate(data.resource)
        result = ResourceVerifier().verify(resource)
        return AgentOutput(summary="资源验证通过。" if result.passed else "资源验证未通过。", payload={"result": result.model_dump()}, trace=["checked_grounding", "checked_consistency", "checked_safety"])
