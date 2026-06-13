from __future__ import annotations

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class QuizSkill(BaseResourceSkill):
    skill_name = "quiz_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        questions = [
            {
                "question_type": "single_choice",
                "prompt": "学习率过大时，梯度下降最可能怎样？",
                "options": ["稳定加速", "震荡或发散", "自动停止", "无需损失函数"],
                "answer": "震荡或发散",
                "explanation": "步长越过低谷会导致损失反复变大或震荡。",
                "knowledge_point_id": "kp-optimization",
                "difficulty": "adaptive",
                "misconception_tags": ["learning_rate_too_large"],
                "source_refs": refs,
            },
            {
                "question_type": "true_false",
                "prompt": "负梯度方向通常指向局部下降最快的方向。",
                "answer": True,
                "explanation": "在一阶近似下，负梯度方向是局部最快下降方向。",
                "knowledge_point_id": "kp-optimization",
                "difficulty": "adaptive",
                "misconception_tags": ["gradient_direction"],
                "source_refs": refs,
            },
        ]
        resource = LearningResource(
            type="quiz",
            title=f"{data.topic} 练习组",
            target_topic=data.topic,
            content={"questions": questions},
            source_refs=refs,
            personalized_reason="用短题检测误区，再把结果写入掌握度记忆。",
            estimated_minutes=8,
            tags=["quiz", "evaluation"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["generated_question_set", "validated_answers"])
        self.validate(output)
        return output
