from __future__ import annotations


class ConfidencePolicy:
    def score(self, evidence_type: str, repeated_count: int = 1, contradicted: bool = False) -> float:
        base = {
            "chat": 0.42,
            "quiz": 0.82,
            "teacher_confirmed": 0.96,
            "resource_feedback": 0.68,
            "app_interaction": 0.62,
            "spatial_layout": 0.76,
            "system_inferred": 0.56,
            "verifier_result": 0.88,
        }.get(evidence_type, 0.5)
        if repeated_count >= 2:
            base = max(base, 0.65)
        if repeated_count >= 4:
            base = max(base, 0.78)
        if contradicted:
            base *= 0.55
        return round(min(1.0, max(0.05, base)), 3)

    def merge(self, old_confidence: float, new_confidence: float) -> float:
        return round(min(1.0, old_confidence * 0.65 + new_confidence * 0.55), 3)
