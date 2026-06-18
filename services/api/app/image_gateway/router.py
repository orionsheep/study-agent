from __future__ import annotations

from app.image_gateway.gemini_image_client import GeminiImageClient
from app.image_gateway.image2_client import Image2Client
from app.image_gateway.prompt_planner import ImagePromptPlanner


class ImageGatewayRouter:
    def __init__(self) -> None:
        self.client = GeminiImageClient()
        self.image2_client = Image2Client()
        self.planner = ImagePromptPlanner()

    async def status(self):
        return await self.client.validate_connection()

    async def statuses(self) -> dict[str, "ImageGatewayStatus"]:
        """Return per-provider statuses so callers can distinguish image2 from gemini_image."""
        gemini = await self.client.validate_connection()
        image2 = await self.image2_client.validate_connection()
        return {"gemini_image": gemini, "image2": image2}


# Imported here (rather than top-of-file) to avoid a circular import at module load.
from app.image_gateway.base import ImageGatewayStatus  # noqa: E402
