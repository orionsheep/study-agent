from __future__ import annotations

from app.image_gateway.prompt_planner import ImagePromptPlanner
from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class ImageGenerationSkill(BaseResourceSkill):
    skill_name = "image_generation_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        plan = ImagePromptPlanner().plan(data.topic, f"用图像解释 {data.topic} 的关键关系")
        resource = LearningResource(
            type="image",
            title=f"{data.topic} 图解资产",
            target_topic=data.topic,
            content={"image_prompt": plan.prompt, "overlay_labels": plan.overlay_labels, "teaching_goal": plan.teaching_goal},
            source_refs=refs,
            personalized_reason="图片由 Gemini/Nano Banana 生成，要求图内直接呈现清晰的简体中文学习信息。",
            tags=["gemini", "中文信息图"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["planned_image_prompt", "prepared_overlay_labels"])
        self.validate(output)
        return output
