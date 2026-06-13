from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import get_settings, missing_secret
from app.image_gateway.base import ImageGatewayStatus, ImageRequest, ImageResult
from app.model_gateway.errors import ModelGatewayError, ProviderBlocked
from app.model_gateway.gemini_client import GEMINI_BASE_URL


class GeminiImageClient:
    name = "gemini_image"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        if missing_secret(self.settings.gemini_api_key):
            raise ProviderBlocked("blocked_missing_credentials", "GEMINI_API_KEY is not configured.")
        return {"x-goog-api-key": self.settings.gemini_api_key, "Content-Type": "application/json"}

    def _payload(self, request: ImageRequest) -> dict[str, Any]:
        return {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {"aspectRatio": "16:9", "imageSize": "1K"},
            },
        }

    def extract_image(self, data: dict[str, Any]) -> tuple[str | None, str | None]:
        for candidate in data.get("candidates", []):
            parts = candidate.get("content", {}).get("parts", []) if isinstance(candidate, dict) else []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                inline = part.get("inlineData") or part.get("inline_data")
                if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                    return inline["data"], inline.get("mimeType") or inline.get("mime_type") or "image/png"
        return None, None

    async def _generate_with_model(self, model: str, request: ImageRequest) -> tuple[dict[str, Any], str | None, str | None]:
        model_id = model.removeprefix("models/")
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.settings.gemini_timeout_seconds), connect=10.0)) as client:
            response = await client.post(f"{GEMINI_BASE_URL}/models/{model_id}:generateContent", headers=self._headers(), json=self._payload(request))
            response.raise_for_status()
            data = response.json()
        image_data, mime_type = self.extract_image(data)
        return data, image_data, mime_type

    async def generate(self, request: ImageRequest) -> ImageResult:
        errors: list[str] = []
        models = [self.settings.gemini_image_model, self.settings.gemini_image_fallback_model]
        for index, model in enumerate(dict.fromkeys(item for item in models if item)):
            for attempt in range(3):
                try:
                    data, image_data, mime_type = await self._generate_with_model(model, request)
                    if not image_data:
                        errors.append(f"{model}: Gemini response did not contain inline image data.")
                        break
                    return ImageResult(
                        provider="gemini",
                        prompt=request.prompt,
                        image_url=f"data:{mime_type};base64,{image_data}",
                        provider_response_id=data.get("responseId"),
                        overlay_labels=request.overlay_labels,
                        metadata={
                            "model": model,
                            "fallback_used": index > 0,
                            "attempt": attempt + 1,
                            "mime_type": mime_type,
                            "teaching_goal": request.teaching_goal,
                        },
                    )
                except httpx.HTTPStatusError as exc:
                    body = exc.response.text[:500] if exc.response is not None else ""
                    errors.append(f"{model} attempt {attempt + 1}: Gemini image HTTP {exc.response.status_code}: {body}")
                    if exc.response is not None and exc.response.status_code < 500:
                        break
                except httpx.TimeoutException as exc:
                    errors.append(f"{model} attempt {attempt + 1}: Gemini image request timed out after {self.settings.gemini_timeout_seconds}s: {type(exc).__name__}")
                except httpx.HTTPError as exc:
                    errors.append(f"{model} attempt {attempt + 1}: Gemini image HTTP transport error: {type(exc).__name__}: {exc}")
                if attempt < 2:
                    await asyncio.sleep(0.8 * (attempt + 1))
        raise ModelGatewayError("; ".join(errors) or "Gemini image request failed.")

    async def validate_connection(self) -> ImageGatewayStatus:
        if missing_secret(self.settings.gemini_api_key):
            return ImageGatewayStatus(
                name=self.name,
                status="blocked_missing_credentials",
                reason="GEMINI_API_KEY is missing; real provider check was not attempted.",
                configured_model=self.settings.gemini_image_model,
            )
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(f"{GEMINI_BASE_URL}/models", headers=self._headers())
                response.raise_for_status()
            return ImageGatewayStatus(name=self.name, status="ready", reason="Gemini models endpoint responded.", configured_model=self.settings.gemini_image_model)
        except Exception as exc:
            return ImageGatewayStatus(name=self.name, status="blocked_provider_error", reason=f"Gemini image provider check failed: {exc}", configured_model=self.settings.gemini_image_model)
