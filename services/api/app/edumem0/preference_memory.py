from app.schemas.app_protocol import EduMemoryItem


def preference_memory(
    student_id: str,
    preference: str,
    sentiment: str,
    course_id: str | None = None,
    knowledge_point_id: str | None = None,
) -> EduMemoryItem:
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        knowledge_point_id=knowledge_point_id,
        memory_type="resource_preference",
        content=f"学习资源偏好：{preference}，反馈：{sentiment}",
        structured_payload={"preference": preference, "sentiment": sentiment},
        confidence=0.68,
        importance=0.65,
        decay_rate=0.025,
        evidence_type="resource_feedback",
        source_agent="memory_agent",
        tags=["resource_preference"],
    )
