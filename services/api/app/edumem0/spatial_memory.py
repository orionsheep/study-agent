from app.schemas.app_protocol import EduMemoryItem


def spatial_memory(student_id: str, layout: dict) -> EduMemoryItem:
    return EduMemoryItem(
        student_id=student_id,
        memory_type="spatial_layout",
        source_event_id=f"edumem0:{student_id}:spatial_layout",
        content="画布布局已保存。",
        structured_payload={"layout": layout},
        confidence=0.78,
        importance=0.72,
        decay_rate=0.0,
        evidence_type="spatial_layout",
        source_agent="app_canvas_agent",
        tags=["spatial_layout"],
    )
