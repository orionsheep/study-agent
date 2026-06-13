from __future__ import annotations

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class DocumentSkill(BaseResourceSkill):
    skill_name = "document_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        resource = LearningResource(
            type="document",
            title=f"{data.topic} 个性化讲义",
            target_topic=data.topic,
            difficulty="入门到进阶",
            content={
                "learning_objectives": [f"解释 {data.topic} 的核心概念", "用例子连接公式和直觉"],
                "explanation": f"围绕 {data.topic}，先给直觉，再给公式，再做小练习。",
                "example": "把损失函数看作山谷，负梯度方向就是下坡方向。",
                "common_mistakes": ["学习率过大", "忽略先修概念", "只背公式不看轨迹"],
                "summary": f"{data.topic} 学习重点是概念、来源证据和练习闭环。",
            },
            source_refs=refs,
            personalized_reason="根据画像优先提供图解、代码和短练习。",
            estimated_minutes=12,
            tags=["document", "personalized"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["built_markdown_sections", "attached_source_refs"])
        self.validate(output)
        return output
