from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.skills.base import SkillInput
from app.skills.resource_bundle_skill import ResourceBundleSkill


class ResourceBundleAgentInput(BaseModel):
    student_id: str
    course_id: str = "ai-course"
    topic: str = "梯度下降"


class ResourceBundleAgent:
    name = "resource_bundle_agent"

    def run(self, data: ResourceBundleAgentInput) -> AgentOutput:
        output = ResourceBundleSkill().run(SkillInput(student_id=data.student_id, course_id=data.course_id, topic=data.topic))
        return AgentOutput(summary="已生成 5 类以上资源包并完成验证。", payload=output.payload, trace=["planned_bundle", *output.trace])
