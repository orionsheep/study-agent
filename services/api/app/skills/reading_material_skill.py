from __future__ import annotations

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class ReadingMaterialSkill(BaseResourceSkill):
    skill_name = "reading_material_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        resource = LearningResource(
            type="reading",
            title=f"{data.topic} 延伸阅读路线",
            target_topic=data.topic,
            content={
                "why_recommended": "当前路径需要把直觉扩展到更正式的优化器概念。",
                "prerequisite": "先完成学习率互动演示。",
                "reading_guide": ["先读课程讲义引用段", "再比较动量与自适应学习率", "最后写 3 句总结"],
            },
            source_refs=refs,
            personalized_reason="避免过早阅读高难材料，先补齐先修。",
            tags=["reading"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["curated_reading_path", "attached_prerequisite"])
        self.validate(output)
        return output
