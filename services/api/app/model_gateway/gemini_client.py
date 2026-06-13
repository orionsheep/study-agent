from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

import httpx

from app.core.config import get_settings, missing_secret
from app.model_gateway.base import ChatMessage, GatewayStatus
from app.model_gateway.errors import ModelGatewayError, ProviderBlocked


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiClient:
    name = "gemini"
    adapter = "google_generate_content"

    def __init__(self) -> None:
        self.settings = get_settings()

    def model_name(self) -> str:
        return self.settings.gemini_text_model.removeprefix("models/")

    def _headers(self) -> dict[str, str]:
        if missing_secret(self.settings.gemini_api_key):
            raise ProviderBlocked("blocked_missing_credentials", "GEMINI_API_KEY is not configured.")
        return {"x-goog-api-key": self.settings.gemini_api_key, "Content-Type": "application/json"}

    def _image_part(self, data_url: str) -> dict[str, Any]:
        """Convert a data URL (data:image/...;base64,...) to a Gemini inlineData part."""
        import base64 as _b64
        import re as _re
        m = _re.match(r"data:(image/[\w+\-.]+);base64,(.+)", data_url)
        if m:
            mime = m.group(1)
            raw = m.group(2)
            return {"inlineData": {"mimeType": mime, "data": raw}}
        # Fallback: treat as raw base64 JPEG
        return {"inlineData": {"mimeType": "image/jpeg", "data": data_url}}

    def serialize_messages(self, messages: list[ChatMessage]) -> dict[str, Any]:
        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                system_parts.append({"text": message.content})
                continue
            role = "model" if message.role == "assistant" else "user"
            parts: list[dict[str, Any]] = [{"text": message.content}]
            if message.images:
                for img in message.images:
                    parts.append(self._image_part(img))
            contents.append({"role": role, "parts": parts})
        if not contents:
            contents.append({"role": "user", "parts": [{"text": ""}]})
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": self.settings.gemini_max_tokens},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        return payload

    async def _complete_with_model(self, model: str, messages: list[ChatMessage]) -> dict[str, Any]:
        payload = self.serialize_messages(messages)
        model_id = model.removeprefix("models/")
        timeout = httpx.Timeout(float(self.settings.gemini_timeout_seconds), connect=float(self.settings.gemini_connect_timeout_seconds))
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{GEMINI_BASE_URL}/models/{model_id}:generateContent", headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        data.setdefault("model", model_id)
        return data

    async def complete(self, messages: list[ChatMessage], stream: bool = False) -> dict[str, Any]:
        errors: list[str] = []
        models = [self.settings.gemini_text_model, self.settings.gemini_text_fallback_model]
        for index, model in enumerate(dict.fromkeys(item for item in models if item)):
            attempts = 3 if index == 0 else 1
            for attempt in range(attempts):
                try:
                    data = await self._complete_with_model(model, messages)
                    data["fallback_used"] = index > 0
                    data["attempt"] = attempt + 1
                    return data
                except httpx.HTTPStatusError as exc:
                    body = exc.response.text[:500] if exc.response is not None else ""
                    errors.append(f"{model} attempt {attempt + 1}: Gemini HTTP {exc.response.status_code}: {body}")
                    if exc.response is not None and exc.response.status_code < 500:
                        break
                except httpx.ConnectTimeout as exc:
                    errors.append(f"{model} attempt {attempt + 1}: Gemini connection timed out after {self.settings.gemini_connect_timeout_seconds}s: {type(exc).__name__}")
                    raise ModelGatewayError("; ".join(errors)) from exc
                except httpx.TimeoutException as exc:
                    errors.append(f"{model} attempt {attempt + 1}: Gemini request timed out after {self.settings.gemini_timeout_seconds}s: {type(exc).__name__}")
                except httpx.HTTPError as exc:
                    errors.append(f"{model} attempt {attempt + 1}: Gemini HTTP transport error: {type(exc).__name__}: {exc}")
                if attempt < attempts - 1:
                    await asyncio.sleep(0.8 * (attempt + 1))
        raise ModelGatewayError("; ".join(errors) or "Gemini request failed.")

    def extract_assistant_text(self, response: dict[str, Any]) -> str:
        candidates = response.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", []) if isinstance(candidates[0], dict) else []
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict) and isinstance(part.get("text"), str)]
        return "".join(text_parts)

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        response = await self.complete(messages, stream=False)
        text = self.extract_assistant_text(response)
        if text:
            yield text

    async def validate_connection(self) -> GatewayStatus:
        if missing_secret(self.settings.gemini_api_key):
            return GatewayStatus(
                name="gemini",
                status="blocked_missing_credentials",
                reason="GEMINI_API_KEY is missing; real provider check was not attempted.",
                configured_model=self.settings.gemini_text_model,
                adapter=self.adapter,
            )
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(f"{GEMINI_BASE_URL}/models", headers=self._headers())
                response.raise_for_status()
            return GatewayStatus(name="gemini", status="ready", reason="Gemini models endpoint responded.", configured_model=self.settings.gemini_text_model, adapter=self.adapter)
        except Exception as exc:
            return GatewayStatus(name="gemini", status="blocked_provider_error", reason=f"Gemini provider check failed: {exc}", configured_model=self.settings.gemini_text_model, adapter=self.adapter)
