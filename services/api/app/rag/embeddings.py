from __future__ import annotations

from functools import lru_cache
from typing import Literal

import httpx

from app.core.config import get_settings, missing_secret


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
EmbeddingTask = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY"]


@lru_cache(maxsize=512)
def _embed_cached(model: str, task_type: str, text: str) -> tuple[float, ...]:
    settings = get_settings()
    if missing_secret(settings.gemini_api_key) or not text.strip():
        return ()
    model_id = model.removeprefix("models/")
    payload = {
        "content": {"parts": [{"text": text[:12000]}]},
        "taskType": task_type,
    }
    timeout = httpx.Timeout(20.0, connect=float(settings.gemini_connect_timeout_seconds))
    try:
        response = httpx.post(
            f"{GEMINI_BASE_URL}/models/{model_id}:embedContent",
            headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        values = response.json().get("embedding", {}).get("values", [])
    except Exception:
        return ()
    return tuple(float(value) for value in values if isinstance(value, int | float))


def embed_text(text: str, task_type: EmbeddingTask = "RETRIEVAL_DOCUMENT") -> list[float]:
    settings = get_settings()
    # Use the strongest embedding model as requested
    model = "text-embedding-004" 
    return list(_embed_cached(model, task_type, text))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
