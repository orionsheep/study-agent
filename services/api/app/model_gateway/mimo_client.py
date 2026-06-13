from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from app.core.config import get_settings, missing_secret
from app.model_gateway.base import ChatMessage, GatewayStatus
from app.model_gateway.errors import ModelGatewayError, ProviderBlocked


class MiMoClient:
    name = "mimo"
    adapter = "openai_compatible_http"

    def __init__(self) -> None:
        self.settings = get_settings()

    def model_name(self) -> str:
        return self.settings.mimo_text_model

    def serialize_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for message in messages:
            content: Any = message.content
            if message.images:
                parts: list[dict[str, Any]] = [{"type": "text", "text": message.content}]
                for img in message.images:
                    parts.append({"type": "image_url", "image_url": {"url": img, "detail": "auto"}})
                content = parts
            item: dict[str, Any] = {"role": message.role, "content": content}
            if self.settings.mimo_use_thinking and message.reasoning_content:
                item["reasoning_content"] = message.reasoning_content
            serialized.append(item)
        return serialized

    def _headers(self) -> dict[str, str]:
        if missing_secret(self.settings.mimo_api_key):
            raise ProviderBlocked("blocked_missing_credentials", "MIMO_API_KEY is not configured.")
        return {"api-key": self.settings.mimo_api_key, "Content-Type": "application/json"}

    async def complete(self, messages: list[ChatMessage], stream: bool = False) -> dict[str, Any]:
        payload = {
            "model": self.settings.mimo_text_model,
            "messages": self.serialize_messages(messages),
            "stream": stream,
            "max_tokens": self.settings.mimo_max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.settings.mimo_timeout_seconds), connect=10.0)) as client:
                response = await client.post(f"{self.settings.mimo_base_url.rstrip('/')}/chat/completions", headers=self._headers(), json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise ModelGatewayError(f"MiMo request timed out after {self.settings.mimo_timeout_seconds}s: {type(exc).__name__}") from exc
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500] if exc.response is not None else ""
            raise ModelGatewayError(f"MiMo HTTP {exc.response.status_code}: {body}") from exc
        except httpx.HTTPError as exc:
            raise ModelGatewayError(f"MiMo HTTP transport error: {type(exc).__name__}: {exc}") from exc

    def extract_assistant_text(self, response: dict[str, Any]) -> str:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    elif isinstance(item, str):
                        parts.append(item)
                return "".join(parts)
        text = first.get("text")
        return text if isinstance(text, str) else ""

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        payload = {
            "model": self.settings.mimo_text_model,
            "messages": self.serialize_messages(messages),
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.settings.mimo_timeout_seconds), connect=10.0)) as client:
            async with client.stream("POST", f"{self.settings.mimo_base_url.rstrip('/')}/chat/completions", headers=self._headers(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line

    async def validate_connection(self) -> GatewayStatus:
        if missing_secret(self.settings.mimo_api_key):
            return GatewayStatus(
                name="mimo",
                status="blocked_missing_credentials",
                reason="MIMO_API_KEY is missing; real provider check was not attempted.",
                configured_model=self.settings.mimo_text_model,
                adapter=self.adapter,
            )
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(f"{self.settings.mimo_base_url.rstrip('/')}/models", headers=self._headers())
                response.raise_for_status()
            return GatewayStatus(
                name="mimo",
                status="ready",
                reason="MiMo OpenAI-compatible endpoint responded.",
                configured_model=self.settings.mimo_text_model,
                adapter=self.adapter,
            )
        except Exception as exc:
            return GatewayStatus(
                name="mimo",
                status="blocked_provider_error",
                reason=f"MiMo provider check failed: {exc}",
                configured_model=self.settings.mimo_text_model,
                adapter=self.adapter,
            )
