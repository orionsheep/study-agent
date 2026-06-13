from __future__ import annotations

from pydantic import BaseModel


class ImageGatewayStatus(BaseModel):
    name: str
    status: str
    reason: str
    configured_model: str | None = None


class ImageRequest(BaseModel):
    prompt: str
    overlay_labels: list[dict] = []
    teaching_goal: str


class ImageResult(BaseModel):
    provider: str
    prompt: str
    image_url: str | None = None
    provider_response_id: str | None = None
    overlay_labels: list[dict] = []
    metadata: dict = {}
