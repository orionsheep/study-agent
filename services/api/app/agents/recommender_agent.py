from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.database.store import get_store


class RecommenderAgentInput(BaseModel):
    student_id: str
    course_id: str = "ai-course"
    topic: str = "梯度下降"


class RecommenderAgent:
    name = "recommender_agent"

    def run(self, data: RecommenderAgentInput) -> AgentOutput:
        store = get_store()
        profile = store.get_profile(data.student_id, course_id=data.course_id)
        resources = store.list_resources(data.student_id, course_id=data.course_id)
        ranked = []
        for resource in resources:
            profile_match = 0.35 if resource.type in {"mindmap", "code_practice", "quiz"} else 0.22
            weakness_match = 0.3 if "数学" in str(profile.get("weak_points", [])) and resource.type in {"document", "quiz"} else 0.18
            goal_match = 0.25 if data.topic in resource.target_topic or data.topic in resource.title else 0.16
            feedback_score = 0.18
            score = round(profile_match + weakness_match + goal_match + feedback_score, 3)
            ranked.append({"resource_id": resource.resource_id, "title": resource.title, "score": score, "reason": "匹配画像、弱点与当前目标。"})
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return AgentOutput(summary="已根据画像和弱点排序资源。", payload={"recommendations": ranked}, trace=["scored_profile_match", "scored_weakness_match", "ranked_resources"])
