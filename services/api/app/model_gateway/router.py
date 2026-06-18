from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.model_gateway.gemini_client import GeminiClient


class ModelGatewayRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.providers = {
            "gemini": GeminiClient(),
        }
        self.primary_name = self.normalize_provider(self.settings.model_provider)
        self.primary = self.providers[self.primary_name]

    def normalize_provider(self, provider: str | None = None) -> str:
        raw = provider if provider is not None else self.settings.model_provider
        cleaned = (raw or "gemini").strip().lower()
        aliases = {
            "google": "gemini",
            "gemini-3.1": "gemini",
            "gemini-3.1-pro": "gemini",
        }
        resolved = aliases.get(cleaned, cleaned)
        if resolved in self.providers:
            return resolved
        return "gemini"

    def fallback_order(self, provider: str | None = None) -> list[str]:
        primary = self.normalize_provider(provider)
        return [primary, *[name for name in self.providers if name != primary]]

    async def status(self, provider: str | None = None):
        return await self.client(provider).validate_connection()

    async def statuses(self):
        results = await asyncio.gather(*(client.validate_connection() for client in self.providers.values()))
        return dict(zip(self.providers.keys(), results, strict=True))

    def client(self, provider: str | None = None):
        return self.providers[self.normalize_provider(provider)]
