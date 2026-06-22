#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
os.environ.setdefault("DATABASE_URL", "postgresql://learnforge:learnforge@127.0.0.1:5432/learnforge")

from app.agents.base import TutorTurnContext  # noqa: E402
from app.agents.orchestrator_agent import OrchestratorAgent, UnifiedOrchestrator  # noqa: E402
from app.database.store import get_store  # noqa: E402
from app.schemas.app_protocol import LearningResource  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_capability_locks() -> None:
    agent = UnifiedOrchestrator()

    interactive = agent.plan_turn(TutorTurnContext(message="生成一个伯努利定律的可交互模型"))
    assert_true(interactive.payload["capability"] == "interactive_demo", "Bernoulli interactive request must lock interactive_demo")
    assert_true(interactive.payload["expected_app_types"] == ["custom.html"], "interactive_demo must expect custom.html")
    assert_true(interactive.payload["expected_resource_types"] == [], "interactive_demo must not require ppt resources")
    assert_true(interactive.payload["expected_artifact_kind"] == "interactive_model", "interactive_demo must require interactive_model artifact_kind")

    correction = agent.plan_turn(TutorTurnContext(message="我说的是生成可交互模型不是PPT"))
    assert_true(correction.payload["capability"] == "interactive_demo", "not-PPT correction must lock interactive_demo")

    ppt = agent.plan_turn(TutorTurnContext(message="请把上面聊天总结成PPT", last_assistant_answer="我们讨论了人船模型。"))
    assert_true(ppt.payload["capability"] == "ppt", "PPT request must lock ppt")
    assert_true(ppt.payload["expected_resource_types"] == ["ppt"], "PPT request must require ppt resource")
    assert_true(ppt.payload["expected_artifact_kind"] == "ppt_deck", "PPT request must require ppt_deck artifact_kind")


def validate_context_topics() -> None:
    agent = UnifiedOrchestrator()
    image = agent.plan_turn(
        TutorTurnContext(
            message="生成一张这个模型的图片",
            last_assistant_answer="上面讨论的是人船模型，核心是动量守恒。",
        )
    )
    assert_true("人船模型" in image.payload["topic"], "image follow-up must inherit human-boat topic")
    assert_true("神经网络" not in image.payload["topic"], "image follow-up must not fall back to neural-network seed topic")

    video_agent = OrchestratorAgent()
    video = video_agent.plan_turn(
        TutorTurnContext(
            message="找一下机械振动相关物理题目相关的视频",
            recent_messages=[{"role": "user", "text": "我说的是 生成可交互模型 不是PPT"}],
            last_assistant_answer="我会生成可交互模型，不生成 PPT。",
        )
    )
    assert_true("机械振动" in video.payload["topic"], "video query must keep current mechanical-vibration topic")
    assert_true("不是PPT" not in video.payload["topic"], "video query must reject correction text as topic")


def validate_video_filter() -> None:
    agent = OrchestratorAgent()
    teaching = LearningResource(
        resource_id="res-script-vibration-good",
        type="video",
        title="高中物理 机械振动 简谐运动 题目讲解",
        target_topic="机械振动",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVGOOD", "description": "机械振动 简谐运动 弹簧振子 物理 教学 题", "play": 100},
        source_refs=[],
        personalized_reason="mock good",
        tags=[],
    )
    bad = LearningResource(
        resource_id="res-script-vibration-bad",
        type="video",
        title="AI工具一键生成机械振动PPT模板",
        target_topic="机械振动",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVBAD", "description": "AI工具 PPT制作 演示文稿", "play": 999999},
        source_refs=[],
        personalized_reason="mock bad",
        tags=[],
    )
    filtered = agent.filter_video_resources("机械振动相关物理题目", [bad, teaching], limit=6)
    assert_true([item.resource_id for item in filtered] == [teaching.resource_id], "video filter must reject PPT/AI-tool drift")


def validate_resource_restore() -> None:
    store = get_store()
    suffix = uuid4().hex
    student_id = f"student-boundary-{suffix}"
    course_id = f"course-boundary-{suffix}"
    conversation_id = f"conversation-boundary-{suffix}"
    run_id = f"run-boundary-{suffix}"
    resource = LearningResource(
        resource_id=f"res-boundary-{suffix}",
        type="video",
        title="机械振动题目讲解",
        target_topic="机械振动",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVBOUNDARY", "bvid": "BVBOUNDARY"},
        source_refs=[],
        personalized_reason="boundary restore",
        tags=["机械振动"],
    )
    store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="boundary_test")
    message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="## 已找到视频\n\n- 机械振动题目讲解",
        metadata={"run_id": run_id},
    )
    store.create_chat_resource_link("msg-stream-boundary", resource.resource_id, run_id=run_id)
    messages = store.list_chat_messages(student_id=student_id, course_id=course_id, conversation_id=conversation_id, limit=5)
    restored = next(item for item in messages if item["id"] == message["id"])
    assert_true(restored["resources"][0]["resource_id"] == resource.resource_id, "chat history must restore linked resources")


def main() -> None:
    validate_capability_locks()
    validate_context_topics()
    validate_video_filter()
    validate_resource_restore()
    print("Artifact boundary validation passed")


if __name__ == "__main__":
    main()
