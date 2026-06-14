from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="learnforge-api-tests-"))
os.environ["DATABASE_URL"] = os.environ.get("LEARNFORGE_TEST_DATABASE_URL", f"sqlite:///{TEST_DATA_DIR / 'learnforge_test.sqlite'}")

from app.hermes_runtime.task_executor import HermesTaskResult


class FakeMiMoClient:
    name = "mimo"
    adapter = "fake_mimo"

    class Settings:
        mimo_text_model = "mimo-test-model"

    settings = Settings()

    def __init__(self) -> None:
        self.calls: list[list[object]] = []

    async def complete(self, messages, stream: bool = False):
        self.calls.append(messages)
        return {
            "id": "test-mimo-response",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "这是 MiMo 测试回复：我会基于你的问题、RAG 引用和左侧 App 给出下一步学习建议。",
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }

    def extract_assistant_text(self, response):
        return response["choices"][0]["message"]["content"]

    def model_name(self):
        return self.settings.mimo_text_model


@pytest.fixture
def fake_mimo_client():
    return FakeMiMoClient()


class FakeHermesTaskExecutor:
    async def run_resource_bundle(self, plan, context, rag_context):
        refs = rag_context.get("source_refs", [{"source_id": "test-source", "title": "测试资料", "locator": "p1"}])
        return HermesTaskResult(
            summary="Hermes 测试资源包已生成。",
            trace=["fake_hermes_runtime", "fake_resource_bundle"],
            resources=[
                {"type": "document", "title": "测试讲义", "target_topic": "测试主题", "content": {"summary": "讲义"}, "source_refs": refs, "personalized_reason": "测试"},
                {"type": "mindmap", "title": "测试导图", "target_topic": "测试主题", "content": {"nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [["a", "b"]]}, "source_refs": refs, "personalized_reason": "测试"},
                {"type": "quiz", "title": "测试题", "target_topic": "测试主题", "content": {"questions": [{"prompt": "选什么？", "options": ["A", "B"], "answer": "A", "explanation": "因为 A"}]}, "source_refs": refs, "personalized_reason": "测试"},
                {"type": "code_practice", "title": "测试代码", "target_topic": "测试主题", "content": {"starter_code": "print('hello')", "expected_output": "hello"}, "source_refs": refs, "personalized_reason": "测试"},
                {"type": "ppt", "title": "测试 PPT", "target_topic": "测试主题", "content": {"slides": [{"title": "第一页"}]}, "source_refs": refs, "personalized_reason": "测试"},
            ],
            apps=[
                {"app_type": "custom.html", "title": "测试信息图", "resource_index": 0, "payload": {"html": "<section><h2>测试信息图</h2><p>安全 HTML。</p></section>"}},
                {"app_type": "mindmap.concept", "title": "测试导图", "resource_index": 1, "payload": {"nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [["a", "b"]]}},
                {"app_type": "quiz.practice", "title": "测试题", "resource_index": 2, "payload": {"questions": [{"prompt": "选什么？", "options": ["A", "B"], "answer": "A", "explanation": "因为 A"}]}},
                {"app_type": "code.lab", "title": "测试代码", "resource_index": 3, "payload": {"starter_code": "print('hello')", "expected_output": "hello"}},
                {"app_type": "ppt.preview", "title": "测试 PPT", "resource_index": 4, "payload": {"slides": [{"title": "第一页"}]}},
            ],
        )

    async def run_detailed_analysis(self, plan, context, rag_context):
        """Fake detailed_analysis — returns sample HTML."""
        return "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'></head><body><h1>测试分析报告</h1><p>Fake Hermes 详细分析结果。</p></body></html>"

    async def run_hermes(self, plan, context, rag_context):
        """Fake unified hermes — delegates to run_resource_bundle for JSON, or returns HTML."""
        message = (context.message or "").lower()
        # If it looks like a detailed analysis request, return HTML
        if any(marker in message for marker in ["分析这道题", "讲解这道题", "帮我讲解", "批改作业"]):
            return HermesTaskResult(
                capability="detailed_analysis",
                mode="background",
                summary="详细分析完成",
                raw_html="<!DOCTYPE html><html><head></head><body><h1>分析报告</h1></body></html>",
                raw_text="---HERMES_HTML_OUTPUT---\n<!DOCTYPE html>...",
                trace=["detailed_analysis_html_generated"],
            )
        # Otherwise return resource bundle result
        return await self.run_resource_bundle(plan, context, rag_context)


@pytest.fixture(autouse=True)
def use_fake_mimo_for_orchestrator(monkeypatch, fake_mimo_client):
    class FakeModelGatewayRouter:
        def normalize_provider(self, provider=None):
            return provider if provider in {"mimo", "gemini"} else "mimo"

        def client(self, provider=None):
            return fake_mimo_client

    monkeypatch.setattr("app.agents.orchestrator_agent.ModelGatewayRouter", FakeModelGatewayRouter)
    monkeypatch.setattr("app.canvas.component_namer.ModelGatewayRouter", FakeModelGatewayRouter)
    monkeypatch.setattr("app.agents.orchestrator_agent.HermesTaskExecutor", FakeHermesTaskExecutor)
