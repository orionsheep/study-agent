from __future__ import annotations

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class MindmapSkill(BaseResourceSkill):
    skill_name = "mindmap_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        refs = self.source_refs(data.topic)
        resource = LearningResource(
            type="mindmap",
            title=f"{data.topic} 知识导图",
            target_topic=data.topic,
            content={
                "format": "mermaid_mindmap",
                "nodes": [
                    {"id": "root", "label": data.topic},
                    {"id": "pre", "label": "先修知识", "highlight": "weak_point"},
                    {"id": "demo", "label": "互动演示", "app_type": "math.gradient_descent_demo"},
                    {"id": "quiz", "label": "诊断练习", "app_type": "quiz.practice"},
                ],
                "edges": [["root", "pre"], ["root", "demo"], ["demo", "quiz"]],
            },
            source_refs=refs,
            personalized_reason="把先修和练习入口放在同一张图里。",
            tags=["mindmap"],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["created_hierarchy", "linked_canvas_nodes"])
        self.validate(output)
        return output
