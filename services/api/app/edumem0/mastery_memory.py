from app.schemas.app_protocol import EduMemoryItem


def mastery_memory(student_id: str, topic: str, score: float, evidence_type: str = "quiz", course_id: str | None = None) -> EduMemoryItem:
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        knowledge_point_id=topic,
        memory_type="mastery",
        content=f"{topic} 掌握度更新为 {score:.2f}",
        structured_payload={"topic": topic, "score": score},
        confidence=0.82,
        importance=0.88,
        decay_rate=0.08,
        evidence_type=evidence_type,
        source_agent="evaluator_agent",
        tags=["mastery", topic],
    )
