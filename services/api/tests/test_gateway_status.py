import pytest
import httpx

from app.model_gateway.base import ChatMessage
from app.model_gateway.errors import ModelGatewayError
from app.model_gateway.gemini_client import GeminiClient
from app.model_gateway.router import ModelGatewayRouter
from app.image_gateway.gemini_image_client import GeminiImageClient
from app.image_gateway.prompt_planner import ImagePromptPlanner
from app.image_gateway.router import ImageGatewayRouter


def test_model_router_preserves_provider_selection_and_fallback_order():
    router = ModelGatewayRouter()
    assert router.normalize_provider("gemini") == "gemini"
    assert router.normalize_provider("google") == "gemini"
    assert router.normalize_provider("unknown") == "gemini"
    assert router.fallback_order("gemini") == ["gemini"]


def test_gemini_extracts_assistant_text_from_candidates():
    response = {"candidates": [{"content": {"parts": [{"text": "第一段"}, {"text": "第二段"}]}}], "model": "gemini-test"}
    assert GeminiClient().extract_assistant_text(response) == "第一段第二段"


@pytest.mark.asyncio
async def test_gemini_connect_timeout_skips_same_provider_fallback(monkeypatch):
    client = GeminiClient()
    attempts: list[str] = []

    async def fail_connect(model, messages):
        attempts.append(model)
        raise httpx.ConnectTimeout("connect timed out")

    monkeypatch.setattr(client, "_complete_with_model", fail_connect)

    with pytest.raises(ModelGatewayError) as exc:
        await client.complete([ChatMessage(role="user", content="hello")])

    assert attempts == [client.settings.gemini_text_model]
    assert "connection timed out" in str(exc.value)


def test_gemini_image_extracts_inline_data():
    response = {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": "abc123"}}]}}]}
    image_data, mime_type = GeminiImageClient().extract_image(response)
    assert image_data == "abc123"
    assert mime_type == "image/png"


@pytest.mark.asyncio
async def test_gemini_image_missing_credentials_reports_blocked():
    status = await ImageGatewayRouter().status()
    assert status.status.startswith("blocked") or status.status == "ready"


def test_image_prompt_planner_outputs_overlay_labels():
    request = ImagePromptPlanner().plan("梯度下降", "解释学习率")
    assert request.overlay_labels
    assert "Simplified Chinese" in request.prompt
    assert "Do not include English words" in request.prompt
    assert "frontend overlay" not in request.prompt
    assert "Avoid embedded Chinese text" not in request.prompt
