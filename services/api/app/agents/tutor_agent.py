from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
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
        if data.app_id:
            text = f"我看到了 {data.app_id} 的最新交互。先观察数值变化，再把它和公式联系起来：{context['context'][:120]}"
        elif "总结" in data.message or "笔记" in data.message:
            text = "我已把本轮关键结论、公式、Demo 观察和下一步动作整理成 Notes App。"
        elif "动能" in data.message:
            text = "动能定理可以帮你建立“变化量”的直觉：合外力做功对应动能变化，类似优化里一步更新带来的损失变化。"
        else:
            text = f"我们按“直觉 -> 公式 -> 互动 -> 练习”的节奏学习 {data.topic}。我会把关键材料放到左侧 App Canvas。"
        return AgentOutput(summary=text, payload={"source_refs": context["source_refs"]}, trace=["retrieved_rag_context", "prepared_markdown_response"])
