from __future__ import annotations

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class PPTSkill(BaseResourceSkill):
    skill_name = "ppt_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        resource = LearningResource(
            type="ppt",
            title=f"{data.topic} 微课幻灯片",
            target_topic=data.topic,
            content={
                "slides": [
                    {"title": "问题引入", "speaker_notes": "从学习者弱点进入。"},
                    {"title": "核心概念", "speaker_notes": "展示公式和图解。"},
                    {"title": "互动任务", "speaker_notes": "连接 Demo App。"},
                ],
                "export_url": "artifact://ppt/gradient-descent-outline",
                "preview_metadata": {"slide_count": 3},
            },
            source_refs=refs,
            personalized_reason="先图解再练习，适合当前画像。",
            tags=["ppt"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["built_slide_outline", "attached_speaker_notes"])
        self.validate(output)
        return output
