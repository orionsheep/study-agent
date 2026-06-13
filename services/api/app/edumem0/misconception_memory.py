from app.schemas.app_protocol import EduMemoryItem


def misconception_memory(student_id: str, topic: str, tags: list[str], course_id: str | None = None) -> EduMemoryItem:
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        knowledge_point_id=topic,
        memory_type="misconception",
        content=f"{topic} 出现误区：{', '.join(tags)}",
        structured_payload={"topic": topic, "misconception_tags": tags},
        confidence=0.84,
        importance=0.9,
        decay_rate=0.08,
        evidence_type="quiz",
        source_agent="evaluator_agent",
        tags=["misconception", *tags],
    )
