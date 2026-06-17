import pytest
from types import SimpleNamespace

from app.agents.base import AgentPlan, TutorTurnContext
from app.agents.orchestrator_agent import OrchestratorAgent, UnifiedOrchestrator
from app.canvas.materializer import CanvasMaterializer, detailed_analysis_context_mismatch, normalize_html_artifact_text, wrap_detailed_analysis_report
from app.agents.planner_agent import PlannerAgent, PlannerAgentInput
from app.agents.profile_agent import ProfileAgent, ProfileAgentInput
from app.agents.resource_bundle_agent import ResourceBundleAgent, ResourceBundleAgentInput
from app.hermes_runtime.task_executor import HermesTaskExecutor, HermesTaskResult
from app.image_gateway.base import ImageResult
from app.image_gateway.prompt_planner import ImagePromptPlanner
from app.model_gateway.errors import ModelGatewayError
from app.schemas.app_protocol import CanvasApp, CanvasPosition, CanvasSize, EduMemoryItem, LearningResource
from app.skills.base import SkillInput
from app.skills.registry import SkillRegistry


def test_registry_contains_all_required_skills():
    names = set(SkillRegistry().names())
    assert len(names) == 16
    assert "document_skill" in names
    assert "course_ingestion_skill" in names


def test_resource_bundle_creates_at_least_five_resources():
    output = ResourceBundleAgent().run(ResourceBundleAgentInput(student_id="demo-student", topic="梯度下降"))
    assert len(output.payload["resources"]) >= 5
    assert all(resource["source_refs"] for resource in output.payload["resources"])


def test_hermes_custom_html_prompt_requires_comprehensive_chinese_learning_structure():
    plan = AgentPlan(
        task_type="hermes_custom_infographic",
        steps=["hermes_runtime"],
        payload={
            "capability": "custom_infographic",
            "topic": "排序算法",
            "expected_app_types": ["custom.html"],
            "expected_resource_types": [],
            "requires_canvas": True,
        },
    )
    prompt = HermesTaskExecutor().build_resource_bundle_prompt(
        plan,
        TutorTurnContext(message="请生成排序算法 HTML 信息图"),
        {"context": "", "source_refs": []},
    )

    assert "标题与目标、核心直觉、可视化主体、步骤/公式、例题、常见误区、自测题、下一步建议" in prompt
    assert "real visible Chinese content" in prompt
    assert "LABEL placeholders" in prompt


def test_answer_only_prompt_compacts_recent_messages_without_metadata_noise():
    executor = HermesTaskExecutor()
    context = TutorTurnContext(
        message="你还记得我们刚才聊了什么吗？",
        last_assistant_answer="我们刚才聊了二次函数，重点是 y=ax²+bx+c 和抛物线图像。",
        recent_messages=[
            {
                "id": "msg-user",
                "role": "user",
                "text": "先给我讲一下二次函数。",
                "metadata": {"plan": {"task_type": "unified_hermes"}},
                "links": [{"link_id": "link-1"}],
            },
            {
                "id": "msg-assistant",
                "role": "assistant",
                "text": "我们刚才聊了二次函数，重点是 y=ax²+bx+c 和抛物线图像。",
                "metadata": {"capability": "answer_only"},
            },
        ],
    )

    prompt = executor.build_answer_only_prompt(context, {"context": ""})

    assert "二次函数" in prompt
    assert '"metadata"' not in prompt
    assert '"links"' not in prompt


def test_implicit_question_defaults_to_answer_only_with_no_canvas():
    agent = UnifiedOrchestrator()

    for message in ["解释一下这道题", "帮我看看图片里的 2.1.7"]:
        plan = agent.plan_turn(
            TutorTurnContext(
                message=message,
                image_data=["data:image/png;base64,AAAA"] if "图片" in message else None,
            )
        )

        assert plan.task_type == "unified_hermes"
        assert plan.payload["capability"] == "answer_only"
        assert plan.payload["requires_canvas"] is False
        assert plan.payload["expected_app_types"] == []


def test_requested_skill_button_locks_interactive_generation():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(TutorTurnContext(message="2.1.7", requested_skill="demo"))

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["requested_skill"] == "demo"
    assert plan.payload["expected_artifact_kind"] == "interactive_model"


def test_explicit_interactive_request_still_generates_directly():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(TutorTurnContext(message="生成一下 2.1.7 的可交互模型"))

    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["requires_canvas"] is True
    assert plan.payload["route_source"] == "capability_contract_lock"


def test_custom_html_quality_gate_rejects_placeholders_and_math_noise():
    agent = UnifiedOrchestrator()

    assert agent.custom_html_render_quality_issue("<main>HTML ARTIFACT</main>", "detailed_analysis") == "placeholder_free:false"
    assert (
        agent.custom_html_render_quality_issue(
            "<section><h1>动量守恒详细分析报告</h1><p>这里展示公式 $\\\\frac{1}{2}mv^2$ 和 E\\_k 的推导过程，正文足够长。</p></section>",
            "detailed_analysis",
        )
        == "math_render_ready:false"
    )


def test_artifact_success_markdown_is_user_facing_not_runtime_log():
    agent = UnifiedOrchestrator()
    plan = AgentPlan(
        task_type="unified_hermes",
        steps=[],
        payload={"capability": "interactive_demo", "topic": "动量守恒", "expected_app_types": ["custom.html"]},
    )
    text = agent.artifact_success_markdown(
        plan,
        HermesTaskResult(capability="interactive_demo", topic="动量守恒", summary="done"),
        None,
        {"artifact_verifier": {"passed": True, "created_app_count": 1, "created_resource_count": 0}},
    )

    assert "可交互模型已生成" in text
    assert "Hermes 已确认" not in text
    assert "产物类型：custom.html" not in text
    assert "artifact_kind" not in text


@pytest.mark.asyncio
async def test_answer_only_sdk_persists_raw_user_message_not_scaffold_prompt(monkeypatch):
    executor = HermesTaskExecutor()
    captured: dict[str, str] = {}

    async def fake_invoke(prompt, provider, model, **kwargs):
        captured["persist_user_message"] = kwargs.get("persist_user_message") or ""
        captured["prompt"] = str(prompt)
        return 0, "这是一次正常回答。", ""

    monkeypatch.setattr(executor, "use_sdk_backend", lambda: True)
    monkeypatch.setattr(executor, "provider_attempts", lambda: [("gemini", "gemini-test-model")])
    monkeypatch.setattr(executor, "_invoke_hermes_sdk", fake_invoke)

    context = TutorTurnContext(
        message="你还记得我刚才说什么吗？",
        conversation_id="answer-only-persist-test",
        recent_messages=[{"role": "user", "text": "先给我讲一下二次函数。"}],
    )
    result = await executor.run_answer_only(context, {"context": ""}, run_id="run-persist-answer-only")

    assert result.text_response == "这是一次正常回答。"
    assert context.message in captured["persist_user_message"]
    assert captured["persist_user_message"] != captured["prompt"]


@pytest.mark.asyncio
async def test_unified_hermes_sdk_persists_raw_user_message_not_scaffold_prompt(monkeypatch):
    executor = HermesTaskExecutor()
    captured: dict[str, str] = {}

    async def fake_invoke(prompt, provider, model, **kwargs):
        captured["persist_user_message"] = kwargs.get("persist_user_message") or ""
        captured["prompt"] = str(prompt)
        return 0, '{"capability":"answer_only","summary":"ok","text_response":"好的，我们继续。","apps":[],"resources":[],"trace":["sdk"]}', ""

    monkeypatch.setattr(executor, "use_sdk_backend", lambda: True)
    monkeypatch.setattr(executor, "provider_attempts", lambda: [("gemini", "gemini-test-model")])
    monkeypatch.setattr(executor, "_invoke_hermes_sdk", fake_invoke)

    plan = AgentPlan(
        task_type="unified_hermes",
        steps=["intent_detect", "hermes_runtime", "canvas_materializer", "artifact_verifier"],
        payload={"capability": "hermes_decides", "topic": "二次函数", "source_material": "请继续讲二次函数"},
    )
    context = TutorTurnContext(
        message="请继续讲二次函数。",
        conversation_id="unified-persist-test",
        recent_messages=[{"role": "assistant", "text": "二次函数的图像是一条抛物线。"}],
        last_assistant_answer="二次函数的图像是一条抛物线。",
    )
    result = await executor.run_hermes(plan, context, {"context": "", "source_refs": []}, run_id="run-persist-unified")

    assert result.capability == "answer_only"
    assert context.message in captured["persist_user_message"]
    assert captured["persist_user_message"] != captured["prompt"]


def test_detailed_analysis_report_wrapper_adds_stable_learnforge_shell():
    raw = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <title>英语阅读理解综合解析报告</title>
  <style>.card{color:red}</style>
</head>
<body>
  <section class="card">
    <h2>Reading Comprehension - Section A</h2>
    <p>Directions: choose one word for each blank.</p>
  </section>
</body>
</html>"""

    html = wrap_detailed_analysis_report(raw, title="Fallback Title")

    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert 'data-learnforge-report="detailed-analysis"' in html
    assert "LearnForge Reading Studio" in html
    assert "Reading Comprehension - Section A" in html
    assert "Directions: choose one word" in html
    assert html.count("\\n") == 0


def test_detailed_analysis_context_guard_blocks_english_image_math_contamination():
    source_material = """
PYTHON_VISION_FALLBACK_OCR:
Reading Comprehension
Section A
Directions: In this section, there is a passage with ten blanks.
where in this process children succeed in controlling their reputation and where they __34__...
第34空、 第35空需要根据词库选择。
"""
    wrong_html = """<!DOCTYPE html>
<html><body><h1>深度解析讲义</h1><p>【题目原题】已知双曲线 C: x^2/a^2-y^2/b^2=1，求离心率。</p></body></html>"""

    assert detailed_analysis_context_mismatch(wrong_html, source_material) == "topic_contamination:双曲线"

    payload = CanvasMaterializer(store=None).validate_custom_html(
        {"html": wrong_html, "title": "IMG_5920图片题目详细解析"},
        "IMG_5920图片题目详细解析",
        source_material=source_material,
        capability="detailed_analysis",
    )
    html = str(payload["html"])

    assert payload["guarded"] is True
    assert payload["fallback_used"] is True
    assert "报告已拦截" in html
    assert "双曲线 C" not in html


def test_detailed_analysis_prompt_binds_image_artifact_and_suppresses_rag():
    executor = HermesTaskExecutor()
    plan = AgentPlan(
        task_type="detailed_analysis",
        steps=["hermes_runtime"],
        payload={"capability": "detailed_analysis", "topic": "IMG_5920图片题目详细解析"},
    )
    prompt = executor.build_detailed_analysis_prompt(
        plan,
        TutorTurnContext(message="请把这张英语图片整篇逐句讲解"),
        {
            "context": "质点运动学、牛顿第二定律、刚体转动惯量。",
            "source_refs": [{"document_id": "physics", "chunk_id": "bad", "course_id": "ai-course"}],
            "current_image_artifacts": [
                {
                    "artifact_id": "artifact_img_001",
                    "object_key": "source.image/artifact_img_001/upload-1.jpg",
                    "content_type": "image/jpeg",
                    "metadata": {"public_url": "https://cdn.example.test/image.jpg"},
                }
            ],
        },
        image_analysis="Reading Comprehension\nSection A\nDirections: choose one word for each blank.\n第34空 第35空",
    )

    assert "artifact_id=artifact_img_001" in prompt
    assert "Reading Comprehension" in prompt
    assert "唯一主上下文" in prompt
    assert "质点运动学" not in prompt
    assert "牛顿第二定律" not in prompt


@pytest.mark.asyncio
async def test_run_detailed_analysis_injects_image_artifact_into_sdk(monkeypatch):
    executor = HermesTaskExecutor()
    artifact = {
        "artifact_id": "artifact_img_002",
        "object_key": "source.image/artifact_img_002/upload-1.jpg",
        "content_type": "image/jpeg",
        "metadata": {"public_url": "https://cdn.example.test/upload-1.jpg"},
    }
    captured: dict[str, object] = {}

    monkeypatch.setattr(executor, "use_sdk_backend", lambda: True)
    monkeypatch.setattr(executor, "_persist_uploaded_image_artifacts", lambda context, run_id: [artifact])

    async def fake_invoke(prompt, provider, model, on_stderr_line=None, run_id=None, persist_user_message=None, student_id=None, **kwargs):
        captured["prompt"] = prompt
        captured["persist_user_message"] = persist_user_message
        return 0, "<!DOCTYPE html><html><body><h1>Reading Comprehension</h1></body></html>", ""

    monkeypatch.setattr(executor, "_invoke_hermes_sdk", fake_invoke)
    plan = AgentPlan(
        task_type="detailed_analysis",
        steps=["hermes_runtime"],
        payload={"capability": "detailed_analysis", "topic": "英语图片详细解析"},
    )

    html = await executor.run_detailed_analysis(
        plan,
        TutorTurnContext(message="请详细讲解这张英语题图片", image_data=["data:image/jpeg;base64,not-real"]),
        {"context": "双曲线旧资料", "source_refs": []},
        run_id="run_test_detailed_image",
    )

    sdk_prompt = captured["prompt"]
    assert "Reading Comprehension" in html
    assert isinstance(sdk_prompt, list)
    assert any(part.get("type") == "image_url" and part.get("image_url", {}).get("url") == artifact["metadata"]["public_url"] for part in sdk_prompt)
    assert "artifact_img_002" in str(captured["persist_user_message"])
    assert "双曲线旧资料" not in str(captured["persist_user_message"])


@pytest.mark.asyncio
async def test_run_resource_bundle_uses_sdk_backend_and_never_cli(monkeypatch):
    executor = HermesTaskExecutor()
    captured: dict[str, object] = {}

    monkeypatch.setattr(executor, "use_sdk_backend", lambda: True)
    monkeypatch.setattr(executor, "provider_attempts", lambda: [("gemini", "fake-gemini")])
    monkeypatch.setattr(executor, "_persist_uploaded_image_artifacts", lambda context, run_id: [])

    async def fail_cli(*args, **kwargs):
        raise AssertionError("CLI fallback must not be called when SDK backend is active")

    async def fake_sdk(prompt, provider, model, run_id=None, persist_user_message=None, student_id=None, **kwargs):
        captured["prompt"] = prompt
        captured["provider"] = provider
        captured["model"] = model
        captured["persist_user_message"] = persist_user_message
        return (
            0,
            (
                '{"summary":"SDK PPT generated","trace":["sdk_embedded"],'
                '"resources":[{"type":"ppt","title":"英语阅读 PPT","content":{"slides":[{"title":"Reading"}]}}],'
                '"apps":[{"app_type":"custom.html","title":"英语阅读 PPT",'
                '"payload":{"layout":"guizang-web-ppt","html":"<!DOCTYPE html><html><body><section class=\\"slide\\" data-slide=\\"1\\">Reading Comprehension</section><section class=\\"slide\\" data-slide=\\"2\\">Section A</section><script>document.addEventListener(\\"keydown\\",()=>{})</script></body></html>"}}]}'
            ),
            "",
        )

    monkeypatch.setattr(executor, "_invoke_hermes", fail_cli)
    monkeypatch.setattr(executor, "_invoke_hermes_sdk", fake_sdk)
    plan = AgentPlan(
        task_type="hermes_ppt",
        steps=["hermes_runtime"],
        payload={
            "capability": "ppt",
            "topic": "英语阅读理解",
            "source_material": "Reading Comprehension\nSection A",
            "expected_app_types": ["custom.html"],
            "expected_resource_types": ["ppt"],
            "requires_canvas": True,
        },
    )

    result = await executor.run_resource_bundle(
        plan,
        TutorTurnContext(message="请把上面内容整理成 PPT"),
        {"context": "", "source_refs": []},
        run_id="run_sdk_resource_bundle",
    )

    assert result.summary == "SDK PPT generated"
    assert result.apps[0]["app_type"] == "custom.html"
    assert captured["provider"] == "gemini"
    assert captured["model"] == "fake-gemini"
    assert "Reading Comprehension" in str(captured["persist_user_message"])


def test_html_normalizer_decodes_double_escaped_document_and_trims_json_tail():
    raw = '\\\\n<!DOCTYPE html>\\\\n<html lang=\\\\"zh-CN\\\\"><body><section>魔方</section></body></html>\\\\n", {"id": "old_chat"}'

    html = normalize_html_artifact_text(raw)

    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert html.endswith("</html>")
    assert "\\n" not in html
    assert '\\"' not in html
    assert "old_chat" not in html
    assert "魔方" in html


def test_hermes_interactive_prompt_blocks_quadratic_context_bleed():
    plan = AgentPlan(
        task_type="hermes_interactive_demo",
        steps=["hermes_runtime"],
        payload={
            "capability": "interactive_demo",
            "topic": "二次函数",
            "expected_app_types": ["custom.html"],
            "expected_resource_types": [],
            "requires_canvas": True,
        },
    )
    prompt = HermesTaskExecutor().build_resource_bundle_prompt(
        plan,
        TutorTurnContext(message="生成二次函数动态演示模型"),
        {"context": "", "source_refs": []},
    )

    assert "never raw template syntax" in prompt
    assert "For a quadratic-function request" in prompt
    assert "DO NOT mention learning rate, gradient descent" in prompt
    assert "Advanced Demo Runtime requirements" in prompt
    assert "computeModel/updateSimulation" in prompt
    assert "continuous animated model" in prompt


def test_hermes_interactive_prompt_demands_complete_bernoulli_runtime():
    plan = AgentPlan(
        task_type="hermes_interactive_demo",
        steps=["hermes_runtime"],
        payload={
            "capability": "interactive_demo",
            "topic": "伯努利定律",
            "expected_app_types": ["custom.html"],
            "expected_resource_types": [],
            "requires_canvas": True,
        },
    )
    prompt = HermesTaskExecutor().build_resource_bundle_prompt(
        plan,
        TutorTurnContext(message="生成一个伯努利定律的3D可交互演示模型"),
        {"context": "", "source_refs": []},
    )

    assert "v2=v1/(A2/A1)" in prompt
    assert "pressure-color field" in prompt
    assert "streamlines/velocity vectors" in prompt
    assert "energy-term bars" in prompt


def test_profile_agent_extracts_many_dimensions():
    output = ProfileAgent().run(ProfileAgentInput(student_id="demo-student", message="我是软件工程大一，Python 一般，数学推导弱，喜欢图解和代码，想学神经网络。"))
    assert len(output.dimensions) >= 8


def test_planner_inserts_prerequisite_stage_for_weak_math():
    output = PlannerAgent().run(PlannerAgentInput(student_id="demo-student", topic="神经网络"))
    titles = [stage["title"] for stage in output.payload["path"]["stages"]]
    assert "补齐数学推导基础" in titles


def test_planner_tolerates_null_profile_fields():
    store = OrchestratorAgent().store
    student_id = "student-null-profile-fields"
    store.save_profile(
        student_id,
        {"weak_points": None, "preferred_resources": None, "learning_goal": "学习神经网络"},
        course_id="ai-course",
    )
    output = PlannerAgent().run(PlannerAgentInput(student_id=student_id, topic="神经网络"))
    assert output.payload["path"]["stages"]


def test_hermes_parser_reports_malformed_json_as_model_gateway_error():
    executor = HermesTaskExecutor()
    with pytest.raises(ModelGatewayError):
        executor.parse_json_result('{"summary":"broken","resources":[{"type":"document"}],"apps":[')


def test_notes_capability_requires_explicit_note_intent():
    agent = OrchestratorAgent()
    answer_plan = agent.plan_turn(TutorTurnContext(message="请总结一下排序算法的核心思想"))
    notes_plan = agent.plan_turn(
        TutorTurnContext(
            message="请把刚才内容整理成学习笔记",
            last_assistant_answer="我们正在学习排序算法，包括冒泡排序、快速排序和归并排序。",
        )
    )
    assert answer_plan.payload["capability"] == "answer_only"
    assert notes_plan.payload["capability"] == "notes"
    assert notes_plan.payload["topic"] == "排序算法"


def test_store_lists_seed_and_current_conversation_apps_only():
    agent = OrchestratorAgent()
    store = agent.store
    app_a = CanvasApp(
        app_id="app-conv-a-filter-test",
        app_type="custom.html",
        title="会话 A 信息图",
        position=CanvasPosition(x=10, y=10),
        size=CanvasSize(width=300, height=220),
        payload={"html": "<section>A</section>"},
        source={"conversation_id": "conv-a", "course_id": "ai-course"},
    )
    app_b = CanvasApp(
        app_id="app-conv-b-filter-test",
        app_type="custom.html",
        title="会话 B 信息图",
        position=CanvasPosition(x=20, y=20),
        size=CanvasSize(width=300, height=220),
        payload={"html": "<section>B</section>"},
        source={"conversation_id": "conv-b", "course_id": "ai-course"},
    )
    store.save_app(app_a, student_id="demo-student", course_id="ai-course")
    store.save_app(app_b, student_id="demo-student", course_id="ai-course")

    titles = [app.title for app in store.list_apps("demo-student", course_id="ai-course", conversation_id="conv-a")]
    assert "学习画像" in titles
    assert "会话 A 信息图" in titles
    assert "会话 B 信息图" not in titles


@pytest.mark.asyncio
async def test_orchestrator_routes_and_emits_trace_steps():
    class InteractiveHermesExecutor:
        @staticmethod
        def _has_uploaded_images(context) -> bool:
            return False

        def is_cancelled(self, run_id):
            return False

        def clear_run(self, run_id):
            return None

        async def run_hermes(self, plan, context, rag_context, **kwargs):
            return HermesTaskResult(
                capability="interactive_demo",
                topic="动能定理",
                summary="动能定理交互模型已生成。",
                    apps=[
                        {
                            "app_type": "custom.html",
                            "title": "动能定理交互模型",
                            "payload": {
                                "html": "<section><h2>动能定理交互模型</h2><canvas width='320' height='180'></canvas><button data-action='reset'>重置</button><script>document.querySelector('[data-action=reset]')?.addEventListener('click',()=>{});requestAnimationFrame(()=>{});</script></section>"
                            },
                        }
                    ],
                )

    agent = UnifiedOrchestrator()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = InteractiveHermesExecutor()
    context = TutorTurnContext(message="生成动能定理演示")
    plan = agent.plan_turn(context)
    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "capability_contract_lock"
    assert plan.payload["expected_artifact_kind"] == "interactive_model"

    events = [event async for event in agent.execute_plan(plan, context)]

    assert any(event["type"] == "run.step" and event["step_name"] == "hermes_runtime" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "canvas_materializer" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "artifact_verifier" and event["status"] == "completed" for event in events)
    assert any(event["type"] == "app.create" and event["app"]["app_type"] == "custom.html" for event in events)
    assert any(
        event["type"] == "app.create"
        and event["app"]["payload"].get("artifact_kind") == "interactive_model"
        for event in events
    )
    assert any(event["type"] == "app.link.create" for event in events)
    assistant_text = "".join(event.get("text", "") for event in events if event["type"] == "assistant.delta")
    assert "可交互模型已生成" in assistant_text
    assert "动能定理" in assistant_text


def test_interactive_quadratic_stays_custom_html_not_gradient_descent():
    agent = OrchestratorAgent()
    context = TutorTurnContext(message="生成二次函数动态演示模型，别再串到梯度下降")
    plan = agent.plan_turn(context)

    assert plan.task_type == "hermes_interactive_demo"
    assert plan.payload["topic"] == "二次函数"
    assert plan.payload["expected_app_types"] == ["custom.html"]


def test_hermes_parser_recovers_json_from_prose_and_fences():
    ex = HermesTaskExecutor()
    # JSON wrapped in a markdown fence with prose before/after, and braces inside a string value.
    fenced = (
        "好的，已生成：\n```json\n"
        '{"apps":[{"app_type":"custom.html","title":"演示","payload":{"html":"<b>{a}</b>"},"source_refs":[]}]}'
        "\n```\n希望有帮助！"
    )
    result = ex.parse_json_result(fenced)
    assert len(result.apps) == 1
    # Trailing prose after a bare JSON object must still parse.
    trailing = '{"resources":[{"type":"document","title":"t","content":{},"source_refs":[],"personalized_reason":"r"}]} 多余的话'
    assert len(ex.parse_json_result(trailing).resources) == 1
    # Pure prose with no JSON object must still be rejected (so the retry path can trigger).
    with pytest.raises(ModelGatewayError):
        ex.parse_json_result("对不起，我没有理解你的问题。")


def test_contextual_video_request_uses_conversation_topic():
    agent = OrchestratorAgent()
    # "推荐几个相关的视频" references the prior discussion; the video query must be the
    # conversation's current topic (分子扩散), not a generic fragment that returns junk.
    context = TutorTurnContext(
        message="推荐几个相关的视频",
        recent_messages=[
            {"role": "user", "text": "生成一个物理分子扩散的可交互模型"},
            {"role": "assistant", "text": "物理分子扩散是热力学核心现象……"},
        ],
        last_assistant_answer="物理分子扩散是热力学核心现象……",
    )
    plan = agent.plan_turn(context)
    assert plan.task_type == "video_recommendations"
    assert "分子扩散" in plan.payload["topic"]


def test_contextual_video_request_prefers_recent_learning_app_title_not_generic_roadmap():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请搜索与当前主题相关的B站教学视频",
        recent_messages=[
            {"role": "user", "text": "给我总结成一个信息图"},
            {"role": "assistant", "text": "专属信息图已生成：计算机软工专业四阶段学习路线图。"},
        ],
        recent_apps=[
            {
                "app_id": "app-custom-roadmap",
                "app_type": "custom.html",
                "title": "计算机软工专业四阶段学习路线图",
            }
        ],
        last_assistant_answer="专属信息图已生成：计算机软工专业四阶段学习路线图。",
    )
    plan = agent.plan_turn(context)
    assert plan.task_type == "video_recommendations"
    assert "计算机软工专业四阶段" in plan.payload["topic"]
    assert plan.payload["topic"] != "路线图"


def test_contextual_video_request_prefers_recent_physics_turn_over_stale_learning_focus():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请搜索与当前主题相关的B站教学视频",
        current_topic="大一软工个性化学习路线图",
        current_objective="规划「大一软工个性化学习路线图」的学习路径",
        recent_apps=[
            {
                "app_id": "app-custom-roadmap",
                "app_type": "custom.html",
                "title": "大一软工个性化学习路线图",
            }
        ],
        recent_messages=[
            {"role": "user", "text": "请基于内燃机的工作原理生成一张教学图片"},
            {"role": "assistant", "text": "四冲程内燃机和奥托循环的教学图解已经生成。"},
        ],
        last_assistant_answer="四冲程内燃机和奥托循环的教学图解已经生成。",
    )
    plan = agent.plan_turn(context)
    assert plan.task_type == "video_recommendations"
    assert "内燃机" in plan.payload["topic"]
    assert "软工" not in plan.payload["topic"]
    assert "python" not in plan.payload["topic"].lower()


def test_contextual_video_request_extracts_clean_internal_combustion_topic():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请搜索与当前主题相关的B站教学视频",
        recent_messages=[
            {"role": "user", "text": "我现在学物理里的内燃机，重点是四冲程内燃机和奥托循环，请先记住这个上下文。"},
        ],
    )

    plan = agent.plan_turn(context)

    assert plan.task_type == "video_recommendations"
    assert plan.payload["topic"] == "内燃机"


def test_video_request_prefers_current_mechanical_vibration_over_correction_history():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="找一下机械振动相关物理题目相关的视频",
        recent_messages=[
            {"role": "user", "text": "我说的是 生成可交互模型 不是PPT"},
            {"role": "assistant", "text": "好的，我会生成可交互模型，不生成 PPT。"},
        ],
        last_assistant_answer="好的，我会生成可交互模型，不生成 PPT。",
    )

    plan = agent.plan_turn(context)

    assert plan.task_type == "video_recommendations"
    assert "机械振动" in plan.payload["topic"]
    assert "不是PPT" not in plan.payload["topic"]
    assert "交互模型" not in plan.payload["topic"]


def test_unified_correction_not_ppt_locks_interactive_demo():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(TutorTurnContext(message="我说的是生成可交互模型不是PPT"))

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["expected_app_types"] == ["custom.html"]
    assert plan.payload["expected_resource_types"] == []
    assert plan.payload["expected_artifact_kind"] == "interactive_model"


def test_unified_ppt_request_locks_ppt_contract():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(
        TutorTurnContext(
            message="请把上面聊天总结成PPT",
            last_assistant_answer="我们刚刚讨论了人船模型与动量守恒。",
        )
    )

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "ppt"
    assert plan.payload["expected_app_types"] == ["custom.html"]
    assert plan.payload["expected_resource_types"] == ["ppt"]
    assert plan.payload["expected_artifact_kind"] == "ppt_deck"


def test_image_followup_inherits_recent_human_boat_topic_not_neural_network():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(
        TutorTurnContext(
            message="生成一张这个模型的图片",
            last_assistant_answer="我们上面讨论的是人船模型，核心是动量守恒和系统质心不变。",
        )
    )

    assert plan.payload["capability"] == "image_explanation"
    assert "人船模型" in plan.payload["topic"]
    assert "神经网络" not in plan.payload["topic"]


@pytest.mark.asyncio
async def test_unified_contextual_video_search_reuses_recent_topic_for_generic_followup():
    class GenericVideoHermesExecutor:
        def is_cancelled(self, run_id):
            return False

        def clear_run(self, run_id):
            return None

        async def run_hermes(self, plan, context, rag_context, **kwargs):
            return HermesTaskResult(
                capability="video_search",
                summary="开始搜索视频",
                topic="相关视频",
                text_response="开始搜索视频",
                trace=["video_search_generic_topic"],
            )

        async def run_answer_only(self, context, rag_context, *, rejected_capability="", run_id=None):
            return HermesTaskResult(capability="answer_only", summary="文本回答", text_response="纯文本回答")

    agent = UnifiedOrchestrator()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = GenericVideoHermesExecutor()
    captured: dict[str, str] = {}

    async def fake_retrieve(topic, context, limit=6):
        captured["topic"] = topic
        return {
            "videos": [
                LearningResource(
                    resource_id="res-video-bernoulli",
                    type="video",
                    title="伯努利定律动画讲解",
                    target_topic=topic,
                    difficulty="中级",
                    content={"url": "https://www.bilibili.com/video/BV1BERNOULLI", "bvid": "BV1BERNOULLI", "author": "测试UP"},
                    source_refs=[{"document_id": "doc-bili", "chunk_id": "chunk-bernoulli", "course_id": "ai-course"}],
                    personalized_reason="上下文视频搜索测试",
                    tags=["#伯努利定律"],
                )
            ],
            "source": "bilibili_live",
        }

    agent.retrieve_screened_videos = fake_retrieve
    context = TutorTurnContext(
        message="找一些相关的视频",
        conversation_id="video-contextual-unified-test",
        recent_messages=[
            {"role": "user", "text": "请解释一下伯努利定律的核心直觉。"},
            {"role": "assistant", "text": "伯努利定律关注流速、压强和能量守恒之间的关系。"},
        ],
        last_assistant_answer="伯努利定律关注流速、压强和能量守恒之间的关系。",
    )

    events = [event async for event in agent.execute_plan(agent.plan_turn(context), context)]

    assert "伯努利" in captured["topic"]
    assert any(event["type"] == "resource.create" and event["resource"]["type"] == "video" for event in events)
    assert any(event["type"] == "app.create" and event["app"]["app_type"] == "video.player" for event in events)


@pytest.mark.asyncio
async def test_unified_video_search_rejects_hermes_topic_drift_to_correction_text():
    class DriftVideoHermesExecutor:
        def is_cancelled(self, run_id):
            return False

        def clear_run(self, run_id):
            return None

        async def run_hermes(self, plan, context, rag_context, **kwargs):
            return HermesTaskResult(
                capability="video_search",
                summary="开始搜索视频",
                topic="是 生成可交互模型 不是PPT",
                text_response="开始搜索视频",
                trace=["video_search_drift_topic"],
            )

        async def run_answer_only(self, context, rag_context, *, rejected_capability="", run_id=None):
            return HermesTaskResult(capability="answer_only", summary="文本回答", text_response="纯文本回答")

    agent = UnifiedOrchestrator()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = DriftVideoHermesExecutor()
    captured: dict[str, str] = {}

    async def fake_retrieve(topic, context, limit=6):
        captured["topic"] = topic
        return {
            "videos": [
                LearningResource(
                    resource_id="res-video-mechanical-vibration",
                    type="video",
                    title="机械振动 简谐运动 物理题目讲解",
                    target_topic=topic,
                    difficulty="中级",
                    content={"url": "https://www.bilibili.com/video/BV1VIBRATION", "bvid": "BV1VIBRATION", "author": "测试UP", "description": "机械振动 简谐运动 弹簧振子 物理题目讲解"},
                    source_refs=[{"document_id": "doc-bili", "chunk_id": "chunk-vibration", "course_id": "ai-course"}],
                    personalized_reason="机械振动视频搜索测试",
                    tags=["机械振动", "简谐运动"],
                )
            ],
            "source": "bilibili_live",
        }

    agent.retrieve_screened_videos = fake_retrieve
    context = TutorTurnContext(
        message="找一下机械振动相关物理题目相关的视频",
        conversation_id="video-drift-unified-test",
        recent_messages=[{"role": "user", "text": "我说的是 生成可交互模型 不是PPT"}],
        last_assistant_answer="我会生成可交互模型，不生成 PPT。",
    )

    events = [event async for event in agent.execute_plan(agent.plan_turn(context), context)]

    assert "机械振动" in captured["topic"]
    assert "不是PPT" not in captured["topic"]
    assert any(event["type"] == "resource.create" and event["resource"]["type"] == "video" for event in events)


def test_video_filter_keeps_internal_combustion_teaching_results():
    agent = OrchestratorAgent()
    teaching = LearningResource(
        resource_id="res-teaching-engine",
        type="video",
        title="【九年级物理】四冲程内燃机工作动画",
        target_topic="内燃机",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVTEACH", "description": "热机 原理 冲程 教学 动画", "play": 1000},
        source_refs=[],
        personalized_reason="教学视频",
        tags=[],
    )
    entertainment = LearningResource(
        resource_id="res-entertainment-engine",
        type="video",
        title="内燃机永不过时，内燃机的魅力谁懂",
        target_topic="内燃机",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVENT", "description": "内燃机情怀剪辑", "play": 999999},
        source_refs=[],
        personalized_reason="泛娱乐视频",
        tags=[],
    )

    filtered = agent.filter_video_resources("内燃机", [entertainment, teaching], limit=6)

    assert [resource.resource_id for resource in filtered] == ["res-teaching-engine"]


def test_video_filter_rejects_ppt_ai_tool_results_for_mechanical_vibration():
    agent = OrchestratorAgent()
    teaching = LearningResource(
        resource_id="res-vibration-teaching",
        type="video",
        title="高中物理 机械振动 简谐运动 题目讲解",
        target_topic="机械振动",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVTEACHVIB", "description": "机械振动 简谐运动 弹簧振子 物理 教学 题", "play": 1000},
        source_refs=[],
        personalized_reason="教学视频",
        tags=[],
    )
    ppt_tool = LearningResource(
        resource_id="res-vibration-ppt-tool",
        type="video",
        title="AI工具一键生成机械振动PPT模板",
        target_topic="机械振动",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVPPTTOOL", "description": "AI工具 PPT制作 演示文稿", "play": 999999},
        source_refs=[],
        personalized_reason="无关工具视频",
        tags=[],
    )

    filtered = agent.filter_video_resources("机械振动相关物理题目", [ppt_tool, teaching], limit=6)

    assert [resource.resource_id for resource in filtered] == ["res-vibration-teaching"]


def test_interactive_model_phrasing_is_single_demo_not_resource_bundle():
    agent = OrchestratorAgent()
    # "生成一个X的交互模型" must be ONE interactive demo, never a 7-resource bundle.
    plan = agent.plan_turn(TutorTurnContext(message="给我生成一个动量守恒的交互模型"))
    assert plan.task_type == "hermes_interactive_demo"
    assert plan.payload["expected_app_types"] == ["custom.html"]
    assert plan.payload["expected_resource_types"] == []


def test_interactive_bernoulli_routes_to_custom_html_not_native_work_energy():
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="生成一个伯努利定律的演示动画"))
    assert plan.task_type == "hermes_interactive_demo"
    # Must NOT degrade a fluid/Bernoulli request into the generic physics.work_energy_demo slider.
    assert plan.payload["expected_app_types"] == ["custom.html"]


def test_unified_orchestrator_preserves_interactive_3d_contract():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(TutorTurnContext(message="生成一个伯努利定律的3D可交互演示模型。"))

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "capability_contract_lock"
    assert plan.payload["expected_app_types"] == ["custom.html"]
    assert plan.payload["expected_resource_types"] == []
    assert plan.payload["expected_artifact_kind"] == "interactive_model"


def test_interactive_model_intent_beats_detailed_analysis_wording():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(TutorTurnContext(message="详细讲解一下伯努利定律，并生成一个3D可交互演示模型"))

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "capability_contract_lock"
    assert plan.payload["expected_artifact_kind"] == "interactive_model"


def test_image_question_interactive_animation_beats_quiz_and_analysis_routes():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(
        TutorTurnContext(
            message="生成一下这个物理题目的可交互演示动画",
            image_data=["data:image/png;base64,AAAA"],
        )
    )

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "capability_contract_lock"
    assert plan.payload["expected_resource_types"] == []


def test_interactive_correction_with_not_quiz_stays_interactive_demo():
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(TutorTurnContext(message="我要的是可交互模型动画，不是练习题"))

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "capability_contract_lock"


@pytest.mark.parametrize(
    "message",
    [
        "我要那种可以玩的 三维魔方",
        "我要那种可以玩的三维模型",
        "我要的是 可交互的模型",
    ],
)
def test_playable_spatial_model_followup_routes_to_interactive_demo(message):
    agent = UnifiedOrchestrator()
    plan = agent.plan_turn(TutorTurnContext(message=message))

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "capability_contract_lock"


def test_interactive_app_bug_feedback_routes_to_repair_plan():
    agent = OrchestratorAgent()
    recent_app = {
        "app_id": "app_rubik",
        "app_type": "custom.html",
        "title": "交互式三维魔方爆炸视图模型",
        "payload": {
            "artifact_id": "artifact_rubik_old",
            "layout": "model_generated_interactive_demo",
            "html": "<section><canvas></canvas><button data-action='shuffle'>打乱</button><button data-action='reset'>复原</button></section>",
        },
    }

    plan = agent.plan_turn(TutorTurnContext(message="打乱和复原没有办法正常工作", recent_apps=[recent_app]))

    assert plan.task_type == "hermes_interactive_demo"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["interactive_repair"] is True
    assert plan.payload["context_source"] == "recent_interactive_app"
    assert plan.payload["repair_target_app_id"] == "app_rubik"
    assert plan.payload["repair_target_artifact_id"] == "artifact_rubik_old"
    assert "Previous HTML excerpt" in plan.payload["source_material"]
    assert plan.payload["expected_app_types"] == ["custom.html"]


def test_unified_orchestrator_interactive_bug_feedback_routes_to_repair_plan():
    agent = UnifiedOrchestrator()
    recent_app = {
        "app_id": "app_rubik",
        "app_type": "custom.html",
        "title": "交互式三维魔方爆炸视图模型",
        "payload": {"layout": "model_generated_interactive_demo", "html": "<section>旧模型</section>"},
    }

    plan = agent.plan_turn(TutorTurnContext(message="这个模块有问题，按钮没反应，修一下", recent_apps=[recent_app]))

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "interactive_app_repair"
    assert plan.payload["expected_artifact_kind"] == "interactive_model"


def test_interactive_app_feature_edit_reads_existing_model_not_latest_report_shell():
    agent = UnifiedOrchestrator()
    real_model = {
        "app_id": "app_real_model",
        "app_type": "custom.html",
        "title": "三维魔方矩阵旋转交互渲染模型",
        "payload": {
            "artifact_id": "artifact_real_model",
            "layout": "model_generated_interactive_demo",
            "html": "<section><canvas></canvas><button data-action='reset'>复原</button><script>requestAnimationFrame(()=>{});</script></section>",
        },
    }
    latest_wrong_report = {
        "app_id": "app_wrong_report",
        "app_type": "custom.html",
        "title": "模型自动复原按钮交互演示",
        "payload": {
            "artifact_id": "artifact_wrong_report",
            "html": "<main data-learnforge-report='detailed-analysis'><div>LearnForge Reading Studio</div><p>这是报告，不是模型。</p></main>",
        },
    }

    plan = agent.plan_turn(
        TutorTurnContext(
            message="我需要这个模型里面有一个自动复原按钮",
            recent_apps=[real_model, latest_wrong_report],
        )
    )

    assert plan.task_type == "unified_hermes"
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["route_source"] == "interactive_app_repair"
    assert plan.payload["repair_target_app_id"] == "app_real_model"


def test_interactive_general_physics_does_not_force_native_demo():
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="生成一下流体的能量守恒和压强变化演示"))
    assert plan.payload["expected_app_types"] == ["custom.html"]


def test_custom_html_skill_does_not_misroute_fluid_demo_into_sorting():
    skill = SkillRegistry().get("custom_html_app_skill")
    # A weak Bernoulli demo whose script body happens to contain the word "sort"/"bubble"
    # must NOT be replaced by the sorting widget. Topic detection runs on the topic, not html.
    inert_html = """
<section>
  <h2>伯努利流体沙盒</h2>
  <label>入口流速 <input type="range"></label>
  <div>压强 P1 101.30 kPa</div>
  <script>const sorted = bubbleSort(arr); /* helper only */</script>
</section>
"""
    output = skill.run(SkillInput(topic="伯努利定律文丘里管流体模拟", payload={"html": inert_html}))
    html = str(output.payload["html"])
    assert 'data-learnforge-widget="sorting-demo"' not in html


def test_custom_html_skill_keeps_generated_bernoulli_html_for_runtime_verification():
    skill = SkillRegistry().get("custom_html_app_skill")
    broken_html = "<section><h2>伯努利演示</h2><button>开始</button><button>重置</button></section>"

    output = skill.run(
        SkillInput(
            topic="生成一个伯努利定律的3D可交互演示模型",
            payload={"html": broken_html},
        )
    )
    html = str(output.payload["html"])

    assert output.payload["valid"] is True
    assert output.payload["fallback_used"] is False
    assert html == broken_html
    assert 'data-learnforge-widget="bernoulli-venturi-demo"' not in html


def test_short_widget_title_collapses_huge_topic():
    skill = SkillRegistry().get("custom_html_app_skill")
    huge = "安排！虽然在上一次对话中，我已经为你生成过一个伯努利定律文丘里管交互沙盒，" * 6
    title = skill.short_widget_title(huge, "互动学习")
    assert len(title) <= 40
    assert "\n" not in title


class _NoopHermesRuntime:
    def prepare(self):
        return None


class _FailingHermesTaskExecutor:
    async def run_resource_bundle(self, plan, context, rag_context):
        raise ModelGatewayError("simulated hermes failure")


@pytest.mark.asyncio
async def test_orchestrator_image_generation_failure_does_not_create_fake_app(monkeypatch):
    class FakeImageClient:
        async def generate(self, request):
            return ImageResult(
                provider="gemini",
                prompt=request.prompt,
                image_url="data:image/png;base64,test-image",
                overlay_labels=request.overlay_labels,
                metadata={"model": "fake-gemini-image"},
            )

    class FakeImageGatewayRouter:
        planner = ImagePromptPlanner()
        client = FakeImageClient()

    monkeypatch.setattr("app.canvas.materializer.ImageGatewayRouter", FakeImageGatewayRouter)

    agent = OrchestratorAgent()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = _FailingHermesTaskExecutor()
    context = TutorTurnContext(message="请基于排序算法生成一张教学图片", model_provider="gemini")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    image_apps = [event["app"] for event in events if event["type"] == "app.create" and event["app"]["app_type"] == "image.explanation"]
    assert plan.payload["capability"] == "image_explanation"
    assert image_apps == []
    assert not any(event["type"] == "app.link.create" for event in events)
    assert not any(event["type"] == "run.step" and event["step_name"] == "contract_fallback" for event in events)
    assert any(event["type"] == "run.done" and event["status"] == "failed" for event in events)


def test_contextual_ppt_ignores_status_ack_and_binds_semantic_english_answer():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请你把上面我和你聊天的那些内容 整理成一个PPT",
        last_assistant_answer="✅ 正在深度分析题目…",
        recent_messages=[
            {"role": "assistant", "text": "Reading Comprehension\nSection A\nDirections: choose one word for each blank."},
            {"role": "assistant", "text": "✅ 正在深度分析题目…"},
        ],
    )

    plan = agent.plan_turn(context)
    rag_context = agent._rag_context_for_plan(plan, context)

    assert plan.task_type == "hermes_ppt"
    assert plan.payload["context_source"] == "last_assistant_answer"
    assert "Reading Comprehension" in plan.payload["source_material"]
    assert "正在深度分析" not in plan.payload["source_material"]
    assert rag_context["context"] == ""
    assert rag_context["source_refs"] == []


@pytest.mark.asyncio
async def test_contextual_request_with_ambiguous_recent_windows_blocks_without_canvas():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="把上面内容整理成 PPT",
        last_assistant_answer="✅ 正在深度分析题目…",
        recent_apps=[
            {"app_id": "app_english", "app_type": "custom.html", "title": "英语阅读理解详细解析"},
            {"app_id": "app_physics", "app_type": "custom.html", "title": "牛顿第二定律交互模型"},
        ],
        conversation_id="ambiguous-context-test",
    )

    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    assert plan.task_type == "clarification_required"
    assert not any(event["type"] == "app.create" for event in events)
    assert any(event["type"] == "run.done" and event["status"] == "blocked" for event in events)
    assert "不能确定" in "".join(event.get("text", "") for event in events if event["type"] == "assistant.delta")


@pytest.mark.asyncio
async def test_detailed_analysis_with_uploaded_image_uses_current_attachment_not_course_rag():
    class CapturingDetailedExecutor:
        captured: dict[str, object] = {}

        async def run_detailed_analysis(self, plan, context, rag_context, run_id=None):
            self.captured["rag_context"] = dict(rag_context)
            return (
                "<!DOCTYPE html><html><head><title>英语图片详细解析</title></head>"
                "<body><section><h2>Reading Comprehension - Section A</h2>"
                "<p>Directions: choose one word for each blank.</p></section></body></html>"
            )

    agent = OrchestratorAgent()
    executor = CapturingDetailedExecutor()
    agent.hermes_executor = executor
    context = TutorTurnContext(
        message="请生成这张英语图片的详细分析报告",
        image_data=["data:image/jpeg;base64,not-a-real-image-but-routes-as-upload"],
        conversation_id="detailed-image-rag-isolation-test",
    )
    plan = agent.plan_turn(context)

    events = [event async for event in agent.execute_plan(plan, context)]
    rag_context = executor.captured["rag_context"]

    assert plan.task_type == "detailed_analysis"
    assert rag_context["context"] == ""
    assert rag_context["context_priority"] == "current_attachment"
    assert all(ref.get("source_type") == "current_attachment" or ref.get("document_id") == "conversation" for ref in rag_context["source_refs"])
    assert not any("质点运动学" in str(event) or "牛顿第二定律" in str(event) for event in events)


@pytest.mark.asyncio
async def test_orchestrator_notes_creates_topic_bound_app_and_memory():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请把本轮学习总结到笔记 App",
        last_assistant_answer="我们刚刚讲了排序算法，重点包括冒泡排序、快速排序、归并排序和堆排序的核心思想、时间复杂度和适用场景。",
    )
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    notes_apps = [event["app"] for event in events if event["type"] == "app.create" and event["app"]["app_type"] == "notes.session"]
    memories = [event["memory"] for event in events if event["type"] == "memory.update" and event["memory"]["memory_type"] == "session_notes"]
    assert plan.payload["topic"] == "排序算法"
    assert len(notes_apps) == 1
    assert notes_apps[0]["title"] == "排序算法学习笔记"
    assert notes_apps[0]["payload"]["topic"] == "排序算法"
    assert "梯度" not in str(notes_apps[0]["payload"])
    assert memories
    assert memories[0]["structured_payload"]["topic"] == "排序算法"


@pytest.mark.asyncio
async def test_orchestrator_notes_emits_app_before_resource_for_current_message_binding():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请把刚才内容整理成学习笔记",
        last_assistant_answer="我们正在学习排序算法，包括冒泡排序、快速排序和归并排序。",
        conversation_id="notes-order-test",
    )
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    first_app_index = next(index for index, event in enumerate(events) if event["type"] == "app.create" and event["app"]["app_type"] == "notes.session")
    first_resource_index = next(index for index, event in enumerate(events) if event["type"] == "resource.create")
    assert first_app_index < first_resource_index


@pytest.mark.asyncio
async def test_orchestrator_keeps_generation_markers_out_of_persisted_chat_history():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请讲一下物理里的动能定理",
        conversation_id="marker-clean-test",
    )
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    streamed_text = "".join(event.get("text", "") for event in events if event["type"] == "assistant.delta")
    stored_messages = agent.store.list_chat_messages(
        student_id=context.student_id,
        course_id=context.course_id,
        conversation_id=context.conversation_id,
        limit=10,
    )
    assistant_messages = [message for message in stored_messages if message["role"] == "assistant"]
    assert "[[generate:" in streamed_text
    assert assistant_messages
    assert all("[[generate:" not in message["text"] for message in assistant_messages)


@pytest.mark.asyncio
async def test_orchestrator_interactive_demo_failure_does_not_create_fake_app():
    class FailingModelClient:
        async def complete(self, messages, stream=False):
            raise ModelGatewayError("simulated regeneration failure")

        def extract_assistant_text(self, response):
            return ""

    class FailingModelGateway:
        def normalize_provider(self, provider=None):
            return "gemini"

        def client(self, provider=None):
            return FailingModelClient()

    agent = OrchestratorAgent()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = _FailingHermesTaskExecutor()
    agent.model_gateway = FailingModelGateway()
    context = TutorTurnContext(message="请生成一个计算机里的哈希表冲突演示")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    custom_apps = [event["app"] for event in events if event["type"] == "app.create" and event["app"]["app_type"] == "custom.html"]
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["topic"] == "哈希表冲突"
    assert custom_apps == []
    assert not any(event["type"] == "app.link.create" for event in events)
    assert any(event["type"] == "run.done" and event["status"] == "failed" for event in events)


@pytest.mark.asyncio
async def test_unified_answer_only_guard_rejects_wrong_html_artifact():
    class MisroutingHermesExecutor:
        def is_cancelled(self, run_id):
            return False

        def clear_run(self, run_id):
            return None

        async def run_hermes(self, plan, context, rag_context, **kwargs):
            return HermesTaskResult(
                capability="detailed_analysis",
                summary="误判报告",
                raw_html="<!DOCTYPE html><html><body><h1>错误报告</h1></body></html>",
                text_response="✅ 分析完成！报告已生成并推送到画布。",
                trace=["misrouted_html"],
            )

        async def run_answer_only(self, context, rag_context, *, rejected_capability="", run_id=None):
            return HermesTaskResult(
                capability="answer_only",
                summary="纯文本回答",
                text_response="我能根据当前对话和记忆回答，但不会为这个问题生成页面。",
                trace=["answer_only_guard_retry", f"rejected_capability:{rejected_capability}"],
            )

    agent = UnifiedOrchestrator()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = MisroutingHermesExecutor()
    context = TutorTurnContext(message="你还能记得我前面和你聊了什么吗", conversation_id="answer-only-guard-test")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]
    assistant_text = "".join(event.get("text", "") for event in events if event.get("type") == "assistant.delta")

    assert any(event["type"] == "run.step" and event["step_name"] == "answer_only_guard" and event["status"] == "completed" for event in events)
    assert not any(event["type"] == "app.create" for event in events)
    assert not any(event["type"] == "resource.create" for event in events)
    assert "不会为这个问题生成页面" in assistant_text
    assert any(event["type"] == "run.done" and event["status"] == "completed" for event in events)


@pytest.mark.asyncio
async def test_unified_explicit_video_search_locks_capability_and_materializes_real_results():
    class VideoSearchHermesExecutor:
        def __init__(self):
            self.calls = 0

        def is_cancelled(self, run_id):
            return False

        def clear_run(self, run_id):
            return None

        async def run_hermes(self, plan, context, rag_context, **kwargs):
            self.calls += 1
            if plan.payload.get("capability") == "video_search":
                return HermesTaskResult(capability="video_search", summary="锁定视频搜索", topic="快速排序", trace=["video_search_retry"])
            return HermesTaskResult(capability="answer_only", summary="误判为文本回答", text_response="你可以自己去 B 站搜一下。", trace=["wrong_answer_only"])

        async def run_answer_only(self, context, rag_context, *, rejected_capability="", run_id=None):
            return HermesTaskResult(capability="answer_only", summary="文本回答", text_response="纯文本回答")

    agent = UnifiedOrchestrator()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = VideoSearchHermesExecutor()

    async def fake_retrieve(topic, context, limit=6):
        return {
            "videos": [
                LearningResource(
                    resource_id="res-video-quick-sort",
                    type="video",
                    title="快速排序算法详解",
                    target_topic=topic,
                    difficulty="中级",
                    content={"url": "https://www.bilibili.com/video/BV1QSORT", "bvid": "BV1QSORT", "author": "测试UP", "description": "快速排序原理和动画讲解", "play": 12345},
                    source_refs=[{"document_id": "doc-bili", "chunk_id": "chunk-qs", "course_id": "ai-course"}],
                    personalized_reason="实时视频搜索测试",
                    tags=["#快速排序"],
                )
            ],
            "source": "bilibili_live",
        }

    agent.retrieve_screened_videos = fake_retrieve
    context = TutorTurnContext(message="帮我搜索快速排序的视频", conversation_id="video-lock-test")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]
    assistant_text = "".join(event.get("text", "") for event in events if event.get("type") == "assistant.delta")

    assert any(event["type"] == "run.step" and event["step_name"] == "capability_lock_retry" and event["status"] == "completed" for event in events)
    assert any(event["type"] == "resource.create" and event["resource"]["type"] == "video" for event in events)
    assert any(event["type"] == "app.create" and event["app"]["app_type"] == "video.player" for event in events)
    assert "快速排序算法详解" in assistant_text
    assert "你可以自己去 B 站搜一下" not in assistant_text


@pytest.mark.asyncio
async def test_unified_ppt_derives_ppt_resource_without_consent_flow():
    class PptHermesExecutor:
        def is_cancelled(self, run_id):
            return False

        def clear_run(self, run_id):
            return None

        async def run_hermes(self, plan, context, rag_context, **kwargs):
            return HermesTaskResult(
                capability="ppt",
                summary="PPT deck 已生成",
                topic="主流排序算法",
                text_response="PPT 已生成",
                apps=[
                    {
                        "app_type": "custom.html",
                        "title": "主流排序算法 PPT",
                        "payload": {
                            "html": (
                                "<!DOCTYPE html><html><body><main class='deck'>"
                                "<section class='slide' data-slide='1'><h1>主流排序算法</h1><p>本页说明冒泡排序、快速排序和归并排序的学习目标。</p></section>"
                                "<section class='slide' data-slide='2'><h2>核心比较</h2><p>比较稳定性、时间复杂度、空间复杂度和适用数据规模，帮助学生选择算法。</p></section>"
                                "<script>document.addEventListener('keydown',()=>{});</script></main></body></html>"
                            )
                        },
                    }
                ],
                trace=["ppt_generated"],
            )

        async def run_answer_only(self, context, rag_context, *, rejected_capability="", run_id=None):
            return HermesTaskResult(capability="answer_only", summary="不应走到这里", text_response="不应走到这里")

    agent = UnifiedOrchestrator()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = PptHermesExecutor()
    context = TutorTurnContext(message="生成一份主流排序算法 PPT", conversation_id="ppt-contract-test")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    assert any(event["type"] == "app.create" and event["app"]["app_type"] == "custom.html" for event in events)
    assert any(
        event["type"] == "app.create"
        and event["app"]["payload"].get("artifact_kind") == "ppt_deck"
        for event in events
    )
    assert any(event["type"] == "resource.create" and event["resource"]["type"] == "ppt" for event in events)
    assert not any(event["type"] == "consent_required" for event in events)
    assert any(event["type"] == "run.done" and event["status"] == "completed" for event in events)


@pytest.mark.asyncio
async def test_orchestrator_interactive_demo_missing_app_does_not_create_fake_app():
    agent = OrchestratorAgent()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = _FailingHermesTaskExecutor()
    context = TutorTurnContext(message="请生成一个所有三角函数及其反函数的可交互模型")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    custom_apps = [event["app"] for event in events if event["type"] == "app.create" and event["app"]["app_type"] == "custom.html"]
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["expected_resource_types"] == []
    assert custom_apps == []
    assert not any(event["type"] == "app.link.create" for event in events)
    assert any(event["type"] == "run.done" and event["status"] == "failed" for event in events)


@pytest.mark.asyncio
async def test_orchestrator_does_not_fallback_to_non_gemini_provider_when_gemini_times_out(monkeypatch):
    class TimeoutGeminiClient:
        adapter = "fake_gemini"

        async def complete(self, messages, stream: bool = False):
            raise ModelGatewayError("gemini request timed out after 90s: ConnectTimeout")

        def extract_assistant_text(self, response):
            return ""

        def model_name(self):
            return "gemini-timeout"

    class HealthyLegacyClient:
        adapter = "fake_legacy"

        async def complete(self, messages, stream: bool = False):
            return {
                "id": "legacy-fallback-response",
                "choices": [{"message": {"content": "排序算法会把一组数据按指定顺序重新排列。常见算法包括冒泡排序、选择排序、插入排序、归并排序、快速排序和堆排序。"}}],
                "model": "legacy-test-model",
            }

        def extract_assistant_text(self, response):
            return response["choices"][0]["message"]["content"]

        def model_name(self):
            return "legacy-test-model"

    class FallbackRouter:
        def __init__(self):
            self.clients = {"gemini": TimeoutGeminiClient(), "legacy": HealthyLegacyClient()}
            self.requested_clients: list[str] = []

        def normalize_provider(self, provider=None):
            return provider if provider in {"gemini", "legacy"} else "gemini"

        def fallback_order(self, provider=None):
            return ["gemini", "legacy"]

        def client(self, provider=None):
            normalized = self.normalize_provider(provider)
            self.requested_clients.append(normalized)
            return self.clients[normalized]

    router = FallbackRouter()
    monkeypatch.setattr("app.agents.orchestrator_agent.ModelGatewayRouter", lambda: router)
    agent = OrchestratorAgent()
    plan = AgentPlan(task_type="answer_only", steps=["intent_detect"], payload={"topic": "排序算法", "capability": "answer_only", "requires_canvas": False})
    context = TutorTurnContext(message="来详细介绍一下几种常见的排序算法", model_provider="gemini")

    with pytest.raises(ModelGatewayError):
        await agent.generate_model_tutor_response(plan, context, {"context": "", "source_refs": []}, {})

    assert router.requested_clients == ["gemini"]


@pytest.mark.asyncio
async def test_orchestrator_uses_local_artifact_reply_when_models_fail_after_canvas_success():
    class GoodInteractiveHermesExecutor:
        @staticmethod
        def _has_uploaded_images(context) -> bool:
            return False

        def is_cancelled(self, run_id):
            return False

        def clear_run(self, run_id):
            return None

        async def run_hermes(self, plan, context, rag_context, **kwargs):
            return await self.run_resource_bundle(plan, context, rag_context)

        async def run_resource_bundle(self, plan, context, rag_context):
            html = """
<section data-learnforge-widget="model-generated-interactive-demo">
  <style>
    .hash-stage{min-height:320px;background:#0f172a;color:#f8fafc;padding:12px}
    .hash-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
    canvas{width:100%;height:280px;background:#111827;border:1px solid #334155}
  </style>
  <h2>哈希表冲突交互演示</h2>
  <div class="hash-controls">
    <label>桶数量 <input data-param="buckets" type="range" min="4" max="16" value="8"></label>
    <button type="button" data-action="reset">重置</button>
    <strong data-role="readout">8</strong>
  </div>
  <div class="hash-stage"><canvas data-role="canvas" width="720" height="300"></canvas></div>
  <script>
  (() => {
    const root = document.currentScript.closest('section');
    const canvas = root.querySelector('[data-role=canvas]');
    const ctx = canvas.getContext('2d');
    const input = root.querySelector('[data-param=buckets]');
    const readout = root.querySelector('[data-role=readout]');
    const state = { t: 0, keys: [12, 22, 32, 41, 52, 62, 72, 82, 91] };
    function computeModel() {
      const buckets = Number(input.value || 8);
      return state.keys.map((key, index) => ({ key, bucket: key % buckets, index }));
    }
    function drawScene() {
      const buckets = Number(input.value || 8);
      readout.textContent = `${buckets} 个桶`;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#111827';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width / buckets;
      ctx.font = '13px sans-serif';
      computeModel().forEach((item) => {
        const x = item.bucket * width + 8;
        const y = 48 + item.index * 23 + Math.sin((state.t + item.index) / 12) * 5;
        ctx.fillStyle = item.index % 2 ? '#38bdf8' : '#f59e0b';
        ctx.fillRect(x, y, Math.max(18, width - 16), 17);
        ctx.fillStyle = '#f8fafc';
        ctx.fillText(`key ${item.key}`, x + 4, y + 13);
      });
      ctx.strokeStyle = '#475569';
      for (let i = 0; i <= buckets; i += 1) {
        ctx.beginPath();
        ctx.moveTo(i * width, 24);
        ctx.lineTo(i * width, 292);
        ctx.stroke();
      }
    }
    function updateSimulation() {
      state.t += 1;
      drawScene();
      requestAnimationFrame(updateSimulation);
    }
    root.addEventListener('input', drawScene);
    root.addEventListener('click', (event) => {
      if (event.target.dataset.action === 'reset') {
        input.value = '8';
        drawScene();
      }
    });
    drawScene();
    updateSimulation();
  })();
  </script>
</section>
"""
            return HermesTaskResult(
                capability="interactive_demo",
                topic="哈希表冲突",
                summary="哈希表冲突交互模型已生成。",
                trace=["fake_hermes_runtime"],
                resources=[],
                apps=[
                    {
                        "app_type": "custom.html",
                        "title": "哈希表冲突交互演示",
                        "payload": {
                            "topic": "哈希表冲突",
                            "layout": "model_generated_interactive_demo",
                            "html": html,
                        },
                    }
                ],
            )

    class FailingClient:
        adapter = "failing_model"

        async def complete(self, messages, stream: bool = False):
            raise ModelGatewayError("Gemini HTTP transport error: ConnectError")

        def extract_assistant_text(self, response):
            return ""

        def model_name(self):
            return "failing-model"

    class FailingRouter:
        def __init__(self):
            self.clients = {"gemini": FailingClient()}

        def normalize_provider(self, provider=None):
            return "gemini"

        def fallback_order(self, provider=None):
            return ["gemini"]

        def client(self, provider=None):
            return self.clients[self.normalize_provider(provider)]

    agent = UnifiedOrchestrator()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = GoodInteractiveHermesExecutor()
    agent.model_gateway = FailingRouter()
    context = TutorTurnContext(
            message="请生成一个计算机里的哈希表冲突演示",
        model_provider="gemini",
        conversation_id="local-artifact-fallback-test",
    )
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]
    assistant_text = "".join(event.get("text", "") for event in events if event.get("type") == "assistant.delta")

    assert plan.task_type == "unified_hermes"
    assert any(event["type"] == "app.create" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "artifact_verifier" and event["status"] == "completed" for event in events)
    assert any(event["type"] == "run.done" and event["status"] == "completed" for event in events)
    assert "可交互模型已生成" in assistant_text
    assert "哈希表冲突" in assistant_text
    assert "ModelGatewayError" not in assistant_text
    assert "ConnectError" not in assistant_text


def test_each_resource_skill_validates_output():
    registry = SkillRegistry()
    for name in ["document_skill", "mindmap_skill", "quiz_skill", "ppt_skill", "code_practice_skill", "image_generation_skill", "video_script_skill", "reading_material_skill", "notes_skill"]:
        output = registry.get(name).run(SkillInput(topic="梯度下降"))
        assert output.resource
        assert output.resource.quality_check is None or output.resource.quality_check.passed


def _disabled_test_custom_html_skill_replaces_inert_sorting_demo_with_executable_widget():
    inert_html = """
<section>
  <button>冒泡排序</button><button>插入排序</button>
  <div class="stage"></div>
  <p>请点击上方按钮开始动画...</p>
</section>
"""
    output = SkillRegistry().get("custom_html_app_skill").run(SkillInput(topic="排序算法", payload={"html": inert_html}))
    html = str(output.payload["html"])

    assert output.payload["valid"] is True
    assert "data-learnforge-widget=\"sorting-demo\"" in html
    assert "data-action=\"bubble\"" in html
    assert "class=\"lf-bar\"" in html
    assert "<script" in html.lower()
    assert "fetch(" not in html


def test_custom_html_skill_preserves_quadratic_template_leaks_for_verifier():
    inert_html = """
<section>
  <h2>二次函数与梯度下降动态演示模型</h2>
  <label>二次项系数 (a) {{ a.toFixed(2) }}</label>
  <input type="range">
  <p>学习率 (Learning Rate ${eta$}) {{ learningRate.toFixed(3) }}</p>
  <button>{{ isAuto ? '停止' : '自动迭代' }}</button>
  <div class="stage">等待生成</div>
</section>
"""
    output = SkillRegistry().get("custom_html_app_skill").run(SkillInput(topic="二次函数", payload={"html": inert_html}))
    html = str(output.payload["html"])

    assert output.payload["valid"] is True
    assert output.payload["fallback_used"] is False
    assert "{{" in html
    assert "梯度下降" in html
    assert "学习率" in html


def test_custom_html_skill_keeps_inert_rubik_html_for_runtime_verification():
    inert_html = """
<section>
  <h2>可交互3D魔方还原演示模型</h2>
  <div class="stage"><canvas></canvas></div>
  <button>U</button><button>R</button><button>随机打乱</button><button>复原</button>
</section>
"""
    output = SkillRegistry().get("custom_html_app_skill").run(SkillInput(topic="可交互3D魔方还原演示模型", payload={"html": inert_html}))
    html = str(output.payload["html"])

    assert output.payload["valid"] is True
    assert output.payload["fallback_used"] is False
    assert html == inert_html
    assert "data-learnforge-widget=\"rubik-cube-demo\"" not in html


def test_rubik_demo_without_standard_move_contract_fails_interactive_quality_gate():
    agent = OrchestratorAgent()
    plan = AgentPlan(
        task_type="hermes_interactive_demo",
        steps=[],
        payload={
            "capability": "interactive_demo",
            "topic": "交互式三维魔方爆炸视图模型",
            "source_material": "生成一个魔方可交互模型",
            "expected_app_types": ["custom.html"],
            "requires_canvas": True,
        },
    )
    incomplete_html = """
<section>
  <canvas></canvas>
  <button data-action="rotate">顶层(U)</button>
  <button data-action="shuffle">一键打乱</button>
  <button data-action="reset">复原状态</button>
  <script>
    const state = { cubies: [], queue: [] };
    requestAnimationFrame(function loop(){ requestAnimationFrame(loop); });
    document.body.addEventListener('click', event => {
      const action = event.target.dataset.action;
      if (action === 'rotate') state.queue.push('U');
      if (action === 'shuffle') state.queue.push('random');
      if (action === 'reset') state.queue = [];
    });
  </script>
</section>
"""
    result = HermesTaskResult(
        summary="bad rubik",
        apps=[{"app_type": "custom.html", "title": "魔方", "payload": {"html": incomplete_html}}],
    )

    assert agent.interactive_demo_quality_issue(plan, result) == "rubik_move_controls_incomplete"


def test_interactive_repair_regeneration_prompt_includes_previous_html_and_bug_report():
    agent = OrchestratorAgent()
    plan = AgentPlan(
        task_type="hermes_interactive_demo",
        steps=[],
        payload={
            "capability": "interactive_demo",
            "topic": "交互式三维魔方爆炸视图模型",
            "source_material": "repair",
            "expected_app_types": ["custom.html"],
            "interactive_repair": True,
            "repair_target_app_id": "app_rubik",
            "repair_target_artifact_id": "artifact_old",
            "repair_reason": "打乱和复原没有办法正常工作",
            "previous_html": "<button data-action='shuffle'>一键打乱</button>",
        },
    )

    messages = agent.build_interactive_regeneration_messages(
        plan,
        TutorTurnContext(message="打乱和复原没有办法正常工作"),
        {"context": ""},
        "rubik_move_controls_incomplete",
    )
    prompt = "\n".join(message.content for message in messages)

    assert "INTERACTIVE_APP_REPAIR_MODE" in prompt
    assert "打乱和复原没有办法正常工作" in prompt
    assert "artifact_old" in prompt
    assert "data-action='shuffle'" in prompt
    assert "not an analysis report" in prompt


@pytest.mark.asyncio
async def test_interactive_regeneration_accepts_raw_html_only_output_after_bridging():
    class RawHtmlOnlyClient:
        async def complete(self, messages, stream=False):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"capability":"interactive_demo","summary":"六种三角函数演示","raw_html":"'
                                '<section><h2>六种三角函数演示</h2><canvas width=\\"640\\" height=\\"320\\"></canvas>'
                                '<button data-action=\\"toggle\\">切换函数</button>'
                                '<script>const state={mode:0};document.body.addEventListener(\\"click\\",e=>{if(e.target.dataset.action===\\"toggle\\"){state.mode=(state.mode+1)%6;}});'
                                'function render(){} function tick(){render();requestAnimationFrame(tick)} render(); requestAnimationFrame(tick);</script>'
                                '</section>"}'
                            )
                        }
                    }
                ]
            }

        def extract_assistant_text(self, response):
            return response["choices"][0]["message"]["content"]

    class RawHtmlGateway:
        def normalize_provider(self, provider=None):
            return "gemini"

        def client(self, provider=None):
            return RawHtmlOnlyClient()

    agent = OrchestratorAgent()
    agent.model_gateway = RawHtmlGateway()
    plan = AgentPlan(
        task_type="hermes_interactive_demo",
        steps=[],
        payload={
            "capability": "interactive_demo",
            "topic": "六种三角函数演示",
            "source_material": "生成一个 6 种三角函数的演示 demo",
            "expected_app_types": ["custom.html"],
            "expected_resource_types": [],
            "requires_canvas": True,
        },
    )

    result = await agent.regenerate_interactive_demo_result(
        plan,
        TutorTurnContext(message="生成一个 6 种三角函数的演示 demo"),
        {"context": ""},
        "missing_custom_html_app",
    )

    assert result is not None
    assert result.apps
    assert result.apps[0]["app_type"] == "custom.html"
    assert "六种三角函数演示" in str(result.apps[0]["payload"]["html"])


def test_canvas_materializer_keeps_generic_custom_html_without_topic_rewrite():
    inert_html = """
<section class="lfx-lab lf-concept-demo" data-learnforge-widget="concept-demo">
  <h2>二次函数</h2>
  <p>这是一个通用输入动作输出模板。</p>
</section>
"""
    payload = CanvasMaterializer(store=None).validate_custom_html(
        {"html": inert_html},
        "学习主题",
        source_material="请基于二次函数生成动态演示模型",
    )
    html = str(payload["html"])

    assert payload["fallback_used"] is False
    assert "data-learnforge-widget=\"concept-demo\"" in html
    assert "这是一个通用输入动作输出模板。" in html


def test_canvas_materializer_preserves_sorting_template_for_verifier():
    inert_html = """
<section>
  <h1>算法可视化实验室</h1>
  <select><option>冒泡排序 (Bubble Sort)</option></select>
  <p>数据规模: {{ arraySize }}</p>
  <button>开始执行</button>
  <h2>{{ currentAlgoInfo.name }}</h2>
  <p>{{ currentAlgoInfo.desc }}</p>
</section>
"""
    payload = CanvasMaterializer(store=None).validate_custom_html(
        {"html": inert_html, "topic": "经典排序算法"},
        "学习主题",
        source_material="请生成经典排序算法动态可视化实验室",
    )
    html = str(payload["html"])

    assert payload["fallback_used"] is False
    assert "{{" in html
    assert "currentAlgoInfo" in html


def _disabled_test_custom_html_skill_replaces_unsafe_empty_sorting_demo_with_fallback_widget():
    unsafe_empty_html = """
<section>
  <button>冒泡排序</button><button>插入排序</button>
  <div class="stage"></div>
  <script>fetch("/api/sort").then(() => renderBars([]))</script>
</section>
"""
    output = SkillRegistry().get("custom_html_app_skill").run(SkillInput(topic="排序算法互动演示", payload={"html": unsafe_empty_html}))
    html = str(output.payload["html"])

    assert output.payload["valid"] is True
    assert "data-learnforge-widget=\"sorting-demo\"" in html
    assert "class=\"lf-bar\"" in html
    assert "fetch(" not in html


@pytest.mark.parametrize("topic", ["哈希表冲突互动演示", "抽屉原理哈希冲突演示"])
def _disabled_test_custom_html_skill_replaces_hash_collision_inert_demo_with_dedicated_widget(topic):
    inert_html = """
<section>
  <button>直觉图景</button><button>关键变量</button>
  <div class="stage">请点击上方按钮开始动画...</div>
</section>
"""
    output = SkillRegistry().get("custom_html_app_skill").run(SkillInput(topic=topic, payload={"html": inert_html}))
    html = str(output.payload["html"])

    assert output.payload["valid"] is True
    assert "data-learnforge-widget=\"hash-collision-demo\"" in html
    assert "data-learnforge-widget=\"concept-demo\"" not in html
    assert "addEventListener" in html
    assert "postMessage" not in html


def _disabled_test_custom_html_skill_blocks_parent_message_scripts():
    unsafe_html = """
<section>
  <h2>Unsafe</h2>
  <script>parent.postMessage({type: "widget:height", height: 999999}, "*")</script>
</section>
"""
    output = SkillRegistry().get("custom_html_app_skill").run(SkillInput(topic="安全测试", payload={"html": unsafe_html}))
    html = str(output.payload["html"])

    assert output.payload["valid"] is True
    assert "postMessage" not in html
    assert "blocked unsafe widget script" in html


def _disabled_test_custom_html_skill_validate_widget_rejects_fetch_scripts():
    skill = SkillRegistry().get("custom_html_app_skill")

    assert skill.validate_widget("<section><script>fetch('/api')</script></section>") is False


def _disabled_test_custom_html_skill_validate_widget_rejects_post_message_scripts():
    skill = SkillRegistry().get("custom_html_app_skill")

    assert skill.validate_widget("<section><script>parent.postMessage('x', '*')</script></section>") is False


def test_dashboard_filters_conversation_scoped_session_notes():
    agent = OrchestratorAgent()
    store = agent.store
    store.create_memory(
        EduMemoryItem(
            student_id="demo-student",
            course_id="ai-course",
            memory_type="session_notes",
            content="会话A排序算法学习笔记",
            confidence=0.95,
            importance=0.8,
            decay_rate=0.01,
            evidence_type="session",
            source_agent="notes_skill",
            source_event_id="test-memory-conv-a-note",
            structured_payload={"conversation_id": "conv-a", "topic": "排序算法"},
            tags=["session_notes"],
        )
    )
    store.create_memory(
        EduMemoryItem(
            student_id="demo-student",
            course_id="ai-course",
            memory_type="session_notes",
            content="会话B物理动能定理学习笔记",
            confidence=0.95,
            importance=0.8,
            decay_rate=0.01,
            evidence_type="session",
            source_agent="notes_skill",
            source_event_id="test-memory-conv-b-note",
            structured_payload={"conversation_id": "conv-b", "topic": "动能定理"},
            tags=["session_notes"],
        )
    )

    dashboard_a = store.dashboard("demo-student", course_id="ai-course", conversation_id="conv-a")
    contents = [item.content for item in dashboard_a.memory_evidence]

    assert "会话A排序算法学习笔记" in contents
    assert "会话B物理动能定理学习笔记" not in contents


@pytest.mark.asyncio
async def test_answer_only_does_not_create_notes_app_or_session_memory():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="排序算法的核心思想是什么，有哪些常见类型",
        conversation_id="answer-only-no-notes-test",
        last_assistant_answer="我们正在学习排序算法。",
    )
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    assert plan.payload["capability"] == "answer_only"
    assert not any(event["type"] == "app.create" and event["app"]["app_type"] == "notes.session" for event in events)
    assert not any(event["type"] == "memory.update" and event["memory"]["memory_type"] == "session_notes" for event in events)


def test_notes_context_prefers_recent_user_learning_topic_over_assistant_subconcept():
    agent = OrchestratorAgent()
    context = TutorTurnContext(
        message="请把刚才内容整理成学习笔记",
        recent_messages=[
            {"role": "user", "text": "请详细讲解一下排序算法的核心思想，重点比较冒泡排序、快速排序和归并排序。"},
            {"role": "assistant", "text": "排序算法中可以从消除逆序对理解冒泡排序，也可以从分治理解快速排序和归并排序。"},
        ],
        last_assistant_answer="排序算法中可以从消除逆序对理解冒泡排序，也可以从分治理解快速排序和归并排序。",
    )
    plan = agent.plan_turn(context)

    assert plan.payload["capability"] == "notes"
    assert plan.payload["topic"] == "排序算法"
    assert plan.payload["context_source"] == "recent_user_message"


def test_hermes_parser_repairs_common_literal_json_noise():
    executor = HermesTaskExecutor()
    result = executor.parse_json_result("""
```json
{'summary': 'ok', 'trace': ['skill'], 'resources': [{'type': 'document', 'title': '讲义', 'content': '内容', 'source_refs': ['r1'], 'personalized_reason': '适合'}], 'apps': [],}
```
""")
    assert result.summary == "ok"
    assert result.resources[0]["title"] == "讲义"


def test_hermes_parser_extracts_plaintext_from_final_response_wrapper():
    executor = HermesTaskExecutor()
    result = executor.parse_json_result(
        '{"final_response":"你刚才最想补的是数学推导。","messages":[{"role":"user","content":"用户原话: 我刚才最想补什么？"}]}'
    )

    assert result.text_response == "你刚才最想补的是数学推导。"
    assert result.summary == "Hermes 回复"


def test_hermes_generated_artifact_message_is_capability_specific():
    executor = HermesTaskExecutor()

    assert executor.generated_artifact_message("interactive_demo") == "✅ 交互演示已生成并推送到画布。"
    assert executor.generated_artifact_message("ppt") == "✅ PPT 已生成并推送到画布。"
    assert executor.generated_artifact_message("detailed_analysis") == "✅ 分析完成！报告已生成并推送到画布。"


def test_hermes_interactive_demo_correction_rejects_native_widget_for_regeneration():
    executor = HermesTaskExecutor()
    plan = AgentPlan(
        task_type="hermes_resource_bundle",
        steps=["hermes_runtime"],
        payload={
            "capability": "interactive_demo",
            "expected_app_types": ["custom.html"],
            "topic": "动量守恒碰撞演示",
        },
    )
    result = HermesTaskResult(
        apps=[
            {
                "app_id": "bad-native-demo",
                "app_type": "physics.work_energy_demo",
                "title": "动量守恒碰撞演示",
                "payload": {},
            }
        ]
    )

    fixed = executor.enforce_interactive_demo_app_types(result, plan)

    assert fixed.apps == []
    assert "rejected_native_demo_app_type:physics.work_energy_demo" in fixed.trace
    assert "needs_interactive_regeneration" in fixed.trace


def test_hermes_prompt_keeps_work_energy_interactive_request_as_custom_html():
    agent = OrchestratorAgent()
    context = TutorTurnContext(message="请生成一个物理里面的动能定理演示", conversation_id="prompt-native-demo-test")
    plan = agent.plan_turn(context)
    prompt = HermesTaskExecutor().build_resource_bundle_prompt(plan, context, {"context": "", "source_refs": []})

    assert plan.task_type == "hermes_interactive_demo"
    assert plan.payload["expected_app_types"] == ["custom.html"]
    assert "physics.work_energy_demo" in prompt
    assert "When expected_app_types is [\"custom.html\"], you MUST return custom.html" in prompt
    assert "STRICT NAMING RULE" in prompt
    assert "测试题" in prompt
    assert "Escape every newline inside string values" in prompt
    assert "HARD ARTIFACT CONTRACT" in prompt
    assert '"expected_resource_types": []' in prompt
    assert '"required_outputs": ["custom.html"]' in prompt


def test_ppt_requests_use_guizang_html_deck_skill():
    agent = OrchestratorAgent()
    context = TutorTurnContext(message="帮我做一份内燃机的瑞士风 PPT", conversation_id="prompt-guizang-ppt-test")
    plan = agent.plan_turn(context)
    prompt = HermesTaskExecutor().build_resource_bundle_prompt(plan, context, {"context": "", "source_refs": []})

    assert plan.task_type == "hermes_ppt"
    assert "guizang-ppt-skill" in plan.payload["hermes_skills"]
    assert plan.payload["expected_app_types"] == ["custom.html"]
    assert plan.payload["expected_resource_types"] == ["ppt"]
    assert "Guizang" in prompt or "guizang-ppt-skill" in prompt
    assert "single-file HTML horizontal-swipe deck" in prompt
    assert '"custom.html"' in prompt


def test_ppt_intent_wins_over_broad_bundle_phrase():
    agent = OrchestratorAgent()
    context = TutorTurnContext(message="生成一套大学物理的简单介绍ppt", conversation_id="prompt-ppt-intent-priority-test")
    plan = agent.plan_turn(context)

    assert plan.task_type == "hermes_ppt"
    assert plan.payload["capability"] == "ppt"
    assert "guizang-ppt-skill" in plan.payload["hermes_skills"]
    assert plan.payload["expected_app_types"] == ["custom.html"]
    assert plan.payload["expected_resource_types"] == ["ppt"]


def test_ppt_contract_does_not_synthesize_missing_deck_or_resource():
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="生成一套大学物理的简单介绍ppt"))
    result = HermesTaskResult(
        summary="model forgot required ppt artifacts",
        resources=[],
        apps=[],
        trace=["missing_ppt_artifacts"],
    )

    fixed = agent.complete_hermes_contract(plan, result, [{"source": "test"}])

    assert fixed.apps == []
    assert fixed.resources == []
    assert any("strict_ppt_generation:no_local_fallback" in item for item in fixed.trace)


def test_strict_generation_verifier_rejects_contract_fallback_apps():
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="生成一套英语阅读理解ppt"))

    verification = agent.verify_artifacts(
        plan,
        None,
        {
            "canvas_materializer": {
                "apps": [
                    {
                        "app_id": "app_fake_ppt",
                        "app_type": "custom.html",
                        "title": "假 PPT",
                        "payload": {"layout": "contract_fallback_guizang_ppt", "fallback_used": True},
                    }
                ],
                "resources": [{"resource_id": "res_fake", "type": "ppt", "title": "假 PPT"}],
            }
        },
    )

    assert verification["passed"] is False
    assert "rejected_fallback_app:contract_fallback_guizang_ppt" in verification["missing_artifacts"]
    assert "rejected_fallback_payload" in verification["missing_artifacts"]


def test_strict_generation_verifier_rejects_cross_type_artifacts():
    agent = OrchestratorAgent()
    plan = AgentPlan(
        task_type="unified_hermes",
        steps=[],
        payload={
            "capability": "interactive_demo",
            "requires_canvas": True,
            "expected_app_types": ["custom.html"],
            "expected_resource_types": [],
        },
    )

    verification = agent.verify_artifacts(
        plan,
        None,
        {
            "canvas_materializer": {
                "apps": [
                    {
                        "app_id": "app_demo",
                        "app_type": "custom.html",
                        "title": "交互模型",
                        "payload": {"html": "<!DOCTYPE html><html><body><canvas></canvas><script>requestAnimationFrame(()=>{});</script></body></html>"},
                    }
                ],
                "resources": [{"resource_id": "res_wrong", "type": "document", "title": "错误文档"}],
            }
        },
    )

    assert verification["passed"] is False
    assert "unexpected_resource_type:document" in verification["missing_artifacts"]


def test_hermes_executor_uses_gemini_only_even_when_non_gemini_configured():
    executor = HermesTaskExecutor()
    executor.settings = SimpleNamespace(
        project_root=executor.settings.project_root,
        hermes_home='.runtime/hermes-test',
        hermes_provider='legacy-provider',
        gemini_api_key='dummy',
        gemini_text_model='gemini-3.1-pro-preview',
        gemini_image_model='gemini-3-pro-image',
    )

    assert executor.provider_attempts() == [('gemini', 'gemini-3.1-pro-preview')]
    assert executor.looks_like_provider_failure('API call failed after 3 retries: HTTP 402: Insufficient account balance')
