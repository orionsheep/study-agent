from __future__ import annotations

from typing import Any


class EvidenceBuilder:
    def chat(self, message: str) -> dict[str, Any]:
        return {"evidence_type": "chat", "quote": message[:160]}

    def quiz(self, question_id: str, is_correct: bool, tags: list[str]) -> dict[str, Any]:
        return {"evidence_type": "quiz", "question_id": question_id, "is_correct": is_correct, "misconception_tags": tags}

    def app_event(self, app_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"evidence_type": "app_interaction", "app_id": app_id, "event_type": event_type, "payload": payload}
