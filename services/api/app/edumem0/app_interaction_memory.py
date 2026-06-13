from app.schemas.app_protocol import EduMemoryItem


def app_interaction_memory(
    student_id: str,
    app_id: str,
    event_type: str,
    payload: dict,
    course_id: str | None = None,
    knowledge_point_id: str | None = None,
) -> EduMemoryItem:
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        knowledge_point_id=knowledge_point_id,
        memory_type="app_interaction",
        content=f"{app_id} 交互：{event_type}",
        structured_payload={"app_id": app_id, "event_type": event_type, "payload": payload},
        confidence=0.62,
        importance=0.68,
        decay_rate=0.04,
        evidence_type="app_interaction",
        source_agent="memory_agent",
        tags=["app_interaction", event_type],
    )
