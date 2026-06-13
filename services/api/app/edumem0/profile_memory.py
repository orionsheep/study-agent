from app.schemas.app_protocol import EduMemoryItem


def profile_memory(student_id: str, dimensions: dict, course_id: str | None = None) -> EduMemoryItem:
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        memory_type="profile",
        content=f"学习画像更新：{dimensions}",
        structured_payload={"dimensions": dimensions},
        confidence=0.68,
        importance=0.8,
        decay_rate=0.0,
        evidence_type="chat",
        source_agent="profile_agent",
        tags=["profile"],
    )
