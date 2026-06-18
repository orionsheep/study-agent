from fastapi.testclient import TestClient
from uuid import uuid4

from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import EduMemoryItem
from app.core.session import SessionHeaders
from app.database.store import get_store
from app.main import ChatRequest, app, build_tutor_context


client = TestClient(app)


def test_profile_extract_api_persists_fresh_user_profile_and_evidence():
    student_id = "closed-loop-profile-student"
    response = client.post(
        "/api/profile/extract",
        json={
            "student_id": student_id,
            "course_id": "ai-course",
            "conversation_id": "closed-loop",
            "message": "我是软件工程大一，Python 一般，数学推导弱，喜欢图解和代码，想学神经网络，希望按小步练习推进。",
        },
    )

    assert response.status_code == 200
    body = response.json()
    profile = body["profile"]

    assert len(profile) >= 8
    for key in [
        "major",
        "grade",
        "knowledge_foundation",
        "learning_goal",
        "cognitive_style",
        "learning_pace",
        "weak_points",
        "preferred_resources",
    ]:
        assert key in profile

    profile_response = client.get(f"/api/profile/{student_id}")
    assert profile_response.status_code == 200
    saved = profile_response.json()
    assert len(saved["profile"]) >= 8
    assert any(item["memory_type"] == "profile" and item["evidence_type"] == "chat" for item in saved["evidence"])


def test_memory_write_applies_repetition_and_conflict_policy():
    student_id = "closed-loop-conflict-student"
    memory = EduMem0Client()

    first = memory.add(
        EduMemoryItem(
            student_id=student_id,
            memory_type="profile",
            content="student says good at calculus",
            structured_payload={"dimensions": {"knowledge_foundation": "good at calculus"}},
            confidence=0.42,
            importance=0.7,
            decay_rate=0.0,
            evidence_type="chat",
            source_agent="profile_agent",
            tags=["profile"],
        )
    )
    repeated = memory.add(
        EduMemoryItem(
            student_id=student_id,
            memory_type="profile",
            content="student says good at calculus",
            structured_payload={"dimensions": {"knowledge_foundation": "good at calculus"}},
            confidence=0.42,
            importance=0.7,
            decay_rate=0.0,
            evidence_type="chat",
            source_agent="profile_agent",
            tags=["profile"],
        )
    )
    conflict = memory.add(
        EduMemoryItem(
            student_id=student_id,
            memory_type="misconception",
            content="quiz shows calculus errors",
            structured_payload={"topic": "calculus", "misconception_tags": ["symbolic_derivation"]},
            confidence=0.84,
            importance=0.9,
            decay_rate=0.08,
            evidence_type="quiz",
            source_agent="evaluator_agent",
            tags=["misconception", "calculus"],
        )
    )

    assert repeated.confidence > first.confidence
    assert "conflict" in conflict.tags
    assert conflict.structured_payload["conflict_decision"]["decision"] in {"replace_old", "mark_conflict"}


def test_resource_feedback_updates_preference_memory_and_dashboard():
    student_id = "closed-loop-feedback-student"
    response = client.post(
        "/api/memory/resource-feedback",
        json={
            "student_id": student_id,
            "resource_id": "res-doc-gradient",
            "preference": "图解讲义",
            "sentiment": "negative",
            "rating": 2,
            "comment": "图很多，但我更想要代码练习。",
        },
    )

    assert response.status_code == 200
    memory_item = response.json()["memory"]
    assert memory_item["memory_type"] == "resource_preference"
    assert memory_item["evidence_type"] == "resource_feedback"

    dashboard = client.get(f"/api/dashboard/{student_id}").json()
    assert any(item["memory_type"] == "resource_preference" for item in dashboard["memory_evidence"])


def test_tutor_context_memory_recall_filters_types_before_recent_limit():
    student_id = "closed-loop-context-recall-student"
    course_id = "ai-course"
    store = get_store()
    store.create_memory(
        EduMemoryItem(
            student_id=student_id,
            course_id=course_id,
            memory_type="profile",
            content="学生是软件工程大一，数学推导弱，偏好图解和代码。",
            structured_payload={"dimensions": {"grade": "大一", "major": "软件工程"}},
            confidence=0.82,
            importance=0.9,
            evidence_type="chat",
            source_event_id="context-recall-profile",
            tags=["profile"],
        )
    )
    for index in range(30):
        store.create_memory(
            EduMemoryItem(
                student_id=student_id,
                course_id=course_id,
                memory_type="spatial_layout",
                content=f"在画布上调整了一个学习 App 的位置 {index}",
                confidence=0.76,
                importance=0.7,
                evidence_type="spatial_layout",
                source_event_id=f"context-recall-layout-{index}",
                tags=["spatial_layout"],
            )
        )

    context = build_tutor_context(
        ChatRequest(
            student_id=student_id,
            course_id=course_id,
            conversation_id="context-recall-conv",
            message="帮我把上面的内容整理成一个 PPT",
        ),
        SessionHeaders(
            x_student_id=student_id,
            x_course_id=course_id,
            x_conversation_id="context-recall-conv",
        ),
    )

    assert any(memory["type"] == "profile" and "数学推导弱" in memory["content"] for memory in context.student_memories)
    assert all(memory["type"] != "spatial_layout" for memory in context.student_memories)


def test_build_tutor_context_keeps_semantic_chat_history_after_operational_noise():
    store = get_store()
    suffix = uuid4().hex
    student_id = f"context-history-student-{suffix}"
    course_id = "ai-course"
    conversation_id = f"context-history-conv-{suffix}"

    store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="user",
        text="先给我讲一下二次函数的基本概念。",
    )
    store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="我们刚才聊的是二次函数：标准形式是 y=ax²+bx+c，图像是一条抛物线。",
    )
    for index in range(28):
        store.save_chat_message(
            student_id=student_id,
            course_id=course_id,
            conversation_id=conversation_id,
            role="assistant",
            text=f"✅ 正在生成交互模型 {index}",
            metadata={"run_id": f"run-operational-{index}", "background_generated": True},
        )

    context = build_tutor_context(
        ChatRequest(
            student_id=student_id,
            course_id=course_id,
            conversation_id=conversation_id,
            message="你还记得我们刚才聊了什么吗？",
        ),
        SessionHeaders(
            x_student_id=student_id,
            x_course_id=course_id,
            x_conversation_id=conversation_id,
        ),
    )

    assert context.last_assistant_answer == "我们刚才聊的是二次函数：标准形式是 y=ax²+bx+c，图像是一条抛物线。"
    assert any("二次函数" in str(item.get("text") or "") for item in context.recent_messages)
    assert all("正在生成交互模型" not in str(item.get("text") or "") for item in context.recent_messages)
