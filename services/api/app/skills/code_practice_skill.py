from __future__ import annotations

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class CodePracticeSkill(BaseResourceSkill):
    skill_name = "code_practice_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        resource = LearningResource(
            type="code_practice",
            title=f"{data.topic} Python 实验",
            target_topic=data.topic,
            content={
                "goal": "用安全的本地示例理解梯度下降迭代。",
                "environment": "浏览器内只展示代码和期望输出，后端不执行任意代码。",
                "starter_code": "lr = 0.18\nx = 4.0\nfor step in range(8):\n    grad = 2 * x\n    x = x - lr * grad\n    print(step, round(x, 3))",
                "expected_output": "x 逐步接近 0。",
                "tests": ["x decreases for a stable learning rate", "large lr shows instability in explanation"],
                "extension_task": "把 lr 改成 1.2，观察为什么会震荡。",
            },
            source_refs=refs,
            personalized_reason="把数学公式转成可读 Python 循环。",
            tags=["code", "safety"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["created_lab", "checked_code_policy"])
        self.validate(output)
        return output
