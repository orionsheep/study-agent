from __future__ import annotations

from typing import Any, AsyncIterator, Protocol

from pydantic import BaseModel


class GatewayStatus(BaseModel):
    name: str
    status: str
    reason: str
    configured_model: str | None = None
    adapter: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str
    reasoning_content: str | None = None
    images: list[str] | None = None  # base64 data URLs or image URLs for multimodal


class ModelGateway(Protocol):
    async def complete(self, messages: list[ChatMessage], stream: bool = False) -> dict[str, Any]:
        ...

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        ...

    async def validate_connection(self) -> GatewayStatus:
        ...
