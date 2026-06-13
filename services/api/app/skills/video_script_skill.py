from __future__ import annotations

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class VideoScriptSkill(BaseResourceSkill):
    skill_name = "video_script_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        resource = LearningResource(
            type="video_script",
            title=f"{data.topic} 60 秒动画脚本",
            target_topic=data.topic,
            content={
                "storyboard": ["山谷视角引入损失函数", "点沿负梯度移动", "学习率过大时越过谷底"],
                "narration": "我们把损失看作地形，学习率就是每一步的步长。",
                "visual_prompts": ["clean educational animation", "loss curve", "moving point"],
                "keyframes": [{"t": 0, "scene": "overview"}, {"t": 20, "scene": "stable update"}, {"t": 45, "scene": "overshoot"}],
                "related_app": "math.gradient_descent_demo",
            },
            source_refs=refs,
            personalized_reason="把抽象优化过程变成可回放的分镜。",
            tags=["video_script"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["created_storyboard", "linked_demo_app"])
        self.validate(output)
        return output
