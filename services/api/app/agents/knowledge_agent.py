from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.rag.knowledge_graph import KnowledgeGraphBuilder
from app.rag.retriever import CourseRetriever


class KnowledgeAgentInput(BaseModel):
    course_id: str = "ai-course"
    topic: str = "梯度下降"


class KnowledgeAgent:
    name = "knowledge_agent"

    def run(self, data: KnowledgeAgentInput) -> AgentOutput:
        retriever = CourseRetriever()
        graph = KnowledgeGraphBuilder().graph(data.course_id)
        chunks = retriever.retrieve(data.topic, course_id=data.course_id)
        return AgentOutput(
            summary=f"已检索 {data.topic} 的课程上下文和知识图谱。",
            payload={"chunks": chunks, "knowledge_graph": graph},
            trace=["retrieved_chunks", "loaded_prerequisite_edges"],
        )
