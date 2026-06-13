from __future__ import annotations

import httpx

from app.core.config import get_settings, missing_secret
from app.image_gateway.base import ImageGatewayStatus, ImageRequest, ImageResult
from app.model_gateway.errors import ProviderBlocked


class Image2Client:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        if missing_secret(self.settings.image2_api_key) or missing_secret(self.settings.image2_base_url):
            raise ProviderBlocked("blocked_missing_credentials", "IMAGE2_API_KEY or IMAGE2_BASE_URL is not configured.")
        return {"Authorization": f"Bearer {self.settings.image2_api_key}", "Content-Type": "application/json"}

    async def generate(self, request: ImageRequest) -> ImageResult:
        payload = {"model": self.settings.image2_model, "prompt": request.prompt, "size": "1024x1024"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.settings.image2_base_url.rstrip('/')}/images/generations", headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        image_url = None
        if data.get("data"):
            image_url = data["data"][0].get("url") or data["data"][0].get("b64_json")
        return ImageResult(
            provider="image2",
            prompt=request.prompt,
            image_url=image_url,
            provider_response_id=data.get("id"),
            overlay_labels=request.overlay_labels,
            metadata={"teaching_goal": request.teaching_goal},
        )

    async def validate_connection(self) -> ImageGatewayStatus:
        if missing_secret(self.settings.image2_api_key) or missing_secret(self.settings.image2_base_url):
            return ImageGatewayStatus(
                name="image2",
                status="blocked_missing_credentials",
                reason="IMAGE2_API_KEY or IMAGE2_BASE_URL is missing; real provider check was not attempted.",
                configured_model=self.settings.image2_model,
            )
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(f"{self.settings.image2_base_url.rstrip('/')}/models", headers=self._headers())
                response.raise_for_status()
            return ImageGatewayStatus(name="image2", status="ready", reason="image2 endpoint responded.", configured_model=self.settings.image2_model)
        except Exception as exc:
            return ImageGatewayStatus(name="image2", status="blocked_provider_error", reason=f"image2 provider check failed: {exc}", configured_model=self.settings.image2_model)
