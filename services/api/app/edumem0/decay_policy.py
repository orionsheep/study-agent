from __future__ import annotations

from datetime import datetime, timezone


class DecayPolicy:
    def rate_for_type(self, memory_type: str) -> float:
        if memory_type in {"mastery", "misconception"}:
            return 0.08
        if memory_type in {"profile", "spatial_layout"}:
            return 0.0
        if memory_type in {"resource_preference", "learning_path"}:
            return 0.025
        return 0.04

    def apply(self, confidence: float, decay_rate: float, valid_from: datetime, now: datetime | None = None) -> float:
        if decay_rate <= 0:
            return confidence
        current = now or datetime.now(timezone.utc)
        if valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        days = max(0, (current - valid_from).days)
        return round(max(0.05, confidence * ((1 - decay_rate) ** days)), 3)
