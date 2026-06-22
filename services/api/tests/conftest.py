from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="learnforge-api-tests-"))
os.environ["DATABASE_URL"] = os.environ.get(
    "LEARNFORGE_TEST_DATABASE_URL",
    "postgresql://learnforge:learnforge@127.0.0.1:5432/learnforge",
)

from app.hermes_runtime.task_executor import HermesTaskResult




class FakeHermesTaskExecutor:
    @staticmethod
    def _has_uploaded_images(context) -> bool:
        # Mirror HermesTaskExecutor._has_uploaded_images so orchestrator code paths that
        # call HermesTaskExecutor._has_uploaded_images(context) work under the mock.
        return bool(getattr(context, "image_data", None) or [])

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

    def is_cancelled(self, run_id):
        return False

    def clear_run(self, run_id):
        return None

    async def run_answer_only(self, context, rag_context, *, rejected_capability="", run_id=None):
        return HermesTaskResult(
            capability="answer_only",
            summary="纯文本回答",
            text_response="这是测试用的纯文本回答。",
            trace=["fake_answer_only"],
        )

    async def run_detailed_analysis(self, plan, context, rag_context, run_id=None):
        """Fake detailed_analysis — returns sample HTML."""
        return "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'></head><body><h1>测试分析报告</h1><p>Fake Hermes 详细分析结果。</p></body></html>"

    async def run_hermes(self, plan, context, rag_context, on_stderr_line=None, on_trace_step=None, on_hermes_event=None, run_id=None):
        """Fake unified hermes — delegates to run_resource_bundle for JSON, or returns HTML.
        Accepts the same kwargs as the real HermesTaskExecutor.run_hermes (on_stderr_line,
        on_trace_step, run_id) so the orchestrator's call site works under the mock.
        """
        message = (context.message or "").lower()
        if plan.payload.get("capability") == "interactive_demo" or any(marker in message for marker in ["演示", "交互", "模型", "动画"]):
            return HermesTaskResult(
                capability="interactive_demo",
                topic="动能定理" if "动能定理" in context.message else context.message,
                summary="测试交互模型已生成。",
                text_response="测试交互模型已生成。",
                trace=["fake_hermes_runtime", "fake_interactive_demo"],
                apps=[
                    {
                        "app_type": "custom.html",
                        "title": "测试交互模型",
                        "payload": {
                            "html": "<section><h2>动能定理交互模型</h2><canvas width='320' height='180'></canvas><button data-action='reset'>重置</button><script>const btn=document.querySelector('[data-action=reset]');btn?.addEventListener('click',()=>{});requestAnimationFrame(()=>{});</script></section>"
                        },
                    }
                ],
            )
        if any(marker in message for marker in ["b站", "bilibili", "视频"]):
            return HermesTaskResult(
                capability="video_search",
                topic="数据结构与算法" if "数据结构" in context.message else context.message,
                summary="Hermes 选择实时视频搜索。",
                trace=["fake_hermes_runtime", "fake_video_search"],
            )
        if any(marker in message for marker in ["ppt", "幻灯片", "课件", "演示文稿"]):
            deck_html = """
<!DOCTYPE html><html><head><style>
.deck{display:flex;overflow-x:auto;scroll-snap-type:x mandatory}.slide{min-width:100%;scroll-snap-align:start}
</style></head><body>
<main class="deck" data-deck="ppt">
<section class="slide"><h1>测试 PPT</h1></section>
<section class="slide"><h2>核心概念</h2></section>
<section class="slide"><h2>示例</h2></section>
<section class="slide"><h2>总结</h2></section>
</main><script>addEventListener('keydown',e=>{if(e.key==='ArrowRight')document.querySelector('.deck').scrollBy({left:innerWidth,behavior:'smooth'});if(e.key==='ArrowLeft')document.querySelector('.deck').scrollBy({left:-innerWidth,behavior:'smooth'});});</script>
</body></html>
"""
            return HermesTaskResult(
                capability="ppt",
                topic="大学物理简单介绍" if "物理" in context.message else context.message,
                summary="测试 PPT 已生成。",
                text_response="测试 PPT 已生成。",
                trace=["fake_hermes_runtime", "fake_ppt"],
                resources=[
                    {
                        "type": "ppt",
                        "title": "测试 PPT",
                        "target_topic": "测试 PPT",
                        "content": {"format": "html_slide_deck"},
                        "source_refs": rag_context.get("source_refs", []),
                        "personalized_reason": "测试",
                    }
                ],
                apps=[
                    {
                        "app_type": "custom.html",
                        "title": "测试 PPT",
                        "payload": {"html": deck_html},
                    }
                ],
            )
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
def use_fake_hermes_executor(monkeypatch):
    class FakeModelClient:
        async def complete(self, messages, stream=False):
            combined = "\n".join(str(getattr(message, "content", message)) for message in messages)
            if "组件命名助手" not in combined:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "Gemini 测试回复 [[generate:custom.html]]临时标记[[/generate]]"
                            }
                        }
                    ]
                }
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"titles":[]}'
                        }
                    }
                ]
            }

        def extract_assistant_text(self, response):
            try:
                return response["choices"][0]["message"]["content"]
            except Exception:
                return ""

        def model_name(self):
            return "gemini-test-model"

    class FakeModelGatewayRouter:
        def normalize_provider(self, provider=None):
            return "gemini"
        def client(self, provider=None):
            return FakeModelClient()

    monkeypatch.setattr("app.agents.orchestrator_agent.ModelGatewayRouter", FakeModelGatewayRouter)
    monkeypatch.setattr("app.canvas.component_namer.ModelGatewayRouter", FakeModelGatewayRouter)
    monkeypatch.setattr("app.agents.orchestrator_agent.HermesTaskExecutor", FakeHermesTaskExecutor)
