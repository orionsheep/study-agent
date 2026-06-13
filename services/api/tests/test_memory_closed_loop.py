from fastapi.testclient import TestClient

from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import EduMemoryItem
from app.main import app


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

