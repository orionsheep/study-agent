from datetime import datetime, timedelta

from app.edumem0.confidence_policy import ConfidencePolicy
from app.edumem0.conflict_resolver import ConflictResolver
from app.edumem0.decay_policy import DecayPolicy
from app.edumem0.extractor import MemoryExtractor
from app.schemas.app_protocol import EduMemoryItem


def test_confidence_policy_repeated_and_quiz_evidence():
    policy = ConfidencePolicy()
    assert policy.score("chat", repeated_count=1) < policy.score("chat", repeated_count=3)
    assert policy.score("quiz") > policy.score("chat")
    assert policy.score("teacher_confirmed") > policy.score("quiz")


def test_decay_policy_keeps_spatial_layout_stable():
    policy = DecayPolicy()
    assert policy.rate_for_type("spatial_layout") == 0
    decayed = policy.apply(0.8, 0.08, datetime.utcnow() - timedelta(days=7))
    assert decayed < 0.8


def test_conflict_resolver_detects_and_explains():
    old = EduMemoryItem(student_id="s", memory_type="profile", content="student says good at calculus", evidence_type="chat")
    new = EduMemoryItem(student_id="s", memory_type="misconception", content="quiz shows calculus errors", evidence_type="quiz", confidence=0.85)
    decision = ConflictResolver().resolve(old, new)
    assert decision.decision in {"replace_old", "mark_conflict"}
    assert decision.explanation


def test_chat_extraction_creates_profile_memory():
    memories = MemoryExtractor().from_chat("demo-student", "我是软件工程大一，Python 一般，数学推导弱，喜欢图解和代码。")
    assert memories[0].memory_type == "profile"
    dims = memories[0].structured_payload["dimensions"]
    assert len(dims) >= 5
