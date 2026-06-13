from __future__ import annotations

from app.image_gateway.gemini_image_client import GeminiImageClient
from app.image_gateway.prompt_planner import ImagePromptPlanner


class ImageGatewayRouter:
    def __init__(self) -> None:
        self.client = GeminiImageClient()
        self.planner = ImagePromptPlanner()

    async def status(self):
        return await self.client.validate_connection()
