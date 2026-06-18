from app.schemas.app_protocol import EduMemoryItem


def path_memory(student_id: str, path_id: str, summary: str, course_id: str | None = None) -> EduMemoryItem:
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        memory_type="learning_path",
        source_event_id=f"edumem0:{student_id}:learning_path:{path_id}",
        content=summary,
        structured_payload={"path_id": path_id},
        confidence=0.74,
        importance=0.78,
        decay_rate=0.025,
        evidence_type="system_inferred",
        source_agent="planner_agent",
        tags=["learning_path"],
    )
