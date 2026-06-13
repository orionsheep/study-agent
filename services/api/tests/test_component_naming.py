import pytest

from app.canvas.component_namer import ComponentTitleNamer, fallback_component_title, is_generic_component_title
from app.schemas.app_protocol import CanvasApp, CanvasPosition, CanvasSize


def _quiz_app(title: str, prompt: str) -> CanvasApp:
    return CanvasApp(
        app_type="quiz.practice",
        title=title,
        position=CanvasPosition(x=0, y=0),
        size=CanvasSize(width=320, height=240),
        payload={"topic": "梯度下降", "questions": [{"prompt": prompt, "answer": "A"}]},
    )


class _JsonTitleClient:
    async def complete(self, messages, stream: bool = False):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"titles":['
                                    '{"index":0,"title":"学习率发散诊断题"},'
                                    '{"index":1,"title":"损失曲线判读题"}'
                                    "]}"
                                )
                            }
                        ]
                    }
                }
            ]
        }

    def extract_assistant_text(self, response):
        return response["candidates"][0]["content"]["parts"][0]["text"]


class _FailingTitleClient:
    async def complete(self, messages, stream: bool = False):
        raise TimeoutError("offline")

    def extract_assistant_text(self, response):
        return ""


class _Router:
    def __init__(self, client):
        self._client = client

    def client(self, provider=None):
        return self._client


@pytest.mark.asyncio
async def test_component_title_namer_uses_llm_titles(monkeypatch):
    monkeypatch.setattr("app.canvas.component_namer.ModelGatewayRouter", lambda: _Router(_JsonTitleClient()))
    apps = [
        _quiz_app("测试题", "为什么学习率过大会导致损失函数发散？"),
        _quiz_app("测试题", "观察损失曲线，判断模型是否收敛。"),
    ]

    trace = await ComponentTitleNamer().rename_apps(apps, source_material="梯度下降与学习率")

    assert [app.title for app in apps] == ["学习率发散诊断题", "损失曲线判读题"]
    assert any(item.startswith("llm_component_titles") for item in trace)


@pytest.mark.asyncio
async def test_component_title_namer_falls_back_to_content_titles(monkeypatch):
    monkeypatch.setattr("app.canvas.component_namer.ModelGatewayRouter", lambda: _Router(_FailingTitleClient()))
    apps = [
        _quiz_app("测试题", "请解释梯度下降中学习率过大为什么会震荡。"),
        _quiz_app("测试题", "请判断损失曲线平台期代表什么训练问题。"),
    ]

    trace = await ComponentTitleNamer().rename_apps(apps, source_material="梯度下降与学习率")

    assert len({app.title for app in apps}) == 2
    assert all(not is_generic_component_title(app.title) for app in apps)
    assert all(app.title != "测试题" for app in apps)
    assert any(item.startswith("component_title_fallback") for item in trace)


def test_sync_fallback_title_rejects_generic_names():
    title = fallback_component_title(
        "测试题",
        component_type="quiz.practice",
        topic="反向传播链式法则",
        payload={"questions": [{"prompt": "为什么链式法则可以计算每层梯度？"}]},
    )

    assert title == "反向传播链式法则诊断题"
