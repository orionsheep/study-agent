import pytest
from types import SimpleNamespace

from app.agents.base import AgentPlan, TutorTurnContext
from app.agents.orchestrator_agent import OrchestratorAgent
from app.canvas.materializer import CanvasMaterializer
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


def test_hermes_executor_bridges_mimo_credentials_to_xiaomi_env():
    executor = HermesTaskExecutor()
    executor.settings = SimpleNamespace(
        project_root=executor.settings.project_root,
        hermes_home=".runtime/hermes-test",
        hermes_provider="mimo",
        mimo_api_key="test-mimo-key",
        mimo_base_url="https://token-plan-cn.xiaomimimo.com/v1",
        mimo_text_model="mimo-v2.5-pro",
        gemini_api_key="",
        gemini_text_model="gemini-3.1-pro-preview",
        gemini_image_model="gemini-3-pro-image",
    )
    env = executor.environment()
    assert executor.provider_name() == "xiaomi"
    assert env["MIMO_API_KEY"] == "test-mimo-key"
    assert env["XIAOMI_API_KEY"] == "test-mimo-key"
    assert env["XIAOMI_BASE_URL"] == "https://token-plan-cn.xiaomimimo.com/v1"


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
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="生成动能定理演示"))
    assert plan.task_type == "hermes_interactive_demo"
    events = [event async for event in agent.execute_plan(plan, TutorTurnContext(message="生成动能定理演示"))]
    assert len([event for event in events if event["type"] == "run.step" and event["status"] == "completed"]) >= 3
    assert any(event["type"] == "run.step" and event["step_name"] == "hermes_runtime" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "canvas_materializer" for event in events)
    assert any(event["type"] == "app.link.create" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "model_gateway" and event["status"] == "completed" for event in events)
    assistant_text = "".join(event.get("text", "") for event in events if event["type"] == "assistant.delta")
    assert "MiMo 测试回复" in assistant_text


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


def test_interactive_model_phrasing_is_single_demo_not_resource_bundle():
    agent = OrchestratorAgent()
    # "生成一个X的交互模型" must be ONE interactive demo, never a 7-resource bundle.
    plan = agent.plan_turn(TutorTurnContext(message="给我生成一个动量守恒的交互模型"))
    assert plan.task_type == "hermes_interactive_demo"
    assert plan.payload["expected_app_types"] == ["custom.html"]


def test_interactive_bernoulli_routes_to_custom_html_not_native_work_energy():
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="生成一个伯努利定律的演示动画"))
    assert plan.task_type == "hermes_interactive_demo"
    # Must NOT degrade a fluid/Bernoulli request into the generic physics.work_energy_demo slider.
    assert plan.payload["expected_app_types"] == ["custom.html"]


def test_interactive_general_physics_does_not_force_native_demo():
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="演示一下流体的能量守恒和压强变化"))
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
async def test_orchestrator_image_contract_fallback_generates_gemini_app(monkeypatch):
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
    assert image_apps
    assert image_apps[0]["payload"]["image_url"].startswith("data:image/")
    assert image_apps[0]["payload"]["provider"] == "gemini"
    assert any(event["type"] == "run.step" and event["step_name"] == "contract_fallback" for event in events)
    assert any(event["type"] == "app.link.create" and event["link"]["action"] == "fullscreen" for event in events)


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
async def test_orchestrator_generic_interactive_demo_uses_custom_html_contract_fallback():
    agent = OrchestratorAgent()
    agent.hermes = _NoopHermesRuntime()
    agent.hermes_executor = _FailingHermesTaskExecutor()
    context = TutorTurnContext(message="请演示一下计算机里的哈希表冲突")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    custom_apps = [event["app"] for event in events if event["type"] == "app.create" and event["app"]["app_type"] == "custom.html"]
    assert plan.payload["capability"] == "interactive_demo"
    assert plan.payload["topic"] == "哈希表冲突"
    assert custom_apps
    html = custom_apps[0]["payload"]["html"]
    assert custom_apps[0]["payload"]["layout"] == "contract_fallback_interactive_demo"
    assert "data-learnforge-widget=\"hash-collision-demo\"" in html
    assert "data-role=\"strategy\"" in html
    assert "data-role=\"buckets-grid\"" in html
    assert "data-role=\"a\"" not in html
    assert "<script" in html.lower()
    assert any(event["type"] == "run.step" and event["step_name"] == "custom_html_app_skill" and event["status"] == "completed" for event in events)


@pytest.mark.asyncio
async def test_orchestrator_passes_user_rag_and_tools_to_mimo(fake_mimo_client):
    agent = OrchestratorAgent()
    context = TutorTurnContext(message="我不懂学习率为什么会发散，请结合左侧互动解释")
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]

    assert fake_mimo_client.calls
    messages = fake_mimo_client.calls[-1]
    prompt = "\n".join(message.content for message in messages)
    assert context.message in prompt
    assert "RAG上下文" in prompt
    assert "source_refs" in prompt
    assert "工具输出摘要" in prompt
    assert any(event["type"] == "run.done" and event["status"] == "completed" for event in events)


@pytest.mark.asyncio
async def test_orchestrator_falls_back_to_mimo_when_gemini_times_out(monkeypatch):
    class TimeoutGeminiClient:
        adapter = "fake_gemini"

        async def complete(self, messages, stream: bool = False):
            raise ModelGatewayError("gemini request timed out after 90s: ConnectTimeout")

        def extract_assistant_text(self, response):
            return ""

        def model_name(self):
            return "gemini-timeout"

    class HealthyMiMoClient:
        adapter = "fake_mimo"

        async def complete(self, messages, stream: bool = False):
            return {
                "id": "mimo-fallback-response",
                "choices": [{"message": {"content": "排序算法会把一组数据按指定顺序重新排列。常见算法包括冒泡排序、选择排序、插入排序、归并排序、快速排序和堆排序。"}}],
                "model": "mimo-test-model",
            }

        def extract_assistant_text(self, response):
            return response["choices"][0]["message"]["content"]

        def model_name(self):
            return "mimo-test-model"

    class FallbackRouter:
        def __init__(self):
            self.clients = {"gemini": TimeoutGeminiClient(), "mimo": HealthyMiMoClient()}

        def normalize_provider(self, provider=None):
            return provider if provider in {"gemini", "mimo"} else "gemini"

        def fallback_order(self, provider=None):
            return ["gemini", "mimo"]

        def client(self, provider=None):
            return self.clients[self.normalize_provider(provider)]

    monkeypatch.setattr("app.agents.orchestrator_agent.ModelGatewayRouter", FallbackRouter)
    agent = OrchestratorAgent()
    plan = AgentPlan(task_type="answer_only", steps=["intent_detect"], payload={"topic": "排序算法", "capability": "answer_only", "requires_canvas": False})
    context = TutorTurnContext(message="来详细介绍一下几种常见的排序算法", model_provider="gemini")

    text, trace = await agent.generate_model_tutor_response(plan, context, {"context": "", "source_refs": []}, {})

    assert "排序算法" in text
    assert trace["provider"] == "mimo"
    assert trace["requested_provider"] == "gemini"
    assert trace["provider_fallback_used"] is True
    assert trace["provider_attempts"][0]["provider"] == "gemini"


@pytest.mark.asyncio
async def test_orchestrator_uses_local_artifact_reply_when_models_fail_after_canvas_success():
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
            self.clients = {"gemini": FailingClient(), "mimo": FailingClient()}

        def normalize_provider(self, provider=None):
            return provider if provider in {"gemini", "mimo"} else "gemini"

        def fallback_order(self, provider=None):
            return ["gemini", "mimo"]

        def client(self, provider=None):
            return self.clients[self.normalize_provider(provider)]

    agent = OrchestratorAgent()
    agent.model_gateway = FailingRouter()
    context = TutorTurnContext(
        message="请基于排序算法生成一个可以在左侧画布打开的互动演示 App",
        model_provider="gemini",
        conversation_id="local-artifact-fallback-test",
    )
    plan = agent.plan_turn(context)
    events = [event async for event in agent.execute_plan(plan, context)]
    assistant_text = "".join(event.get("text", "") for event in events if event.get("type") == "assistant.delta")

    assert any(event["type"] == "app.create" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "artifact_verifier" and event["status"] == "completed" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "model_gateway" and event["status"] == "completed" and "本地画布摘要" in str(event.get("detail")) for event in events)
    assert any(event["type"] == "run.done" and event["status"] == "completed" for event in events)
    assert "已为你生成" in assistant_text
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


def test_custom_html_skill_replaces_quadratic_vue_template_bleed_with_executable_widget():
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
    assert output.payload["fallback_used"] is True
    assert "data-learnforge-widget=\"quadratic-demo\"" in html
    assert "data-param=\"a\"" in html
    assert "data-action=\"play\"" in html
    assert "data-drag-point=\"x\"" in html
    assert "data-role=\"svg\"" in html
    assert "{{" not in html
    assert "梯度下降" not in html
    assert "学习率" not in html


def test_custom_html_skill_replaces_inert_rubik_cube_with_dedicated_widget():
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
    assert output.payload["fallback_used"] is True
    assert "data-learnforge-widget=\"rubik-cube-demo\"" in html
    assert "data-move=\"U\"" in html
    assert "data-action=\"scramble\"" in html
    assert "root.addEventListener('click'" in html
    assert "grid-template-columns:minmax(250px,320px) minmax(0,1fr)" in html
    assert "lf-rubik-cubie" in html


def test_canvas_materializer_uses_source_material_to_repair_wrong_custom_html_topic():
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

    assert payload["fallback_used"] is True
    assert "data-learnforge-widget=\"quadratic-demo\"" in html
    assert "data-action=\"play\"" in html
    assert "输入 · 动作 · 输出" not in html


def test_canvas_materializer_replaces_sorting_mustache_template_with_canvas_lab():
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

    assert payload["fallback_used"] is True
    assert "data-learnforge-widget=\"sorting-demo\"" in html
    assert "data-role=\"canvas\"" in html
    assert "Algorithm Motion Lab" in html
    assert "requestAnimationFrame" in html
    assert "{{" not in html
    assert "currentAlgoInfo" not in html


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
        message="请详细讲解一下排序算法的核心思想和常见类型",
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


def test_hermes_interactive_demo_correction_outputs_real_custom_html_widget():
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
    app = fixed.apps[0]
    html = str(app["payload"]["html"])

    assert app["app_type"] == "custom.html"
    assert "data-needs-rescue" not in html
    assert "data-learnforge-widget=\"momentum-demo\"" in html
    assert "<canvas" in html.lower()
    assert "<script" in html.lower()


def test_hermes_prompt_guides_native_physics_demo_instead_of_html():
    agent = OrchestratorAgent()
    context = TutorTurnContext(message="请演示一下物理里面的动能定理", conversation_id="prompt-native-demo-test")
    plan = agent.plan_turn(context)
    prompt = HermesTaskExecutor().build_resource_bundle_prompt(plan, context, {"context": "", "source_refs": []})

    assert plan.payload["expected_app_types"] == ["physics.work_energy_demo"]
    assert "physics.work_energy_demo" in prompt
    assert "Do not generate custom HTML for this case" in prompt
    assert "STRICT NAMING RULE" in prompt
    assert "测试题" in prompt
    assert "Escape every newline inside string values" in prompt


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


def test_ppt_contract_normalizes_legacy_ppt_preview_to_custom_html():
    agent = OrchestratorAgent()
    plan = agent.plan_turn(TutorTurnContext(message="生成一套大学物理的简单介绍ppt"))
    result = HermesTaskResult(
        summary="legacy ppt preview",
        resources=[{"type": "ppt", "title": "大学物理 PPT", "content": {"slides": []}, "source_refs": []}],
        apps=[{"app_type": "ppt.preview", "title": "大学物理 PPT 预览", "payload": {"slides": []}}],
        trace=["legacy_ppt_preview"],
    )

    fixed = agent.complete_hermes_contract(plan, result, [{"source": "test"}])

    assert fixed.apps[0]["app_type"] == "custom.html"
    assert fixed.apps[0]["payload"]["deck_kind"] == "guizang-web-ppt"
    assert "<html" in fixed.apps[0]["payload"]["html"].lower()
    assert any("normalized_ppt_app:ppt.preview->custom.html" in item for item in fixed.trace)


def test_hermes_executor_adds_gemini_provider_fallback_after_mimo():
    executor = HermesTaskExecutor()
    executor.settings = SimpleNamespace(
        project_root=executor.settings.project_root,
        hermes_home='.runtime/hermes-test',
        hermes_provider='mimo',
        mimo_api_key='test-mimo-key',
        mimo_base_url='https://token-plan-cn.xiaomimimo.com/v1',
        mimo_text_model='mimo-v2.5-pro',
        gemini_api_key='test-gemini-key',
        gemini_text_model='gemini-3.1-pro-preview',
        gemini_image_model='gemini-3-pro-image',
    )

    assert executor.provider_attempts() == [('xiaomi', 'mimo-v2.5-pro'), ('gemini', 'gemini-3.1-pro-preview')]
    assert executor.looks_like_provider_failure('API call failed after 3 retries: HTTP 402: Insufficient account balance')
