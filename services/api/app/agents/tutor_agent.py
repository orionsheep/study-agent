from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.database.store import get_store
from app.rag.retriever import CourseRetriever


class TutorAgentInput(BaseModel):
    student_id: str
    course_id: str = "ai-course"
    message: str
    app_id: str | None = None
    topic: str = "梯度下降"


class TutorAgent:
    name = "tutor_agent"

    def run(self, data: TutorAgentInput) -> AgentOutput:
        context = CourseRetriever().context_with_refs(data.topic, course_id=data.course_id)
        trace = ["retrieved_rag_context"]
        # 读取该学生的掌握度/误区记忆 + 画像,让回答因人而异。
        # 之前是纯硬编码话术(不读任何记忆),现在先注入个性化上下文。
        store = get_store()
        profile = store.get_profile(data.student_id, course_id=data.course_id) or {}
        memories = store.search_memories(
            data.student_id,
            query=data.topic,
            memory_types=["mastery", "misconception"],
            course_id=data.course_id,
            limit=8,
        ) or []
        weak_points = profile.get("weak_points") or []
        misconceptions = [m for m in memories if m.memory_type == "misconception"]
        low_mastery = [
            m for m in memories
            if m.memory_type == "mastery" and (m.confidence or 0) < 0.6
        ]

        # 拼接个性化上下文前缀:告诉学生"我记得你的弱点"。
        personal_prefix = self._personal_prefix(weak_points, misconceptions, low_mastery)
        if personal_prefix:
            trace.append("loaded_student_memory")

        if data.app_id:
            text = f"我看到了 {data.app_id} 的最新交互。先观察数值变化，再把它和公式联系起来：{context['context'][:120]}"
        elif "总结" in data.message or "笔记" in data.message:
            text = "我已把本轮关键结论、公式、Demo 观察和下一步动作整理成 Notes App。"
        elif "动能" in data.message:
            text = "动能定理可以帮你建立“变化量”的直觉：合外力做功对应动能变化，类似优化里一步更新带来的损失变化。"
        else:
            text = f"我们按“直觉 -> 公式 -> 互动 -> 练习”的节奏学习 {data.topic}。我会把关键材料放到左侧 App Canvas。"

        if personal_prefix:
            text = f"{personal_prefix}\n\n{text}"
        return AgentOutput(
            summary=text,
            payload={
                "source_refs": context["source_refs"],
                "weak_points": weak_points,
                "misconception_count": len(misconceptions),
                "low_mastery_count": len(low_mastery),
            },
            trace=[*trace, "prepared_markdown_response"],
        )

    @staticmethod
    def _personal_prefix(
        weak_points: list, misconceptions: list, low_mastery: list
    ) -> str:
        """根据记忆生成一段个性化开场白。空数据时返回空串(不注入噪音)。"""
        parts: list[str] = []
        if weak_points:
            joined = "、".join(str(w) for w in weak_points[:3])
            parts.append(f"根据你之前的学习记录，你在 {joined} 上还需要加强")
        if misconceptions:
            tags = []
            for m in misconceptions[:3]:
                tags.extend(m.structured_payload.get("misconception_tags", []) or [m.content[:20]])
            unique_tags = list(dict.fromkeys(str(t) for t in tags))[:3]
            if unique_tags:
                parts.append(f"你之前在「{'、'.join(unique_tags)}」上踩过坑，这轮我们重点避开")
        if low_mastery:
            topics = list(dict.fromkeys(
                str(m.knowledge_point_id or m.content[:16]) for m in low_mastery[:3]
            ))
            parts.append(f"这几块你掌握得还不够扎实：{'、'.join(topics)}，我会讲得更细")
        if not parts:
            return ""
        return "我记得你的情况——" + "；".join(parts) + "。"
