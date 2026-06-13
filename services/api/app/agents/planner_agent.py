from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.database.store import get_store
from app.edumem0.path_memory import path_memory
from app.schemas.app_protocol import LearningPath, LearningPathStage


class PlannerAgentInput(BaseModel):
    student_id: str
    course_id: str = "ai-course"
    topic: str = "神经网络"


class PlannerAgent:
    name = "planner_agent"

    @staticmethod
    def _list_field(profile: dict, key: str) -> list[str]:
        value = profile.get(key)
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return [str(value)]

    def run(self, data: PlannerAgentInput) -> AgentOutput:
        store = get_store()
        profile = store.get_profile(data.student_id, course_id=data.course_id) or {}
        weak_points = self._list_field(profile, "weak_points")
        weak_math = any("数学" in item for item in weak_points) or "数学" in str(profile)
        stages = [
            LearningPathStage(
                stage_id="stage-math",
                title="补齐数学推导基础",
                status="in_progress" if weak_math else "recommended",
                mastery_required=0.55,
                current_mastery=0.38 if weak_math else 0.58,
                recommended_resource_ids=["res-doc-gradient"],
                app_ids=["app-gradient"],
                reason="数学推导弱点需要先用图解与代码补齐。" if weak_math else "快速复习先修后进入优化。",
            ),
            LearningPathStage(
                stage_id="stage-opt",
                title="梯度下降与学习率",
                status="recommended",
                mastery_required=0.65,
                current_mastery=0.42,
                recommended_resource_ids=["res-quiz-gradient", "res-code-lab"],
                app_ids=["app-gradient", "app-quiz"],
                reason="该阶段直接支撑神经网络训练。",
            ),
            LearningPathStage(
                stage_id="stage-nn",
                title=f"{data.topic} 训练闭环",
                status="locked",
                mastery_required=0.75,
                current_mastery=0.25,
                recommended_resource_ids=["res-mindmap"],
                app_ids=["app-knowledge"],
                reason="完成优化基础后解锁。",
            ),
        ]
        path = LearningPath(
            path_id="path-neural-network",
            title=f"{data.topic} 个性化学习路径",
            current_stage_id=stages[0].stage_id,
            overall_progress=0.32,
            stages=stages,
            next_actions=["打开梯度下降实验台", "完成诊断题", "总结到笔记 App"],
        )
        store.save_path(data.student_id, data.course_id, path)
        memory = path_memory(data.student_id, path.path_id, f"已生成 {data.topic} 学习路径。", course_id=data.course_id)
        store.create_memory(memory)
        return AgentOutput(summary="已生成个性化学习路径。", payload={"path": path.model_dump(), "memory": memory.model_dump()}, trace=["read_profile", "built_path", "wrote_path_memory"])
