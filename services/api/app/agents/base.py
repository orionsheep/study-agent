from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TutorTurnContext(BaseModel):
    student_id: str = "demo-student"
    course_id: str = "ai-course"
    conversation_id: str = "demo-conversation"
    message: str
    requested_skill: str | None = None
    context_payload: dict[str, Any] = Field(default_factory=dict)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    model_provider: str | None = None
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    last_assistant_answer: str | None = None
    recent_apps: list[dict[str, Any]] = Field(default_factory=list)
    recent_resources: list[dict[str, Any]] = Field(default_factory=list)
    # 学生画像与掌握度记忆 —— 让 Hermes 生成内容时能因人而异。
    # 单次查询、多处消费(沿用 recent_messages 的模式)。
    profile: dict[str, Any] = Field(default_factory=dict)
    student_memories: list[dict[str, Any]] = Field(default_factory=list)
    current_topic: str | None = None
    current_objective: str | None = None
    image_data: list[str] | None = None


class AgentPlan(BaseModel):
    task_type: str
    steps: list[str]
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    trace: list[str] = Field(default_factory=list)
