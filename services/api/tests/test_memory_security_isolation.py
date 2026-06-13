from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.edumem0.client import EduMem0Client
from app.database.store import get_store
from app.main import app
from app.schemas.app_protocol import EduMemoryItem


client = TestClient(app)


def iso_ts(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(timespec="seconds")


def test_student_context_mismatch_is_forbidden():
    response = client.get(
        "/api/dashboard/security-target-student",
        headers={"X-Student-Id": "security-header-student", "X-Course-Id": "ai-course"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN_STUDENT_CONTEXT"


def test_memory_search_is_scoped_to_course():
    student_id = "course-isolation-student"
    memory = EduMem0Client()
    memory.add(
        EduMemoryItem(
            student_id=student_id,
            course_id="course-alpha",
            knowledge_point_id="kp-shared",
            memory_type="mastery",
            content="shared topic alpha mastery evidence",
            structured_payload={"topic": "shared-topic", "course": "alpha"},
            confidence=0.82,
            importance=0.9,
            decay_rate=0.0,
            evidence_type="quiz",
            tags=["mastery", "shared-topic"],
        )
    )
    memory.add(
        EduMemoryItem(
            student_id=student_id,
            course_id="course-beta",
            knowledge_point_id="kp-shared",
            memory_type="mastery",
            content="shared topic beta mastery evidence",
            structured_payload={"topic": "shared-topic", "course": "beta"},
            confidence=0.82,
            importance=0.9,
            decay_rate=0.0,
            evidence_type="quiz",
            tags=["mastery", "shared-topic"],
        )
    )

    response = client.post(
        "/api/memory/search",
        headers={"X-Student-Id": student_id, "X-Course-Id": "course-alpha"},
        json={"student_id": student_id, "course_id": "course-alpha", "query": "shared-topic", "limit": 10},
    )

    assert response.status_code == 200
    memories = response.json()["memories"]
    assert memories
    assert {item["course_id"] for item in memories} == {"course-alpha"}


def test_memory_search_orders_by_effective_confidence_after_decay():
    student_id = "decay-ranking-student"
    memory = EduMem0Client()
    memory.add(
        EduMemoryItem(
            student_id=student_id,
            course_id="decay-course",
            memory_type="resource_preference",
            content="decay-topic old high confidence signal",
            structured_payload={"topic": "decay-topic", "age": "old"},
            confidence=0.95,
            importance=1.0,
            decay_rate=0.5,
            evidence_type="resource_feedback",
            valid_from=iso_ts(10),
            tags=["decay-topic"],
        )
    )
    fresh = memory.add(
        EduMemoryItem(
            student_id=student_id,
            course_id="decay-course",
            memory_type="resource_preference",
            content="decay-topic fresh moderate confidence signal",
            structured_payload={"topic": "decay-topic", "age": "fresh"},
            confidence=0.4,
            importance=1.0,
            decay_rate=0.0,
            evidence_type="resource_feedback",
            valid_from=iso_ts(0),
            tags=["decay-topic"],
        )
    )

    results = memory.search(student_id, query="decay-topic", course_id="decay-course", limit=2)

    assert results[0].id == fresh.id
    assert results[0].effective_confidence == 0.4
    assert results[1].decayed is True


def test_source_event_id_is_idempotent_within_course():
    student_id = "idempotent-student"
    source_event_id = "event-idempotent-1"
    store = get_store()
    memory = EduMem0Client()

    memory.add(
        EduMemoryItem(
            student_id=student_id,
            course_id="idempotent-course",
            memory_type="app_interaction",
            content="idempotent signal first",
            structured_payload={"step": 1},
            confidence=0.5,
            importance=0.5,
            decay_rate=0.0,
            evidence_type="app_interaction",
            source_event_id=source_event_id,
            tags=["idempotent"],
        )
    )
    replay = memory.add(
        EduMemoryItem(
            student_id=student_id,
            course_id="idempotent-course",
            memory_type="app_interaction",
            content="idempotent signal replay",
            structured_payload={"step": 2},
            confidence=0.7,
            importance=0.6,
            decay_rate=0.0,
            evidence_type="app_interaction",
            source_event_id=source_event_id,
            tags=["idempotent", "replay"],
        )
    )

    memories = [
        item
        for item in store.list_memories(student_id, course_id="idempotent-course", limit=20)
        if item.source_event_id == source_event_id
    ]
    assert len(memories) == 1
    assert replay.version == 2
    assert replay.structured_payload["idempotent_replay"] is True
