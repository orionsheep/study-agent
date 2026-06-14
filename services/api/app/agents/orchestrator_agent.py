from __future__ import annotations

import asyncio
import json
import re
from html import escape
from typing import Any, AsyncIterator

from app.agents.capability_contract import contract_payload, detect_capability, detect_infographic_render_mode, extract_learning_topic, is_generic_topic, resolve_generation_topic
from app.agents.app_canvas_agent import AppCanvasAgent
from app.agents.base import AgentPlan, TutorTurnContext
from app.agents.evaluator_agent import EvaluatorAgent, EvaluatorAgentInput
from app.agents.knowledge_agent import KnowledgeAgent, KnowledgeAgentInput
from app.agents.memory_agent import MemoryAgent, MemoryAgentInput
from app.agents.planner_agent import PlannerAgent, PlannerAgentInput
from app.agents.profile_agent import ProfileAgent, ProfileAgentInput
from app.agents.recommender_agent import RecommenderAgent, RecommenderAgentInput
from app.agents.resource_bundle_agent import ResourceBundleAgent, ResourceBundleAgentInput
from app.agents.tutor_agent import TutorAgent, TutorAgentInput
from app.agents.verifier_agent import VerifierAgent
from app.canvas.materializer import CanvasMaterializer, MaterializedBundle
from app.database.store import get_store
from app.hermes_runtime.runtime import HermesRuntime
from app.hermes_runtime.task_executor import HermesTaskExecutor, HermesTaskResult
from app.model_gateway.base import ChatMessage
from app.model_gateway.errors import ModelGatewayError, ProviderBlocked
from app.model_gateway.router import ModelGatewayRouter
from app.rag.retriever import CourseRetriever
from app.schemas.app_protocol import (
    AppCreateEvent,
    AppLinkCreateEvent,
    AssistantDelta,
    AssistantDone,
    CanvasApp,
    CanvasPosition,
    CanvasSize,
    ChatAppLink,
    ContextUpdateEvent,
    DashboardUpdateEvent,
    EduMemoryItem,
    LearningResource,
    MemoryUpdateEvent,
    PathUpdateEvent,
    ResourceCreateEvent,
    RunDone,
    RunStarted,
    RunStepEvent,
    new_id,
)
from app.skills.base import SkillInput
from app.skills.custom_html_app_skill import CustomHtmlAppSkill
from app.skills.notes_skill import NotesSkill
from app.video.bilibili import extract_bvid, video_player_payload
from app.video.search import BilibiliSearchError, search_bilibili_videos


def event_dict(event: Any) -> dict[str, Any]:
    return event.model_dump() if hasattr(event, "model_dump") else event


def strip_generation_markers(text: str) -> str:
    return re.sub(r"\[\[generate:[^\]]+\]\][\s\S]*?\[\[/generate\]\]", "", text).strip()


def is_video_search_request(message: str) -> bool:
    lowered = message.lower()
    has_video = any(term in lowered for term in ["b站", "哔哩", "bilibili", "视频", "课程视频"])
    has_search_intent = any(term in lowered for term in ["找", "推荐", "搜索", "有没有", "给我", "查", "视频库"])
    has_script_intent = any(term in lowered for term in ["脚本", "分镜", "旁白", "短视频脚本", "生成视频"])
    return has_video and has_search_intent and not has_script_intent


def clean_video_query(message: str, topic: str | None = None) -> str:
    candidate = topic or message
    candidate = re.sub(r"(帮我|请你|请|给我|找一下|找一找|找|搜索|推荐|查一下|查|有没有|一些|几个|几门|课程|视频库)", " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"(哔哩哔哩|哔哩|bilibili|B站|b站|上面|里面|相关|优质|高质量|视频|教程|课程)", " ", candidate, flags=re.IGNORECASE)
    # normalize "4级"/"6级"/"8级" (digit+级) → "四级"/"六级" so CJK bigrams capture them
    candidate = re.sub(r"([0-9]+)\s*级", lambda m: {"4":"四","6":"六","8":"八","2":"二","3":"三","1":"一","5":"五","7":"七","9":"九"}.get(m.group(1), m.group(1))+"级", candidate)
    candidate = re.sub(r"\s*的\s*", " ", candidate)
    # drop leading location/filler prepositions left after the cleanup (在/上/到/从/这个…)
    candidate = re.sub(r"^[\s，。、]*(在|上|到|从|这个|那个|关于|有关)\s*", "", candidate)
    candidate = re.sub(r"(?<![a-z0-9+#])([a-z])\s+语言", r"\1语言", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" ：:，。！？、\n\t\"'《》“”")
    return candidate or topic or message


class OrchestratorAgent:
    name = "orchestrator_agent"

    def __init__(self) -> None:
        self.store = get_store()
        self.hermes = HermesRuntime()
        self.hermes_executor = HermesTaskExecutor()
        self.model_gateway = ModelGatewayRouter()

    @staticmethod
    def model_provider_label(provider: str | None) -> str:
        return "Gemini" if provider == "gemini" else "MiMo" if provider == "mimo" else "所选模型"

    def model_failure_text(self, provider: str | None, reason: str) -> str:
        label = self.model_provider_label(provider)
        lowered = reason.lower()
        if "blocked_all_providers" in lowered or "所有可用回答模型" in reason:
            return "当前所有回答模型都暂时不可用：请稍后重试，或检查后端的 Gemini/MiMo API 配置和网络连通性。"
        if "timeout" in lowered or "connecttimeout" in lowered:
            return f"{label} 连接超时，后端暂时连不上模型服务。已记录详细错误；可以稍后重试，或切换另一个回答模型。"
        if "missing" in lowered or "api_key" in lowered or "credentials" in lowered:
            return f"{label} 还没有配置可用的 API Key，请先检查后端模型环境变量。"
        if "http 401" in lowered or "http 403" in lowered:
            return f"{label} 鉴权失败，请检查 API Key、模型权限或服务额度。"
        if "http 402" in lowered or "quota" in lowered or "insufficient" in lowered:
            return f"{label} 额度或账户状态不可用，请检查模型服务额度后再试。"
        return f"{label} 暂时没有成功返回，后端已记录详细错误。请稍后重试，或切换另一个回答模型。"

    COURSE_LABELS: dict[str, str] = {
        "ai-course": "人工智能导论",
    }

    CAPABILITY_OBJECTIVE_TEMPLATES: dict[str, str] = {
        "interactive_demo": "通过互动演示深入理解「{topic}」",
        "custom_infographic": "可视化总结「{topic}」的核心知识",
        "quiz": "通过练习题检验「{topic}」的掌握程度",
        "mindmap": "构建「{topic}」的知识结构图",
        "code_lab": "用代码实验验证「{topic}」的原理",
        "image_explanation": "生成「{topic}」的教学图解",
        "ppt": "制作「{topic}」的课件演示",
        "video_script": "编写「{topic}」的视频脚本",
        "notes": "整理「{topic}」的学习笔记",
        "learning_path": "规划「{topic}」的学习路径",
        "resource_bundle": "系统学习「{topic}」的完整资源包",
        "answer_only": "深入理解「{topic}」",
    }

    def _course_label(self, course_id: str) -> str:
        label = self.COURSE_LABELS.get(course_id)
        if label:
            return label
        row = self.store.conn.execute("SELECT title FROM courses WHERE id=?", (course_id,)).fetchone()
        if row:
            title = row["title"] if isinstance(row, dict) else row[0]
            self.COURSE_LABELS[course_id] = str(title)
            return str(title)
        return course_id

    def _infer_objective(self, topic: str, capability: str, context: TutorTurnContext) -> str:
        template = self.CAPABILITY_OBJECTIVE_TEMPLATES.get(capability, "深入理解「{topic}」")
        return template.format(topic=topic)

    def _recent_conversation_topic(self, context: TutorTurnContext) -> str | None:
        """The current learning subject of the conversation, for follow-ups like
        '推荐几个相关的视频' where '相关' refers to what was just discussed. Prefer the most
        recent real user topic; fall back to the last assistant answer."""
        for item in reversed(context.recent_messages or []):
            if str(item.get("role")) != "user":
                continue
            text = str(item.get("text") or "").strip()
            if not text or text == context.message.strip():
                continue
            candidate = self._extract_video_context_topic(text)
            if candidate:
                return candidate
        if context.last_assistant_answer:
            candidate = self._extract_video_context_topic(context.last_assistant_answer)
            if candidate:
                return candidate
        for candidate in [context.current_topic, context.current_objective]:
            cleaned = self._clean_contextual_video_topic(candidate)
            if cleaned:
                return cleaned
        for app in reversed(context.recent_apps or []):
            if not isinstance(app, dict):
                continue
            title = str(app.get("title") or "").strip()
            app_type = str(app.get("app_type") or "")
            if app_type in {"video.player"}:
                continue
            cleaned = self._clean_contextual_video_topic(title)
            if cleaned:
                return cleaned
        return None

    @staticmethod
    def _clean_contextual_video_topic(text: str | None) -> str | None:
        if not text:
            return None
        candidate = str(text).strip()
        candidate = re.sub(r"^(打开|已生成|生成|专属|个性化|可视化)\s*", "", candidate)
        candidate = re.sub(r"(B站视频播放器|视频播放器|播放器|信息图|学习路径|路线图|学习计划|App|app)$", "", candidate).strip(" ：:，。！？、\n\t\"'《》“”")
        candidate = clean_video_query(candidate, None)
        candidate = re.sub(r"^(当前|本轮|这次|这个|该)\s*(主题|内容|学习目标)\s*", "", candidate)
        candidate = candidate.strip(" ：:，。！？、\n\t\"'《》“”")
        if len(candidate) < 3 or is_generic_topic(candidate):
            return None
        return candidate[:80]

    def _extract_video_context_topic(self, text: str | None) -> str | None:
        if not text:
            return None
        source = str(text).strip()
        priority_patterns = [
            r"(四冲程内燃机|内燃机|奥托循环|热机|发动机|机械原理|热力学)",
            r"([\u4e00-\u9fffA-Za-z0-9]{2,32}(?:工作原理|基本原理|物理原理|机械原理|循环|冲程|压缩过程|膨胀过程|做功过程|排气过程))",
        ]
        for pattern in priority_patterns:
            match = re.search(pattern, source, flags=re.IGNORECASE)
            if not match:
                continue
            cleaned = self._clean_contextual_video_topic(match.group(1))
            if cleaned:
                return cleaned
        candidate = extract_learning_topic(source)
        cleaned = self._clean_contextual_video_topic(candidate)
        if cleaned:
            return cleaned
        return None

    def plan_turn(self, context: TutorTurnContext) -> AgentPlan:
        message = context.message.lower()
        if any(term in message for term in ["我是", "画像", "喜欢", "大一"]):
            return AgentPlan(
                task_type="profile_build",
                steps=["intent_detect", "profile_agent", "memory_agent", "dashboard_skill"],
                payload={"topic": "学习画像", "capability": "dashboard", "requires_canvas": False},
            )

        spec = detect_capability(context.message)
        resolved_topic = resolve_generation_topic(context.message, context.last_assistant_answer)
        if isinstance(resolved_topic, tuple):
            topic = str(resolved_topic[0] or context.message) if len(resolved_topic) >= 1 else context.message
            context_source = str(resolved_topic[1] or "current_message") if len(resolved_topic) >= 2 else "current_message"
            source_material = str(resolved_topic[2] or topic) if len(resolved_topic) >= 3 else topic
        else:
            topic = str(resolved_topic or context.message)
            context_source = "last_assistant_answer" if context.last_assistant_answer and topic == context.last_assistant_answer else "current_message"
            source_material = topic
        payload = contract_payload(spec, topic or context.message, context_source, source_material)
        if is_video_search_request(context.message):
            # Video query comes from the user's actual message subject (e.g. "Java入门").
            # BUT follow-ups like "推荐几个相关的视频" / "这方面的视频" reference the prior
            # discussion, so when the request is contextual or has no real subject of its own,
            # fall back to the conversation's current learning topic.
            raw_topic = extract_learning_topic(context.message)
            video_topic = clean_video_query(context.message, raw_topic)
            is_contextual = any(
                marker in context.message
                for marker in ["相关", "这个", "这方面", "这类", "这些", "上面", "刚才", "刚刚", "上述", "该主题", "这部分", "此类"]
            )
            if is_contextual or len(video_topic) < 3 or is_generic_topic(video_topic):
                ctx_topic = self._recent_conversation_topic(context)
                if ctx_topic:
                    video_topic = ctx_topic
            if len(video_topic) < 3:
                video_topic = clean_video_query(context.message, None)
            payload.update(
                {
                    "capability": "video_recommendations",
                    "topic": video_topic,
                    "source_material": context.message,
                    "context_source": "current_message",
                    "expected_app_types": ["video.player"],
                    "expected_resource_types": ["video"],
                    "requires_canvas": True,
                }
            )
            return AgentPlan(
                task_type="video_recommendations",
                steps=["intent_detect", "video_retriever", "video_canvas", "artifact_verifier"],
                payload=payload,
            )
        if spec.name == "notes" and context.recent_messages and any(term in message for term in ["刚才", "上一句", "上面", "上一轮", "本轮"]):
            recent_user_topic = next(
                (
                    extracted
                    for item in reversed(context.recent_messages)
                    if item.get("role") == "user"
                    and str(item.get("text") or "").strip() != context.message.strip()
                    for extracted in [extract_learning_topic(str(item.get("text") or ""))]
                    if extracted and not is_generic_topic(extracted)
                ),
                None,
            )
            if recent_user_topic:
                payload["topic"] = recent_user_topic
                payload["source_material"] = context.last_assistant_answer[:3000] if context.last_assistant_answer else payload.get("source_material", recent_user_topic)
                payload["context_source"] = "recent_user_message"
        if spec.name == "notes" and context.last_assistant_answer and is_generic_topic(payload.get("topic")):
            inherited_topic = extract_learning_topic(context.last_assistant_answer)
            if inherited_topic:
                payload["topic"] = inherited_topic
                payload["source_material"] = context.last_assistant_answer[:3000]
                payload["context_source"] = "last_assistant_answer"
        payload["original_message"] = context.message
        if spec.name == "custom_infographic":
            render_mode = detect_infographic_render_mode(context.message)
            payload["infographic_render_mode"] = render_mode
            if render_mode == "image":
                payload["expected_app_types"] = ["image.explanation"]
                payload["expected_resource_types"] = []
                payload["requires_image_url"] = True
                payload["image_provider_alias"] = "nanobanana"
            else:
                payload["expected_app_types"] = ["custom.html"]
                payload["expected_resource_types"] = ["document"]
                payload["requires_image_url"] = False
        if spec.name == "interactive_demo":
            demo_text = f"{topic} {context.message}".lower()
            # NO DEGRADATION: interactive demos default to custom.html so the model generates a
            # real, topic-specific Canvas/SVG simulation. The generic native demos
            # (physics.work_energy_demo / math.gradient_descent_demo) are ONLY used when the
            # request is SPECIFICALLY about that exact concept — never as a catch-all for broad
            # terms like "物理/能量/力学", which previously hijacked fluids, Bernoulli, waves, etc.
            payload["expected_app_types"] = ["custom.html"]
            # Topics that must always be a bespoke custom.html simulation, never a native slider.
            forces_custom_html = any(
                term in demo_text
                for term in [
                    "伯努利", "文丘里", "流体", "流速", "压强", "管道", "升力", "空气动力",
                    "bernoulli", "venturi", "fluid", "波", "振动", "电路", "几何", "概率",
                ]
            )
            is_exact_work_energy = (not forces_custom_html) and any(
                term in demo_text for term in ["动能定理", "功能原理", "work-energy", "work energy"]
            )
            is_exact_gradient = (not forces_custom_html) and any(
                term in demo_text for term in ["梯度下降", "gradient descent"]
            )
            if any(term in demo_text for term in ["二次函数", "抛物线", "顶点式", "开口方向", "判别式", "quadratic", "parabola"]):
                payload["topic"] = "二次函数" if "二次函数" in demo_text else payload.get("topic", topic)
                payload["source_material"] = context.message
                payload["context_source"] = "current_message"
                payload["expected_app_types"] = ["custom.html"]
            elif is_exact_work_energy:
                payload["expected_app_types"] = ["physics.work_energy_demo"]
            elif is_exact_gradient:
                payload["expected_app_types"] = ["math.gradient_descent_demo"]

        if spec.name == "answer_only":
            return AgentPlan(
                task_type="tutor_turn",
                steps=["intent_detect", "knowledge_agent"],
                payload=payload,
            )
        if spec.name == "learning_path":
            payload.setdefault("app_id", "app-path")
            return AgentPlan(
                task_type="learning_path",
                steps=["intent_detect", "planner_agent", "recommender_agent", "app_canvas_agent", "artifact_verifier"],
                payload=payload,
            )
        if spec.name == "notes":
            payload.setdefault("app_id", "app-notes")
            return AgentPlan(
                task_type="notes_summary",
                steps=["intent_detect", "notes_skill", "artifact_verifier"],
                payload=payload,
            )
        if spec.name == "detailed_analysis":
            payload.update({
                "capability": "detailed_analysis",
                "requires_canvas": True,
                "expected_app_types": ["custom.html"],
                "expected_resource_types": [],
                "is_background_task": True,
                "background_label": "正在深度分析题目…",
            })
            payload.setdefault("app_id", "app-detailed-analysis")
            return AgentPlan(
                task_type="detailed_analysis",
                steps=["intent_detect", "analysis_acknowledge", "hermes_runtime", "html_report_builder", "canvas_materializer", "artifact_verifier"],
                payload=payload,
            )
        return AgentPlan(
            task_type=f"hermes_{spec.name}",
            steps=["intent_detect", "hermes_runtime", "resource_bundle_skill", "canvas_materializer", "artifact_verifier"],
            payload=payload,
        )

    def dispatch_skill(self, skill_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if skill_name == "notes_skill":
            output = NotesSkill().run(SkillInput(**payload))
            return output.model_dump()
        raise KeyError(skill_name)

    def record_trace(self, run_id: str, step: str, order: int, output: dict[str, Any] | None = None, status: str = "completed") -> None:
        self.store.add_step(run_id, order, step, output_json=output or {}, status=status)

    def save_chat_message(
        self,
        context: TutorTurnContext,
        role: str,
        text: str,
        *,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not text:
            return
        self.store.save_chat_message(
            student_id=context.student_id,
            course_id=context.course_id,
            conversation_id=context.conversation_id,
            role=role,
            text=text,
            metadata={"run_id": run_id, **(metadata or {})} if run_id else metadata,
        )

    def source_refs_for_plan(self, plan: AgentPlan, context: TutorTurnContext, rag_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        source_material = str(plan.payload.get("source_material") or context.message)
        topic = str(plan.payload.get("topic") or "当前学习主题")
        conversation_ref = {
            "document_id": "conversation",
            "chunk_id": f"chat-{context.conversation_id}-{new_id('ctx')}",
            "course_id": context.course_id,
            "chapter": "Tutor Chat",
            "section": topic,
            "quote_span": [0, min(160, len(source_material))],
            "confidence": 0.94 if plan.payload.get("context_source") == "last_assistant_answer" else 0.88,
        }
        if plan.payload.get("requires_canvas"):
            return [conversation_ref, *rag_refs[:2]]
        return rag_refs

    def missing_required_artifacts(self, plan: AgentPlan, hermes_result: HermesTaskResult | None) -> list[str]:
        if not plan.payload.get("requires_canvas"):
            return []
        expected_apps = [str(item) for item in plan.payload.get("expected_app_types", []) if item]
        expected_resources = [str(item) for item in plan.payload.get("expected_resource_types", []) if item]
        actual_apps = {
            str(item.get("app_type") or item.get("type"))
            for item in ((hermes_result.apps if hermes_result else []) or [])
            if isinstance(item, dict) and (item.get("app_type") or item.get("type"))
        }
        actual_resources = {
            str(item.get("type"))
            for item in ((hermes_result.resources if hermes_result else []) or [])
            if isinstance(item, dict) and item.get("type")
        }
        missing = [f"{app_type} App" for app_type in expected_apps if app_type not in actual_apps]
        missing.extend(f"{resource_type} Resource" for resource_type in expected_resources if resource_type not in actual_resources)
        return missing

    async def repair_hermes_result(
        self,
        plan: AgentPlan,
        context: TutorTurnContext,
        rag_context: dict[str, Any],
        missing: list[str],
    ) -> HermesTaskResult | None:
        repair_payload = {**plan.payload, "protocol_repair_missing": missing}
        repair_plan = AgentPlan(task_type=plan.task_type, steps=plan.steps, payload=repair_payload)
        try:
            return await self.hermes_executor.run_resource_bundle(repair_plan, context, rag_context)
        except Exception:
            return None

    def merge_hermes_results(self, original: HermesTaskResult, repaired: HermesTaskResult) -> HermesTaskResult:
        def merge_items(left: list[dict[str, Any]], right: list[dict[str, Any]], key_names: tuple[str, ...]) -> list[dict[str, Any]]:
            merged: list[dict[str, Any]] = []
            seen: set[str] = set()
            for item in [*left, *right]:
                if not isinstance(item, dict):
                    continue
                key = next((str(item.get(name)) for name in key_names if item.get(name)), json.dumps(item, ensure_ascii=False, sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
            return merged

        return HermesTaskResult(
            summary=repaired.summary or original.summary,
            trace=[*original.trace, *repaired.trace],
            resources=merge_items(original.resources, repaired.resources, ("resource_id", "type", "title")),
            apps=merge_items(original.apps, repaired.apps, ("app_id", "app_type", "title")),
            raw_text=f"{original.raw_text}\n\n---PROTOCOL_REPAIR---\n\n{repaired.raw_text}",
        )

    def fallback_resource_for_type(self, resource_type: str, topic: str, source_refs: list[dict[str, Any]]) -> dict[str, Any]:
        title_by_type = {
            "document": f"{topic}讲义摘要",
            "mindmap": f"{topic}概念导图资源",
            "quiz": f"{topic}自测题库",
            "code_practice": f"{topic}代码实验资源",
            "ppt": f"{topic}PPT大纲",
            "video_script": f"{topic}视频脚本",
            "reading": f"{topic}延伸阅读",
            "notes": f"{topic}学习笔记",
        }
        return {
            "type": resource_type,
            "title": title_by_type.get(resource_type, f"{topic}学习资源"),
            "target_topic": topic,
            "content": {
                "topic": topic,
                "summary": f"根据当前请求生成“{topic}”的{resource_type}资源。",
                "key_points": [f"聚焦 {topic} 的核心概念", "保留当前对话上下文", "可继续扩展为图解、练习或实验"],
            },
            "source_refs": source_refs,
            "personalized_reason": f"由 Capability Contract 在 Hermes 输出不完整时补齐，确保“{topic}”产物落地。",
            "tags": ["contract_fallback", resource_type],
        }

    def fallback_infographic_html(self, topic: str, source_material: str = "") -> str:
        safe_topic = escape(topic)
        safe_source = escape(source_material[:420])
        template = """
<section class="lfx-lab lf-infographic" data-learnforge-widget="lab-infographic">
  <style>
    .lf-infographic .lf-core-loop{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:12px}
    .lf-infographic .lf-node{min-height:120px;display:grid;place-items:center;text-align:center;border:1px solid rgba(255,255,255,.16);border-radius:18px;padding:14px;background:linear-gradient(135deg,rgba(100,216,255,.16),rgba(126,240,178,.08));font-weight:900}
    .lf-infographic .lf-node:nth-child(2){background:linear-gradient(135deg,rgba(255,209,102,.18),rgba(255,122,168,.09))}
    .lf-infographic .lf-node:nth-child(3){background:linear-gradient(135deg,rgba(155,140,255,.18),rgba(100,216,255,.08))}
    .lf-infographic .lf-step-list{display:grid;gap:10px;margin:0;padding:0;list-style:none}
    .lf-infographic .lf-step-list li{display:grid;grid-template-columns:30px minmax(0,1fr);gap:10px;align-items:start;color:#d8def2}
    .lf-infographic .lf-num{display:grid;place-items:center;width:30px;height:30px;border-radius:10px;background:linear-gradient(135deg,#64d8ff,#7ef0b2);color:#06111c;font-weight:950}
    .lf-infographic .lf-source{margin-top:14px;color:#aab3ca;border-left:3px solid #ffd166;padding-left:10px;font-size:12px;line-height:1.6}
    @media(max-width:760px){.lf-infographic .lf-core-loop{grid-template-columns:1fr}}
  </style>
  <div class="lfx-hero">
    <div>
      <div class="lfx-kicker">LearnForge Lab · 信息图</div>
      <h2 class="lfx-title">__LF_TOPIC__</h2>
      <p class="lfx-sub">先抓直觉，再进入可视化主体；把概念拆成输入条件、关键动作、反馈结果和迁移练习。</p>
    </div>
    <div class="lfx-card">
      <strong>学习目标</strong>
      <p>能用自己的话解释它解决什么问题、每一步为什么发生，以及在哪些场景容易用错。</p>
      <div class="lfx-tabs" aria-label="学习视角">
        <button type="button" data-lf-tab="intuition">直觉</button>
        <button type="button" data-lf-tab="method">步骤</button>
        <button type="button" data-lf-tab="check">自测</button>
      </div>
    </div>
  </div>
  <div class="lfx-grid">
    <div class="lfx-card lfx-span-7">
      <strong>核心直觉</strong>
      <div class="lf-core-loop" aria-label="直觉图">
        <div class="lf-node">输入条件</div>
        <div class="lf-node">关键动作</div>
        <div class="lf-node">结果反馈</div>
      </div>
    </div>
    <div class="lfx-card lfx-span-5">
      <strong>掌握覆盖率</strong>
      <div class="lfx-bar-stage" data-lf-bars='[{"label":"直觉","value":86},{"label":"步骤","value":72},{"label":"例题","value":64},{"label":"迁移","value":48}]'></div>
    </div>
    <div class="lfx-card lfx-span-6" data-lf-panel="intuition">
      <strong>概念入口</strong>
      <p>把“__LF_TOPIC__”看成一个可观察过程：输入是什么、动作如何改变状态、输出为什么能验证理解。</p>
    </div>
    <div class="lfx-card lfx-span-6" data-lf-panel="method">
      <strong>步骤/公式</strong>
      <ul class="lf-step-list">
        <li><span class="lf-num">1</span><span>先识别概念入口和触发条件。</span></li>
        <li><span class="lf-num">2</span><span>再比较关键变量、约束和变化方向。</span></li>
        <li><span class="lf-num">3</span><span>最后用最小样例验证每一步。</span></li>
      </ul>
    </div>
    <div class="lfx-card lfx-span-6" data-lf-panel="check">
      <strong>自测题</strong>
      <div data-lf-quiz>
        <p>学习这个主题时，最稳的起点是什么？</p>
        <div class="lfx-toolbar">
          <button type="button" data-lf-answer="false">直接背结论</button>
          <button type="button" data-lf-answer="true">先找输入、动作和输出</button>
          <button type="button" data-lf-answer="false">只看复杂例题</button>
        </div>
        <p data-lf-feedback>选择一个答案，系统会即时反馈。</p>
      </div>
    </div>
    <div class="lfx-card lfx-span-6">
      <strong>例题切入</strong>
      <p>拿一个最小样例，写出输入、计算或判断过程、最终输出，再把每一步映射回概念名称。</p>
      <div data-lf-sparkline="[18,28,36,53,61,78,86]"></div>
    </div>
    <div class="lfx-card lfx-span-6">
      <strong>常见误区</strong>
      <ul class="lf-step-list">
        <li><span class="lf-num">!</span><span>只背结论，不知道触发条件。</span></li>
        <li><span class="lf-num">!</span><span>能看懂例子，但不能迁移到新题。</span></li>
      </ul>
    </div>
    <div class="lfx-card lfx-span-6">
      <strong>下一步建议</strong>
      <p>继续生成一道练习题或一个互动演示，把这个概念从“看懂”推进到“会用”。</p>
    </div>
  </div>
  <p class="lf-source">__LF_SOURCE__</p>
</section>
"""
        return template.replace("__LF_TOPIC__", safe_topic).replace(
            "__LF_SOURCE__",
            safe_source or "来源：当前 Tutor Chat 对话与课程 RAG 上下文。",
        )

    def fallback_interactive_html(self, topic: str, source_material: str = "") -> str:
        skill = CustomHtmlAppSkill()
        return skill.fallback_widget(topic, source_material, "")

    def fallback_ppt_html(self, topic: str, source_material: str = "") -> str:
        safe_topic = escape(topic or "主题演示")
        safe_source = escape((source_material or "").strip()[:260])
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{safe_topic} · Web PPT</title>
  <style>
    html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#f6f2e8;color:#141414;font-family:'Noto Sans SC','Helvetica Neue',Arial,sans-serif;}}
    .deck{{height:100%;display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;}}
    .slide{{position:relative;flex:0 0 100%;height:100%;box-sizing:border-box;padding:7vh 8vw;scroll-snap-align:start;display:grid;align-content:center;gap:24px;border-right:1px solid rgba(20,20,20,.14);}}
    .kicker{{font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:#2457ff;font-weight:800;}}
    h1{{font-size:clamp(46px,8vw,116px);line-height:.92;margin:0;font-weight:900;letter-spacing:0;max-width:980px;}}
    h2{{font-size:clamp(34px,5vw,72px);line-height:1;margin:0;font-weight:880;letter-spacing:0;}}
    p,li{{font-size:clamp(18px,2vw,28px);line-height:1.55;max-width:850px;}}
    .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;max-width:1000px;}}
    .card{{border:1px solid #141414;padding:22px;min-height:150px;background:rgba(255,255,255,.45);}}
    .num{{position:absolute;right:36px;bottom:30px;font-size:13px;color:#555;}}
    .hint{{position:absolute;left:36px;bottom:30px;font-size:13px;color:#555;}}
    @media(max-width:720px){{.slide{{padding:52px 28px}}.grid{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <main class="deck" tabindex="0">
    <section class="slide">
      <div class="kicker">Guizang Web PPT · fallback</div>
      <h1>{safe_topic}</h1>
      <p>{safe_source or "围绕当前学习主题生成一份可全屏播放的网页 PPT。"}</p>
      <span class="hint">← → / 滚动翻页</span><span class="num">01</span>
    </section>
    <section class="slide">
      <div class="kicker">Context</div>
      <h2>为什么值得讲</h2>
      <div class="grid">
        <div class="card"><strong>核心问题</strong><p>先把听众最容易困惑的地方摆出来。</p></div>
        <div class="card"><strong>关键概念</strong><p>用一条主线串起定义、机制和应用。</p></div>
        <div class="card"><strong>行动出口</strong><p>最后落到复习、练习或项目实践。</p></div>
      </div>
      <span class="num">02</span>
    </section>
    <section class="slide">
      <div class="kicker">Takeaway</div>
      <h2>三句话带走</h2>
      <ul>
        <li>先抓住“{safe_topic}”的核心变量。</li>
        <li>再用例子验证理解是否能迁移。</li>
        <li>最后通过练习或演示把知识转成能力。</li>
      </ul>
      <span class="num">03</span>
    </section>
  </main>
  <script>
    const deck=document.querySelector('.deck');
    window.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')deck.scrollBy({{left:innerWidth,behavior:'smooth'}});if(e.key==='ArrowLeft')deck.scrollBy({{left:-innerWidth,behavior:'smooth'}});}});
  </script>
</body>
</html>"""

    def fallback_app_for_type(self, app_type: str, topic: str, capability: str = "", source_material: str = "") -> dict[str, Any]:
        title_by_type = {
            "custom.html": f"{topic}信息图",
            "image.explanation": f"{topic}教学图解",
            "physics.work_energy_demo": f"{topic}互动演示",
            "math.gradient_descent_demo": f"{topic}互动演示",
            "mindmap.concept": f"{topic}思维导图",
            "quiz.practice": f"{topic}练习题库",
            "code.lab": f"{topic}代码实验",
            "ppt.preview": f"{topic}PPT预览",
            "video.script": f"{topic}视频脚本",
            "notes.session": f"{topic}学习笔记",
            "resource.center": f"{topic}资源中心",
            "learning.path": f"{topic}学习路径",
            "dashboard.learning": f"{topic}学习仪表盘",
            "video.player": f"{topic}视频播放器",
        }
        payload_by_type = {
            "custom.html": {
                "topic": topic,
                "html": (
                    self.fallback_interactive_html(topic, source_material)
                    if capability == "interactive_demo"
                    else self.fallback_ppt_html(topic, source_material)
                    if capability == "ppt"
                    else self.fallback_infographic_html(topic, source_material)
                ),
                "layout": (
                    "contract_fallback_interactive_demo"
                    if capability == "interactive_demo"
                    else "contract_fallback_guizang_ppt"
                    if capability == "ppt"
                    else "contract_fallback_infographic"
                ),
                "deck_kind": "guizang-web-ppt" if capability == "ppt" else None,
            },
            "image.explanation": {
                "topic": topic,
                "teaching_goal": f"生成一张帮助理解“{topic}”的教学图解",
                "infographic_render_mode": "image" if capability == "custom_infographic" else "teaching_image",
                "provider_alias": "nanobanana" if capability == "custom_infographic" else "gemini",
                "visual_brief": f"面向学习者的“{topic}”信息图，要求构图完整、中文字少而清晰、视觉层级强、适合在画布中全屏展示。",
                "overlay_labels": [
                    {"id": "label-core", "text": "核心概念", "x": 0.18, "y": 0.22},
                    {"id": "label-step", "text": "关键步骤", "x": 0.58, "y": 0.42},
                    {"id": "label-risk", "text": "易错点", "x": 0.72, "y": 0.76},
                ],
            },
            "physics.work_energy_demo": {
                "topic": topic,
                "mass": 2,
                "initialVelocity": 3,
                "finalVelocity": 7,
                "force": 8,
                "displacement": 5,
                "teaching_goal": f"通过调节质量、速度、力和位移理解“{topic}”。",
            },
            "math.gradient_descent_demo": {
                "topic": topic,
                "learningRate": 0.18,
                "initialPoint": 4,
                "iterations": 12,
                "teaching_goal": f"通过滑块观察“{topic}”的动态变化。",
            },
            "mindmap.concept": {"topic": topic, "nodes": [{"id": "root", "label": topic}], "edges": []},
            "quiz.practice": {"questions": [{"stem": f"请用自己的话解释：{topic}", "options": [], "answer": "开放题"}]},
            "code.lab": {"starter_code": "# 在这里实现你的思路\n", "tests": [], "expected_output": "完成后观察输出"},
            "ppt.preview": {"slides": [{"title": topic, "bullets": ["核心概念", "应用场景", "下一步练习"]}]},
            "video.script": {"storyboard": [{"scene": topic, "visual": "主题图解"}], "narration": f"本段解释 {topic}。"},
            "notes.session": {"topic": topic, "key_conclusions": [f"围绕 {topic} 继续整理"]},
            "resource.center": {"topic": topic, "resources": []},
            "learning.path": {"topic": topic, "stages": [{"title": "理解基础", "status": "in_progress"}]},
            "dashboard.learning": {"topic": topic, "status": "ready"},
            "video.player": {"topic": topic, "bvid": "", "url": ""},
        }
        title = title_by_type.get(app_type, f"{topic}学习 App")
        if app_type == "image.explanation" and capability == "custom_infographic":
            title = f"{topic} Nano Banana 信息图"
        return {
            "app_type": app_type,
            "title": title,
            "topic": topic,
            "payload": payload_by_type.get(app_type, {"topic": topic}),
            "personalized_reason": f"由 Capability Contract 补齐“{topic}”的 {app_type} 画布产物。",
        }

    def video_recommendation_app(
        self,
        *,
        topic: str,
        resources: list[LearningResource],
        student_id: str,
        course_id: str,
        conversation_id: str,
        message_id: str,
        run_id: str,
    ) -> CanvasApp:
        source_refs = [ref for resource in resources for ref in resource.source_refs[:1]]
        app = CanvasApp(
            app_type="video.player",
            title=f"{topic} B站视频播放器" if topic else "B站视频播放器",
            icon="Film",
            render_mode="native_react",
            state="focused",
            position=CanvasPosition(x=520, y=730),
            size=CanvasSize(width=720, height=520),
            z_index=78,
            group_id="agent-generated-video",
            payload={
                **video_player_payload(topic or "B站视频推荐", resources),
                "status": "B站视频可播放",
                "tag_system": ["#B站视频", "#视频推荐", "#大学课程"],
            },
            source={
                "student_id": student_id,
                "course_id": course_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "run_id": run_id,
                "skill_name": "bilibili_video_retriever",
                "capability": "video_recommendations",
            },
            source_refs=source_refs,
            personalized_reason=f"根据“{topic}”从本地 B站视频资源池检索，可在专用播放器里直接预览和切换。",
            actions=[
                {"label": "切换视频", "action": "video.select"},
                {"label": "让导师推荐", "action": "tutor.explain"},
            ],
        )
        return self.store.save_app(app, student_id=student_id, course_id=course_id, agent="orchestrator_agent", skill="bilibili_video_retriever")

    def learning_path_app(
        self,
        *,
        path: dict[str, Any],
        student_id: str,
        course_id: str,
        conversation_id: str,
        message_id: str,
        run_id: str,
    ) -> CanvasApp:
        path_id = str(path.get("path_id") or "path-neural-network")
        app_id = f"app-path-{student_id}-{path_id}".replace("_", "-")
        title = str(path.get("title") or "个性化学习路径")
        app = CanvasApp(
            app_id=app_id,
            app_type="learning.path",
            title=title,
            icon="Route",
            render_mode="native_react",
            state="focused",
            position=CanvasPosition(x=420, y=40),
            size=CanvasSize(width=460, height=330),
            z_index=80,
            group_id="agent-generated-learning-path",
            payload={
                "path_id": path_id,
                "path": path,
                "topic": path.get("title") or "学习路径",
                "status": "已生成个性化学习路径",
            },
            source={
                "student_id": student_id,
                "course_id": course_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "run_id": run_id,
                "skill_name": "planner_agent",
                "capability": "learning_path",
            },
            source_refs=[],
            personalized_reason="根据当前学习画像、掌握度和学习目标生成，可作为后续资源推送和阶段聚焦入口。",
            actions=[{"label": "聚焦当前阶段", "action": "path.focus_current"}],
        )
        return self.store.save_app(app, student_id=student_id, course_id=course_id, agent="orchestrator_agent", skill="planner_agent")

    def merge_video_resources(
        self,
        local_resources: list[LearningResource],
        live_resources: list[LearningResource],
        *,
        limit: int = 6,
    ) -> list[LearningResource]:
        merged: list[LearningResource] = []
        seen: set[str] = set()
        for resource in [*local_resources, *live_resources]:
            key = extract_bvid(resource) or str(resource.content.get("url") or resource.resource_id)
            if key in seen:
                continue
            seen.add(key)
            merged.append(resource)
            if len(merged) >= limit:
                break
        return merged

    @staticmethod
    def _video_text(resource: LearningResource) -> str:
        content = resource.content or {}
        return " ".join(
            [
                resource.title,
                resource.target_topic,
                str(content.get("description") or ""),
                str(content.get("tags") or ""),
                str(content.get("author") or ""),
            ]
        ).casefold()

    @staticmethod
    def _video_terms(topic: str) -> list[str]:
        text = (topic or "").casefold()
        ascii_terms = re.findall(r"[0-9a-zA-Z+#]{2,}", text)
        cjk_terms: list[str] = []
        for run in re.findall(r"[\u4e00-\u9fff]{2,}", text):
            cjk_terms.append(run)
            cjk_terms.extend(run[i : i + 2] for i in range(max(0, len(run) - 1)))
        stopwords = {"教程", "课程", "视频", "学习", "入门", "基础", "推荐", "相关", "当前", "主题"}
        terms: list[str] = []
        seen: set[str] = set()
        for term in [*ascii_terms, *cjk_terms]:
            if term in stopwords or term in seen:
                continue
            seen.add(term)
            terms.append(term)
        return terms

    @staticmethod
    def _video_requires_educational_signal(topic: str) -> bool:
        lowered = (topic or "").casefold()
        return any(term in lowered for term in ["内燃机", "四冲程", "奥托循环", "热机"])

    @staticmethod
    def _video_has_educational_signal(haystack: str) -> bool:
        return any(
            term in haystack
            for term in [
                "教学", "教程", "课程", "公开课", "讲解", "详解", "知识点", "考点",
                "初中", "高中", "大学", "物理", "九年级", "原理", "工作原理",
                "冲程", "热机", "奥托循环", "动画", "实验", "题", "做题",
            ]
        )

    @staticmethod
    def _video_has_negative_signal(haystack: str) -> bool:
        return any(
            term in haystack
            for term in [
                "搞笑", "美女", "成人", "擦边", "福利", "不笑算我输", "极限过审",
                "致敬", "魅力谁懂", "永不过时", "悲鸣", "声音带来", "情怀",
                "minecraft", "我的世界", "游戏", "建筑教程", "内燃机车",
            ]
        )

    def filter_video_resources(self, topic: str, resources: list[LearningResource], *, limit: int = 6) -> list[LearningResource]:
        terms = self._video_terms(topic)
        if not terms:
            return resources[:limit]
        ranked: list[tuple[int, LearningResource]] = []
        for resource in resources:
            haystack = self._video_text(resource)
            if self._video_has_negative_signal(haystack):
                continue
            if self._video_requires_educational_signal(topic) and not self._video_has_educational_signal(haystack):
                continue
            score = sum(1 for term in terms if term in haystack)
            strong = any(term in haystack for term in terms if len(term) >= 3 or re.search(r"[a-zA-Z+#]", term))
            if score <= 0 or not strong:
                continue
            ranked.append((score, resource))
        ranked.sort(key=lambda item: (item[0], int(item[1].content.get("play") or 0)), reverse=True)
        return [resource for _, resource in ranked[:limit]]

    @staticmethod
    def expanded_video_queries(topic: str) -> list[str]:
        cleaned = topic.strip()
        expanded = [
            cleaned,
            f"{cleaned} 入门 教程",
            f"{cleaned} 完整课程",
            f"{cleaned} 实战",
        ]
        seen: set[str] = set()
        return [query for query in expanded if query and not (query in seen or seen.add(query))]

    async def retrieve_screened_videos(self, topic: str, context: TutorTurnContext, *, limit: int = 6) -> dict[str, Any]:
        local_videos = self.store.search_video_resources(topic, limit=limit * 2)
        all_candidates: list[LearningResource] = []
        live_errors: list[str] = []
        queries_used: list[str] = []
        source = "local_fallback"

        for query in self.expanded_video_queries(topic):
            queries_used.append(query)
            try:
                live_videos = await search_bilibili_videos(
                    query,
                    limit=limit,
                    reason=f"B站「{topic}」筛选推荐",
                )
                if live_videos:
                    source = "mixed" if local_videos else "bilibili_live"
                    all_candidates = self.merge_video_resources(all_candidates, live_videos, limit=limit * 3)
                    for resource in live_videos:
                        try:
                            self.store.save_resource(
                                resource,
                                student_id=context.student_id,
                                course_id=context.course_id,
                                created_by_skill="bilibili_video_retriever",
                            )
                        except Exception:
                            pass
            except BilibiliSearchError as exc:
                live_errors.append(str(exc)[:180])
            if len(self.filter_video_resources(topic, all_candidates, limit=limit)) >= min(3, limit):
                break

        if local_videos:
            all_candidates = self.merge_video_resources(all_candidates, local_videos, limit=limit * 3)

        videos = self.filter_video_resources(topic, all_candidates, limit=limit)
        if videos and source == "local_fallback" and any(resource.resource_id.startswith("res-bili-") for resource in videos):
            source = "bilibili_live"
        return {
            "videos": videos,
            "source": source if videos else "none",
            "queries_used": queries_used or [topic],
            "live_errors": live_errors,
        }

    @staticmethod
    def video_url(resource: LearningResource) -> str:
        content = resource.content or {}
        url = content.get("url")
        if isinstance(url, str) and url.startswith("http"):
            return url
        bvid = extract_bvid(resource)
        return f"https://www.bilibili.com/video/{bvid}" if bvid else ""

    def video_recommendation_text(self, topic: str, resources: list[LearningResource], source: str) -> str:
        if not resources:
            return (
                f"我按「{topic}」检索并筛了一轮，但这次没有找到标题/简介明显匹配的 B站教学视频。\n\n"
                "我没有把弱相关视频放到画布里。你可以把范围说得更具体一点，比如“Python 面向对象”“Python 爬虫入门”或“Python 数据分析实战”，我再重新搜。"
            )
        source_label = "实时搜索" if source in {"bilibili_live", "mixed"} else "本地资源库"
        lines = [
            f"我先按「{topic}」做了{source_label}，并用标题、简介和标签做了一轮相关性筛选。下面这些是可以直接打开的视频：",
            "",
        ]
        for index, resource in enumerate(resources[:6], 1):
            content = resource.content or {}
            author = str(content.get("author") or "").strip()
            play = content.get("play")
            play_text = f" · 播放 {play}" if play not in (None, "") else ""
            url = self.video_url(resource)
            meta = f"（{author}{play_text}）" if author or play_text else ""
            if url:
                lines.append(f"{index}. [{resource.title}]({url}){meta}")
            else:
                lines.append(f"{index}. {resource.title}{meta}")
            description = str(content.get("description") or resource.personalized_reason or "").strip()
            if description:
                lines.append(f"   推荐理由：{description[:90]}")
        lines.extend(["", "我也把同一批视频放进左侧播放器，方便你切换预览。"])
        return "\n".join(lines)

    async def emit_video_artifacts(self, step_outputs: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        retriever = step_outputs.get("video_retriever", {})
        canvas = step_outputs.get("video_canvas", {})
        if isinstance(retriever, dict):
            for item in retriever.get("resources", []):
                if isinstance(item, dict):
                    resource = LearningResource.model_validate(item)
                    message_id = str(canvas.get("message_id") or "")
                    yield event_dict(ResourceCreateEvent(resource=resource, message_id=message_id or None))
        if isinstance(canvas, dict) and isinstance(canvas.get("app"), dict):
            app = CanvasApp.model_validate(canvas["app"])
            link = ChatAppLink.model_validate(canvas["link"]) if isinstance(canvas.get("link"), dict) else None
            yield event_dict(AppCreateEvent(app=app, link=link))
            if link:
                yield event_dict(AppLinkCreateEvent(link=link))

    def complete_hermes_contract(self, plan: AgentPlan, hermes_result: HermesTaskResult, source_refs: list[dict[str, Any]]) -> HermesTaskResult:
        if not plan.payload.get("requires_canvas"):
            return hermes_result
        topic = str(plan.payload.get("topic") or plan.payload.get("original_message") or "当前主题")[:120]
        capability = str(plan.payload.get("capability") or "")
        source_material = str(plan.payload.get("source_material") or plan.payload.get("original_message") or "")
        resources = list(hermes_result.resources)
        apps = list(hermes_result.apps)
        trace_additions: list[str] = []
        if capability == "ppt":
            normalized_apps: list[dict[str, Any]] = []
            for app in apps:
                if not isinstance(app, dict):
                    continue
                app_type = str(app.get("app_type") or app.get("type") or "")
                payload = app.get("payload") if isinstance(app.get("payload"), dict) else {}
                html = str(payload.get("html") or "")
                if app_type in {"ppt.preview", "presentation", "slides"} or (app_type == "custom.html" and not self.is_navigable_ppt_html(html)):
                    normalized = self.fallback_app_for_type("custom.html", topic, capability=capability, source_material=source_material)
                    normalized["title"] = str(app.get("title") or normalized["title"])
                    normalized_apps.append(normalized)
                    trace_additions.append(f"normalized_ppt_app:{app_type or 'missing'}->custom.html")
                    continue
                normalized_apps.append(app)
            apps = normalized_apps
        actual_resource_types = {str(item.get("type")) for item in resources if isinstance(item, dict) and item.get("type")}
        actual_app_types = {str(item.get("app_type") or item.get("type")) for item in apps if isinstance(item, dict) and (item.get("app_type") or item.get("type"))}
        added: list[str] = []
        for resource_type in plan.payload.get("expected_resource_types", []):
            if resource_type and resource_type not in actual_resource_types:
                resources.append(self.fallback_resource_for_type(str(resource_type), topic, source_refs))
                added.append(f"{resource_type} resource")
        for app_type in plan.payload.get("expected_app_types", []):
            if app_type and app_type not in actual_app_types:
                apps.append(self.fallback_app_for_type(str(app_type), topic, capability=capability, source_material=source_material))
                added.append(f"{app_type} app")
        if not added:
            if not trace_additions:
                return hermes_result
            return HermesTaskResult(
                summary=hermes_result.summary or f"已根据 Capability Contract 标准化 {topic} PPT 产物。",
                trace=[*hermes_result.trace, *trace_additions],
                resources=resources,
                apps=apps,
                raw_text=hermes_result.raw_text,
            )
        return HermesTaskResult(
            summary=hermes_result.summary or f"已根据 Capability Contract 补齐 {topic} 产物。",
            trace=[*hermes_result.trace, *trace_additions, f"contract_fallback:{','.join(added)}"],
            resources=resources,
            apps=apps,
            raw_text=hermes_result.raw_text,
        )

    @staticmethod
    def is_navigable_ppt_html(html: str | None) -> bool:
        if not html:
            return False
        source = str(html)
        slide_count = len(re.findall(r"<section\b[^>]*(?:class=['\"][^'\"]*\bslide\b|data-layout=|data-slide=)", source, flags=re.IGNORECASE))
        if slide_count < 2:
            slide_count = len(re.findall(r"class=['\"][^'\"]*\bslide\b", source, flags=re.IGNORECASE))
        has_deck_marker = bool(re.search(r"guizang|web\s*ppt|horizontal[- ]swipe|slide deck|class=['\"][^'\"]*\bdeck\b|data-deck", source, flags=re.IGNORECASE))
        has_navigation = bool(re.search(r"ArrowRight|ArrowLeft|PageDown|PageUp|scrollIntoView|scrollTo|touch(start|end)|wheel", source, flags=re.IGNORECASE))
        return slide_count >= 2 and (has_deck_marker or has_navigation)

    def collect_created_apps(self, materialized: MaterializedBundle | None, step_outputs: dict[str, Any]) -> list[dict[str, Any]]:
        apps: list[dict[str, Any]] = []
        if materialized:
            apps.extend(app.model_dump() for app in materialized.apps)
        for output in step_outputs.values():
            if not isinstance(output, dict):
                continue
            app = output.get("app")
            if isinstance(app, dict):
                apps.append(app)
            app_items = output.get("apps")
            if isinstance(app_items, list):
                apps.extend(item for item in app_items if isinstance(item, dict))
        return apps

    def collect_created_resources(self, materialized: MaterializedBundle | None, step_outputs: dict[str, Any]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        if materialized:
            resources.extend(resource.model_dump() for resource in materialized.resources)
        for output in step_outputs.values():
            if not isinstance(output, dict):
                continue
            resource = output.get("resource")
            if isinstance(resource, dict):
                resources.append(resource)
            resource_items = output.get("resources")
            if isinstance(resource_items, list):
                resources.extend(item for item in resource_items if isinstance(item, dict))
        return resources

    def verify_artifacts(self, plan: AgentPlan, materialized: MaterializedBundle | None, step_outputs: dict[str, Any]) -> dict[str, Any]:
        if not plan.payload.get("requires_canvas"):
            return {
                "passed": True,
                "created_app_count": 0,
                "created_resource_count": 0,
                "missing_artifacts": [],
                "reason": "answer_only_or_no_canvas_required",
            }
        apps = self.collect_created_apps(materialized, step_outputs)
        resources = self.collect_created_resources(materialized, step_outputs)
        expected_apps = [str(item) for item in plan.payload.get("expected_app_types", []) if item]
        expected_resources = [str(item) for item in plan.payload.get("expected_resource_types", []) if item]
        actual_app_types = [str(item.get("app_type") or item.get("type")) for item in apps if item.get("app_type") or item.get("type")]
        actual_resource_types = [str(item.get("type")) for item in resources if item.get("type")]
        missing = [f"{app_type} App" for app_type in expected_apps if app_type not in actual_app_types]
        missing.extend(f"{resource_type} Resource" for resource_type in expected_resources if resource_type not in actual_resource_types)
        image_ready = True
        image_error = None
        if "image.explanation" in expected_apps:
            image_apps = [item for item in apps if item.get("app_type") == "image.explanation"]
            image_ready = any(isinstance(item.get("payload"), dict) and item["payload"].get("image_url") for item in image_apps)
            image_error = next(
                (
                    item.get("payload", {}).get("image_error")
                    for item in image_apps
                    if isinstance(item.get("payload"), dict) and item.get("payload", {}).get("image_error")
                ),
                None,
            )
            if not image_ready:
                missing.append("image.explanation.payload.image_url")
        return {
            "passed": not missing,
            "capability": plan.payload.get("capability"),
            "created_app_count": len(apps),
            "created_resource_count": len(resources),
            "expected_app_types": expected_apps,
            "actual_app_types": actual_app_types,
            "expected_resource_types": expected_resources,
            "actual_resource_types": actual_resource_types,
            "missing_artifacts": missing,
            "image_ready": image_ready,
            "image_error": image_error,
        }

    def artifact_failure_text(self, verification: dict[str, Any]) -> str:
        missing = "、".join(verification.get("missing_artifacts") or ["必需画布产物"])
        if verification.get("image_error"):
            return f"这次没有完成画布生成，因为 Gemini 图片生成失败：{verification['image_error']}。我不会假装已经把图片放到左侧画布。"
        return f"这次没有完成画布生成，因为产物校验没有通过，缺少：{missing}。我不会假装已经生成；需要重新触发 Hermes 或把任务拆小后再生成。"

    def local_artifact_success_text(
        self,
        plan: AgentPlan,
        context: TutorTurnContext,
        materialized: MaterializedBundle | None,
        step_outputs: dict[str, Any],
        model_message: str,
    ) -> str | None:
        artifact_verifier = step_outputs.get("artifact_verifier")
        if not isinstance(artifact_verifier, dict) or not artifact_verifier.get("passed") or not artifact_verifier.get("created_app_count"):
            return None
        apps = self.collect_created_apps(materialized, step_outputs)
        resources = self.collect_created_resources(materialized, step_outputs)
        app_titles = [str(item.get("title") or "学习 App") for item in apps[:3] if isinstance(item, dict)]
        resource_titles = [str(item.get("title") or "学习资源") for item in resources[:3] if isinstance(item, dict)]
        topic = str(plan.payload.get("topic") or extract_learning_topic(context.message) or context.message).strip()
        app_text = "、".join(app_titles) if app_titles else "左侧画布 App"
        resource_text = "、".join(resource_titles) if resource_titles else "配套学习资源"
        return (
            f"已为你生成「{topic}」相关的画布内容，并通过产物校验。\n\n"
            f"左侧可以打开：{app_text}。\n\n"
            f"同时已准备：{resource_text}。\n\n"
            f"{model_message}，所以这次先用画布摘要回复你。你可以直接点击上方的 AppLink 打开互动演示，边看边调整或继续追问具体算法。"
        )

    def needs_quality_rewrite(self, text: str, plan: AgentPlan, context: TutorTurnContext, step_outputs: dict[str, Any]) -> bool:
        clean = strip_generation_markers(text)
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", clean))
        wants_explanation = any(term in context.message for term in ["详细", "讲解", "介绍", "解释", "说明", "对比", "列出", "为什么", "怎么"])
        wants_canvas = bool(plan.payload.get("requires_canvas"))
        if chinese_chars < (420 if wants_explanation or wants_canvas else 220):
            return True
        if len([line for line in clean.splitlines() if line.strip()]) < 5 and (wants_explanation or wants_canvas):
            return True
        weak_markers = ["虽然目前这里没有", "我无法直接", "打开左侧", "我已经放到", "生成到左侧画布", "准备了核心内容"]
        if any(marker in clean for marker in weak_markers) and chinese_chars < 900:
            return True
        artifact_verifier = step_outputs.get("artifact_verifier")
        if isinstance(artifact_verifier, dict) and not artifact_verifier.get("passed") and "失败" not in clean and "没有完成" not in clean:
            return True
        return False

    def build_quality_rewrite_messages(
        self,
        plan: AgentPlan,
        context: TutorTurnContext,
        rag_context: dict[str, Any],
        step_outputs: dict[str, Any],
        weak_answer: str,
    ) -> list[ChatMessage]:
        artifact_verifier = step_outputs.get("artifact_verifier", {})
        source_material = str(plan.payload.get("source_material") or context.last_assistant_answer or context.message)
        source_refs = rag_context.get("source_refs", [])
        tool_summary = json.dumps(self.compact_step_outputs(step_outputs), ensure_ascii=False)[:1800]
        system = (
            "你是 LearnForge 的高质量中文学习导师。现在需要重写一版更好的最终回复。"
            "核心目标是让学生真正学懂问题本身，画布/App 只是辅助，不能喧宾夺主。"
            "RAG 证据不是必用材料：只有 has_relevant_context=true 且内容明显贴合用户问题时才使用。"
            "如果 RAG 为空或只是弱相关，必须正常回答问题，不要把无关语料拼进正文。"
            "必须输出完整中文正文，避免空泛比喻、半句话、只说已生成、只引导去左侧画布。"
            "如果是算法/数学/物理/计算机主题，优先包含：核心概念、直觉解释、步骤或公式、复杂度/适用场景、例子、易错点、学习建议。"
            "如果是文科或英语主题，优先包含：背景、结构化要点、证据/原文依据、对比、可复习总结。"
            "只有 artifact_verifier.passed=true 且 created_app_count>0 时，才可以说画布产物已生成；否则只能在末尾简短说明画布失败，不能假装成功。"
        )
        user = (
            f"用户问题: {context.message}\n"
            f"任务类型: {plan.task_type}\n"
            f"Capability: {plan.payload.get('capability')}\n"
            f"主题: {plan.payload.get('topic')}\n"
            f"源材料/上一轮内容: {source_material[:3000]}\n"
            f"RAG是否相关: {json.dumps({'has_relevant_context': rag_context.get('has_relevant_context'), 'policy': rag_context.get('retrieval_policy'), 'note': rag_context.get('retrieval_note')}, ensure_ascii=False)}\n"
            f"RAG上下文: {str(rag_context.get('context', ''))[:1800]}\n"
            f"source_refs: {json.dumps(source_refs, ensure_ascii=False)}\n"
            f"artifact_verifier: {json.dumps(artifact_verifier, ensure_ascii=False)}\n"
            f"工具输出摘要: {tool_summary}\n"
            f"上一版弱回答: {strip_generation_markers(weak_answer)[:1200]}\n\n"
            "请直接给出重写后的最终导师回复。要求：\n"
            "1. 先完整回答学习问题，不要先谈画布。\n"
            "2. 结构清晰，可以使用小标题、表格或编号。\n"
            "3. 如果画布失败，在最后单独用一小段说明失败原因和下一步。\n"
            "4. 不要输出任何系统说明或 JSON。"
        )
        return [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user, images=context.image_data)]

    def generation_suggestion_marker(self, plan: AgentPlan, context: TutorTurnContext) -> str:
        if plan.payload.get("capability") != "answer_only":
            return ""
        topic = extract_learning_topic(context.message) or extract_learning_topic(context.last_assistant_answer or "") or str(plan.payload.get("topic") or "").strip()
        if is_generic_topic(topic):
            return ""
        lower = f"{topic} {context.message}".lower()
        if any(term in lower for term in ["定理", "公式", "函数", "算法", "物理", "力学", "梯度", "排序", "模型"]):
            label = f"生成「{topic}」互动演示"
            return f"\n\n[[generate:interactive_demo:{topic}]]{label}[[/generate]]"
        if any(term in lower for term in ["结构", "流程", "概念", "知识点", "对比"]):
            label = f"生成「{topic}」信息图"
            return f"\n\n[[generate:custom_infographic:{topic}]]{label}[[/generate]]"
        label = f"生成「{topic}」教学图"
        return f"\n\n[[generate:image_explanation:{topic}]]{label}[[/generate]]"

    def compact_step_outputs(self, step_outputs: dict[str, Any]) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for step, output in step_outputs.items():
            item: dict[str, Any] = {"step": step}
            if isinstance(output, dict):
                if "summary" in output:
                    item["summary"] = str(output["summary"])[:240]
                if "path" in output and isinstance(output["path"], dict):
                    item["path_title"] = output["path"].get("title")
                if "resources" in output and isinstance(output["resources"], list):
                    item["resources"] = [
                        {"title": resource.get("title"), "type": resource.get("type")}
                        for resource in output["resources"][:6]
                        if isinstance(resource, dict)
                    ]
                if "app" in output and isinstance(output["app"], dict):
                    item["app"] = {"app_id": output["app"].get("app_id"), "title": output["app"].get("title"), "type": output["app"].get("app_type")}
                if "link" in output and isinstance(output["link"], dict):
                    item["link"] = {"link_id": output["link"].get("link_id"), "label": output["link"].get("label")}
                if step == "artifact_verifier":
                    item["artifact_verifier"] = {
                        "passed": output.get("passed"),
                        "created_app_count": output.get("created_app_count"),
                        "created_resource_count": output.get("created_resource_count"),
                        "missing_artifacts": output.get("missing_artifacts", []),
                    }
            compact.append(item)
        return compact

    def build_tutor_messages(self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any], step_outputs: dict[str, Any]) -> list[ChatMessage]:
        profile = self.store.get_profile(context.student_id, course_id=context.course_id)
        source_refs = rag_context.get("source_refs", [])
        tool_summary = json.dumps(self.compact_step_outputs(step_outputs), ensure_ascii=False)[:1800]
        recent_messages = json.dumps(context.recent_messages[-6:], ensure_ascii=False)[:1200]
        recent_apps = json.dumps(
            [{"app_id": item.get("app_id"), "title": item.get("title"), "app_type": item.get("app_type")} for item in context.recent_apps[-6:]],
            ensure_ascii=False,
        )[:900]
        recent_resources = json.dumps(
            [{"resource_id": item.get("resource_id"), "title": item.get("title"), "type": item.get("type")} for item in context.recent_resources[-6:]],
            ensure_ascii=False,
        )[:900]
        artifact_verifier = step_outputs.get("artifact_verifier", {})
        system = (
            "你是 LearnForge V2 的真实 AI 学习导师，必须基于用户消息、RAG 证据、学习画像和工具执行结果回答。"
            "最主要职责是正常、完整地回答学生的学习问题；画布、App、资源卡只是辅助功能，不能替代正文讲解。"
            "RAG 是可选证据，不是强制素材。只有 has_relevant_context=true 且证据和问题直接相关时才引用或改写 RAG。"
            "如果 RAG 为空、低相关或只是在课程库里碰巧相似，必须忽略 RAG 并直接回答学生问题；禁止硬凑无关 RAG 内容。"
            "回答要具体、可执行、适合右侧 Tutor Chat，必要时引用左侧 App/资源。"
            "如果用户问的是概念、算法、题目或知识讲解，必须先给出完整讲解、关键步骤、例子和学习建议，再补充画布状态。"
            "禁止只输出“已生成到画布”“打开左侧 App”或一段很短的引导语来代替学习回答。"
            "硬性规则：只有 artifact_verifier.passed=true 且 created_app_count>0 时，才允许说“已生成”“已放到左侧画布”或类似表述。"
            "如果任务是 answer_only，或者 artifact_verifier 不存在/未通过，禁止声称创建了 App、图片、信息图、PPT、题库或任何画布产物。"
            "如果工具结果不足或画布失败，也必须继续回答用户的学习问题，然后用单独一句说明画布失败原因和下一步，绝不编造外部动作。"
        )
        user = (
            f"学生ID: {context.student_id}\n"
            f"课程ID: {context.course_id}\n"
            f"用户消息: {context.message}\n"
            f"任务类型: {plan.task_type}\n"
            f"Capability: {plan.payload.get('capability')}\n"
            f"短主题: {plan.payload.get('topic')}\n"
            f"源材料摘要: {str(plan.payload.get('source_material') or '')[:1200]}\n"
            f"计划步骤: {', '.join(plan.steps)}\n"
            f"学习画像: {json.dumps(profile, ensure_ascii=False)}\n"
            f"最近对话: {recent_messages}\n"
            f"上一轮导师回答: {context.last_assistant_answer or ''}\n"
            f"最近画布App: {recent_apps}\n"
            f"最近资源: {recent_resources}\n"
            f"RAG检索策略: {json.dumps({'has_relevant_context': rag_context.get('has_relevant_context'), 'policy': rag_context.get('retrieval_policy'), 'note': rag_context.get('retrieval_note')}, ensure_ascii=False)}\n"
            f"RAG上下文: {rag_context.get('context', '')}\n"
            f"source_refs: {json.dumps(source_refs, ensure_ascii=False)}\n"
            f"artifact_verifier: {json.dumps(artifact_verifier, ensure_ascii=False)}\n"
            f"工具输出摘要: {tool_summary}\n\n"
            "请生成一段中文导师回复：先完整回应用户真实学习问题；如果产物校验通过，再说明左侧画布或资源如何使用；如果没有通过，也不要只说失败，要继续给出正文讲解，并在末尾简短说明画布失败原因和下一步。"
        )
        return [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user, images=context.image_data)]

    async def complete_tutor_response_with_provider(
        self,
        provider: str,
        plan: AgentPlan,
        context: TutorTurnContext,
        rag_context: dict[str, Any],
        step_outputs: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        client = self.model_gateway.client(provider)
        response = await client.complete(self.build_tutor_messages(plan, context, rag_context, step_outputs), stream=False)
        text = client.extract_assistant_text(response).strip()
        if not text:
            raise ModelGatewayError(f"{provider} returned an empty assistant message.")
        quality_rewrite_used = False
        quality_rewrite_error = ""
        if self.needs_quality_rewrite(text, plan, context, step_outputs):
            try:
                rewrite_response = await client.complete(self.build_quality_rewrite_messages(plan, context, rag_context, step_outputs, text), stream=False)
                rewritten = client.extract_assistant_text(rewrite_response).strip()
                if rewritten and len(strip_generation_markers(rewritten)) > len(strip_generation_markers(text)):
                    response = rewrite_response
                    text = rewritten
                    quality_rewrite_used = True
            except (ProviderBlocked, ModelGatewayError) as exc:
                quality_rewrite_error = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        response_payload = response if isinstance(response, dict) else {}
        usage = response_payload.get("usage")
        model = response_payload.get("model") if isinstance(response_payload.get("model"), str) else client.model_name()
        trace = {
            "provider": provider,
            "model": model,
            "adapter": getattr(client, "adapter", "unknown"),
            "usage": usage if isinstance(usage, dict) else {},
            "response_id": response_payload.get("id"),
            "fallback_used": bool(response_payload.get("fallback_used")),
            "quality_rewrite_used": quality_rewrite_used,
        }
        if quality_rewrite_error:
            trace["quality_rewrite_error"] = quality_rewrite_error[:500]
        return text, trace

    async def generate_model_tutor_response(self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any], step_outputs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        requested_provider = self.model_gateway.normalize_provider(context.model_provider)
        fallback_order = getattr(self.model_gateway, "fallback_order", None)
        provider_order = fallback_order(context.model_provider) if callable(fallback_order) else [requested_provider]
        attempt_errors: list[dict[str, str]] = []
        for index, provider in enumerate(provider_order):
            try:
                text, trace = await self.complete_tutor_response_with_provider(provider, plan, context, rag_context, step_outputs)
                trace["requested_provider"] = requested_provider
                trace["provider_fallback_used"] = index > 0 or provider != requested_provider
                if attempt_errors:
                    trace["provider_attempts"] = [*attempt_errors, {"provider": provider, "status": "completed", "reason": ""}]
                    trace["fallback_from"] = requested_provider
                    trace["fallback_reason"] = attempt_errors[0]["reason"][:500]
                return text, trace
            except ProviderBlocked as exc:
                attempt_errors.append({"provider": provider, "status": exc.code, "reason": exc.reason})
            except ModelGatewayError as exc:
                reason = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
                attempt_errors.append({"provider": provider, "status": "failed", "reason": reason})
        if attempt_errors and all(item["status"].startswith("blocked") for item in attempt_errors):
            reason = "；".join(f"{self.model_provider_label(item['provider'])}: {item['reason']}" for item in attempt_errors)
            raise ProviderBlocked("blocked_all_providers", reason)
        reason = "；".join(f"{self.model_provider_label(item['provider'])}: {item['reason']}" for item in attempt_errors)
        raise ModelGatewayError(f"所有可用回答模型都调用失败：{reason}")

    async def execute_plan(self, plan: AgentPlan, context: TutorTurnContext) -> AsyncIterator[dict[str, Any]]:
        run_id = self.store.create_run(context.student_id, plan.task_type, {"message": context.message, "plan": plan.model_dump()})
        self.save_chat_message(context, "user", context.message, run_id=run_id, metadata={"plan": plan.model_dump()})
        yield event_dict(RunStarted(run_id=run_id, task_type=plan.task_type))
        self.hermes.prepare()
        rag_context = CourseRetriever().context_with_refs(plan.payload.get("topic", "梯度下降"), course_id=context.course_id)
        source_refs = self.source_refs_for_plan(plan, context, rag_context["source_refs"])
        rag_context = {**rag_context, "source_refs": source_refs}
        message_id = new_id("msg")
        step_order = 1
        step_outputs: dict[str, Any] = {}
        hermes_result: HermesTaskResult | None = None
        materialized: MaterializedBundle | None = None
        hermes_fallback_mode = False

        for step in plan.steps:
            running_detail = "加载 LearnForge profile、Skills、Toolsets/MCP" if step == "hermes_runtime" else "执行中"
            yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="running", detail=running_detail))
            step_status = "completed"
            completed_detail = "Hermes Agent 原生 Skills/Toolsets 编排完成" if step == "hermes_runtime" else "已完成"
            if step == "analysis_acknowledge":
                ack_text = plan.payload.get("background_label", "正在深度分析你的题目，这可能需要几分钟…")
                yield event_dict({"type": "assistant.delta", "message_id": message_id, "text": f"✅ {ack_text}\n\n> 💡 你可以在后台运行期间继续提问，分析完成后会自动推送到画布。"})
                yield event_dict({"type": "assistant.done", "message_id": message_id})
                yield event_dict({"type": "background.task_started", "run_id": run_id, "label": ack_text, "task_type": plan.task_type})
                output = {"acknowledged": True, "label": ack_text}
                self.save_chat_message(context, "assistant", f"✅ {ack_text}", run_id=run_id)
                step_status = "completed"
                completed_detail = "任务已确认，分析在后台继续"
            elif step == "html_report_builder":
                if hermes_result and hermes_result.raw_text:
                    raw = hermes_result.raw_text or ""
                    # 提取 HTML 部分：跳过可能的 Markdown 摘要前缀（## 📝 分析完成...）
                    html_match = re.search(r"<!DOCTYPE\s+html", raw, re.IGNORECASE)
                    if html_match:
                        html_content = raw[html_match.start():]
                    else:
                        # 尝试找 <html> 或 <body> 作为 HTML 起点
                        html_match = re.search(r"<\s*html", raw, re.IGNORECASE)
                        html_content = raw[html_match.start():] if html_match else raw
                    if html_content:
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="html_report_builder", status="running", detail="构建交互式 HTML 分析报告"))
                        output = {"html_content": html_content}
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="html_report_builder", status="completed", detail="HTML 报告已生成"))
                        yield event_dict({"type": "background.task_progress", "run_id": run_id, "progress": 0.95, "detail": "HTML报告已生成，正在推送到画布"})
                    else:
                        output = {"warning": "Hermes 未返回 HTML 内容"}
                        completed_detail = "警告：未生成 HTML 报告"
                else:
                    output = {"error": "Hermes 未返回有效内容"}
                    step_status = "failed"
                step_outputs["html_report_builder"] = output
            elif step == "intent_detect":
                output = {
                    "summary": f"识别为 {plan.payload.get('capability', plan.task_type)}",
                    "capability": plan.payload.get("capability"),
                    "requires_canvas": plan.payload.get("requires_canvas", False),
                    "expected_app_types": plan.payload.get("expected_app_types", []),
                    "expected_resource_types": plan.payload.get("expected_resource_types", []),
                    "context_source": plan.payload.get("context_source"),
                }
                yield event_dict(
                    RunStepEvent(
                        run_id=run_id,
                        step_name="capability_contract",
                        status="completed",
                        detail=(
                            f"{plan.payload.get('capability')} · apps={','.join(plan.payload.get('expected_app_types', []) or ['none'])} · "
                            f"resources={','.join(plan.payload.get('expected_resource_types', []) or ['none'])}"
                        ),
                    )
                )
                # ---- Emit context.update for dynamic TopBar ----
                detected_topic = str(plan.payload.get("topic") or context.message)[:120].strip()
                detected_capability = str(plan.payload.get("capability") or plan.task_type)
                course_label = self._course_label(context.course_id)
                learning_objective = self._infer_objective(detected_topic, detected_capability, context)
                yield event_dict(ContextUpdateEvent(
                    topic=detected_topic,
                    capability=detected_capability,
                    course_label=course_label,
                    learning_objective=learning_objective,
                ))
                self.store.save_learning_focus(
                    context.student_id, context.course_id,
                    topic=detected_topic,
                    objective=learning_objective,
                    course_label=course_label,
                )
                if plan.payload.get("capability") == "custom_infographic":
                    mode = str(plan.payload.get("infographic_render_mode") or "image")
                    yield event_dict(
                        RunStepEvent(
                            run_id=run_id,
                            step_name="infographic_router",
                            status="completed",
                            detail="Nano Banana 图片版" if mode == "image" else "HTML 渲染版",
                        )
                    )
                for skill_name in plan.payload.get("hermes_skills", [])[:8]:
                    yield event_dict(RunStepEvent(run_id=run_id, step_name="skill_call", status="completed", detail=str(skill_name)))
            elif step == "hermes_runtime":
                if plan.task_type == "detailed_analysis":
                    # detailed_analysis: 直接输出 HTML，不走 JSON 资源包路径
                    try:
                        raw_html = await self.hermes_executor.run_detailed_analysis(plan, context, rag_context)
                        hermes_result = HermesTaskResult(
                            summary="详细分析完成",
                            trace=["detailed_analysis_html_generated"],
                            resources=[],
                            apps=[],
                            raw_text=raw_html,
                        )
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="hermes_runtime", status="completed", detail="HTML 分析报告已生成"))
                        completed_detail = "HTML 分析报告已生成"
                    except (ProviderBlocked, ModelGatewayError) as exc:
                        code = exc.code if isinstance(exc, ProviderBlocked) else "hermes_execution_failed"
                        reason = exc.reason if isinstance(exc, ProviderBlocked) else str(exc)
                        output = {"status": code, "reason": reason}
                        self.record_trace(run_id, step, step_order, output, status="failed")
                        self.store.finish_run(run_id, output, "failed")
                        yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="failed", detail=reason))
                        yield event_dict(AssistantDelta(message_id=message_id, text=f"详细分析执行失败：{reason}"))
                        yield event_dict(RunDone(run_id=run_id, status="failed"))
                        yield event_dict(AssistantDone(message_id=message_id))
                        return
                else:
                    if plan.payload.get("capability") == "ppt":
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="ppt_style", status="running", detail="选择网页 PPT 视觉风格"))
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="ppt_style", status="completed", detail="已确定 Guizang 网页 PPT 风格"))
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="ppt_outline", status="running", detail="规划页面结构与讲解顺序"))
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="ppt_outline", status="completed", detail="已规划封面、主体与总结页"))
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="ppt_slide_html", status="running", detail="生成可翻页 HTML Slide Deck"))
                    try:
                        hermes_result = await self.hermes_executor.run_resource_bundle(plan, context, rag_context)
                    except (ProviderBlocked, ModelGatewayError) as exc:
                        code = exc.code if isinstance(exc, ProviderBlocked) else "hermes_execution_failed"
                        reason = exc.reason if isinstance(exc, ProviderBlocked) else str(exc)
                        if plan.payload.get("requires_canvas"):
                            hermes_fallback_mode = True
                            hermes_result = HermesTaskResult(
                                summary=f"Hermes 执行失败，启用 Capability Contract 兜底：{reason}",
                                trace=[f"hermes_failed:{code}", "capability_contract_fallback_enabled"],
                                resources=[],
                                apps=[],
                            )
                            step_status = "failed"
                            completed_detail = f"Hermes 执行失败，转入合同兜底：{reason[:140]}"
                        else:
                            output = {"status": code, "reason": reason}
                            self.record_trace(run_id, step, step_order, output, status="failed")
                            self.store.finish_run(run_id, output, "failed")
                            yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="failed", detail=reason))
                            yield event_dict(AssistantDelta(message_id=message_id, text=f"Hermes 执行失败：{reason}"))
                            yield event_dict(RunDone(run_id=run_id, status="failed"))
                            yield event_dict(AssistantDone(message_id=message_id))
                            return
                    if hermes_result is None:
                        output = {"status": code, "reason": reason}
                        self.record_trace(run_id, step, step_order, output, status="failed")
                        self.store.finish_run(run_id, output, "failed")
                        yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="failed", detail=reason))
                        yield event_dict(AssistantDelta(message_id=message_id, text=f"Hermes 执行失败：{reason}"))
                        yield event_dict(RunDone(run_id=run_id, status="failed"))
                        yield event_dict(AssistantDone(message_id=message_id))
                        return
                # detailed_analysis 跳过 artifact 检查（非 JSON 产物）
                if plan.task_type == "detailed_analysis":
                    missing = []
                else:
                    missing = [] if hermes_fallback_mode else self.missing_required_artifacts(plan, hermes_result)
                if missing:
                    yield event_dict(RunStepEvent(run_id=run_id, step_name="protocol_repair", status="running", detail=f"补齐缺失产物：{'、'.join(missing)}"))
                    repaired_result = await self.repair_hermes_result(plan, context, rag_context, missing)
                    merged_result = self.merge_hermes_results(hermes_result, repaired_result) if repaired_result else None
                    repair_missing = self.missing_required_artifacts(plan, merged_result) if merged_result else missing
                    repair_output = {
                        "summary": "Hermes 协议修复完成" if repaired_result and not repair_missing else "Hermes 协议修复仍缺少产物",
                        "missing_before": missing,
                        "missing_after": repair_missing,
                        "repaired": bool(repaired_result and not repair_missing),
                    }
                    if merged_result:
                        hermes_result = merged_result
                    self.record_trace(run_id, "protocol_repair", step_order, repair_output, status="completed" if not repair_missing else "failed")
                    step_outputs["protocol_repair"] = repair_output
                    yield event_dict(
                        RunStepEvent(
                            run_id=run_id,
                            step_name="protocol_repair",
                            status="completed" if not repair_missing else "failed",
                            detail=repair_output["summary"],
                        )
                    )
                    step_order += 1
                # detailed_analysis 不需要合同补齐（非 JSON 产物）
                if plan.task_type != "detailed_analysis":
                    hermes_result = self.complete_hermes_contract(plan, hermes_result, source_refs)
                if plan.payload.get("capability") == "ppt":
                    yield event_dict(RunStepEvent(run_id=run_id, step_name="ppt_slide_html", status="completed", detail="网页 PPT HTML 已生成"))
                    has_navigable_deck = any(
                        isinstance(item, dict)
                        and str(item.get("app_type") or item.get("type") or "") == "custom.html"
                        and self.is_navigable_ppt_html((item.get("payload") or {}).get("html") if isinstance(item.get("payload"), dict) else "")
                        for item in hermes_result.apps
                    )
                    yield event_dict(
                        RunStepEvent(
                            run_id=run_id,
                            step_name="ppt_deck_verify",
                            status="completed" if has_navigable_deck else "failed",
                            detail="已确认 PPT 可翻页" if has_navigable_deck else "PPT 翻页结构不足，已使用兜底 deck",
                        )
                    )
                for trace_item in hermes_result.trace[-10:]:
                    trace_text = str(trace_item)
                    step_name = "contract_fallback" if trace_text.startswith("contract_fallback") or trace_text.startswith("capability_contract_fallback") else "hermes_native_trace"
                    yield event_dict(RunStepEvent(run_id=run_id, step_name=step_name, status="completed", detail=trace_text[:180]))
                output = {
                    "summary": hermes_result.summary,
                    "resource_count": len(hermes_result.resources),
                    "app_count": len(hermes_result.apps),
                    "trace": hermes_result.trace,
                }
            elif step == "resource_bundle_skill":
                if not hermes_result:
                    output = {"summary": "Hermes 尚未返回资源包。", "resources": []}
                else:
                    output = {
                        "summary": hermes_result.summary,
                        "resources": [
                            {"title": item.get("title"), "type": item.get("type")}
                            for item in hermes_result.resources
                            if isinstance(item, dict)
                        ],
                    }
            elif step == "video_retriever":
                topic = str(plan.payload.get("topic") or "").strip() or clean_video_query(context.message, None)
                yield event_dict(RunStepEvent(run_id=run_id, step_name="video_context", status="completed", detail=f"锁定搜索主题：{topic}"))
                yield event_dict(RunStepEvent(run_id=run_id, step_name="bilibili_live_search", status="running", detail=f"实时搜索：{', '.join(self.expanded_video_queries(topic)[:2])}"))
                result = await self.retrieve_screened_videos(topic, context, limit=6)
                live_source = str(result.get("source") or "")
                live_status = "completed" if live_source in {"bilibili_live", "mixed"} else "failed"
                live_detail = "实时搜索返回并参与筛选" if live_status == "completed" else "实时搜索没有返回足够相关结果，使用本地资源兜底"
                if result.get("live_errors"):
                    live_detail = f"{live_detail}：{'; '.join(result.get('live_errors', [])[:2])}"
                yield event_dict(RunStepEvent(run_id=run_id, step_name="bilibili_live_search", status=live_status, detail=live_detail[:180]))
                videos = result["videos"]
                source = str(result["source"])
                yield event_dict(RunStepEvent(run_id=run_id, step_name="video_relevance_filter", status="completed" if videos else "failed", detail=f"按标题/简介/标签筛选，保留 {len(videos)} 个高相关视频"))
                if videos:
                    summary = f"已筛选出 {len(videos)} 个「{topic}」相关 B站视频，等待最终回答一起展示。"
                else:
                    summary = f"没有找到“{topic}”的高相关 B站视频。"
                output = {
                    "summary": summary,
                    "query": topic,
                    "source": source,
                    "queries_used": result.get("queries_used", [topic]),
                    "live_errors": result.get("live_errors", []),
                    "resources": [resource.model_dump() for resource in videos],
                }
                completed_detail = output["summary"]
                if not videos:
                    step_status = "failed"
            elif step == "video_canvas":
                raw_resources = step_outputs.get("video_retriever", {}).get("resources") if isinstance(step_outputs.get("video_retriever"), dict) else []
                video_resources = [
                    LearningResource.model_validate(item)
                    for item in raw_resources
                    if isinstance(item, dict)
                ]
                if not video_resources:
                    output = {"summary": "没有可写入画布的视频资源。", "resources": [], "apps": []}
                    step_status = "failed"
                    completed_detail = "没有可写入画布的视频资源"
                else:
                    topic = str(step_outputs.get("video_retriever", {}).get("query") or plan.payload.get("topic") or "B站视频推荐")
                    saved_app = self.video_recommendation_app(
                        topic=topic,
                        resources=video_resources,
                        student_id=context.student_id,
                        course_id=context.course_id,
                        conversation_id=context.conversation_id,
                        message_id=message_id,
                        run_id=run_id,
                    )
                    link = self.store.create_chat_link(message_id, saved_app.app_id, f"打开 {saved_app.title}", action="fullscreen", run_id=run_id)
                    output = {
                        "summary": f"已准备 {len(video_resources)} 个 B站视频和左侧播放器，等待最终回答一起展示。",
                        "app": saved_app.model_dump(),
                        "link": link.model_dump(),
                        "resources": [resource.model_dump() for resource in video_resources],
                        "message_id": message_id,
                    }
                    completed_detail = output["summary"]
            elif step == "canvas_materializer":
                if plan.task_type == "detailed_analysis":
                    html_content = step_outputs.get("html_report_builder", {}).get("html_content", "")
                    if html_content:
                        materialized = MaterializedBundle(
                            resources=[],
                            apps=[CanvasApp(
                                app_id=plan.payload.get("app_id", "app-detailed-analysis"),
                                app_type="custom.html",
                                title=plan.payload.get("topic", "题目分析报告"),
                                payload={"html": html_content, "title": plan.payload.get("topic", "题目分析报告")},
                                position={"x": 100, "y": 80},
                                size={"width": 900, "height": 700},
                            )],
                            trace=["detailed_analysis_report"],
                        )
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="canvas_materializer", status="completed", detail="HTML分析报告已推送到画布"))
                        yield event_dict({"type": "background.task_completed", "run_id": run_id, "detail": "分析完成！报告已推送到画布"})
                        # Persist the CanvasApp and emit app.create / app.link.create events
                        for app in materialized.apps:
                            self.store.save_app(app, student_id=context.student_id, course_id=context.course_id, agent="orchestrator_agent", skill="detailed-analysis-skill")
                            link = self.store.create_chat_link(message_id, app.app_id, f"打开 {app.title}", action="fullscreen", run_id=run_id)
                            yield event_dict(AppCreateEvent(app=app, link=link))
                            yield event_dict(AppLinkCreateEvent(link=link))
                        output = {"status": "materialized", "app_type": "custom.html", "app_id": plan.payload.get("app_id", "app-detailed-analysis")}
                    else:
                        output = {"status": "no_html_content", "reason": "html_report_builder 未生成内容"}
                        materialized = MaterializedBundle(resources=[], apps=[], trace=["detailed_analysis_no_html"])
                    step_outputs[step] = output
                elif not hermes_result:
                    output = {"summary": "没有可物化的 Hermes 资源包。", "apps": []}
                else:
                    wants_image = any(
                        isinstance(item, dict) and (item.get("app_type") == "image.explanation" or item.get("type") == "image")
                        for item in [*hermes_result.apps, *hermes_result.resources]
                    )
                    wants_custom_html = any(
                        isinstance(item, dict) and (item.get("app_type") in {"custom.html", "infographic", "interactive.demo", "animation.demo", "html.app", "custom_html"})
                        for item in hermes_result.apps
                    )
                    if wants_image:
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="image_generation_skill", status="running", detail="调用 Gemini 图片生成"))
                    if wants_custom_html:
                        yield event_dict(RunStepEvent(run_id=run_id, step_name="custom_html_app_skill", status="running", detail="校验安全 HTML / 互动演示沙箱"))
                    try:
                        materialized = await CanvasMaterializer(self.store).materialize(
                            hermes_result,
                            student_id=context.student_id,
                            course_id=context.course_id,
                            conversation_id=context.conversation_id,
                            message_id=message_id,
                            run_id=run_id,
                            fallback_refs=source_refs,
                            capability=str(plan.payload.get("capability") or ""),
                            source_material=str(plan.payload.get("source_material") or context.message),
                        )
                    except Exception as exc:
                        materialized = MaterializedBundle(resources=[], apps=[], trace=[f"canvas_materializer_failed:{exc}"])
                        step_status = "failed"
                        completed_detail = f"画布物化失败：{exc}"
                        output = {"status": "canvas_materializer_failed", "reason": str(exc)}
                        yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="failed", detail=str(exc)))
                    if wants_image and materialized.apps:
                        image_apps = [app for app in materialized.apps if app.app_type == "image.explanation"]
                        image_error = next((app.payload.get("image_error") for app in image_apps if app.payload.get("image_error")), None)
                        image_ready = any(app.payload.get("image_url") for app in image_apps)
                        if image_ready:
                            yield event_dict(RunStepEvent(run_id=run_id, step_name="image_generation_skill", status="completed", detail="Gemini 图片已写入图解 App"))
                        elif image_error:
                            yield event_dict(RunStepEvent(run_id=run_id, step_name="image_generation_skill", status="failed", detail=str(image_error)))
                    if wants_custom_html and materialized.apps:
                        html_apps = [app for app in materialized.apps if app.app_type == "custom.html"]
                        html_ready = any(app.payload.get("html") and not app.payload.get("html_error") for app in html_apps)
                        yield event_dict(
                            RunStepEvent(
                                run_id=run_id,
                                step_name="custom_html_app_skill",
                                status="completed" if html_ready else "failed",
                                detail="安全 HTML 已写入 custom.html App" if html_ready else "custom.html App 未通过安全校验",
                            )
                        )
                    for app in materialized.apps:
                        link = self.store.create_chat_link(message_id, app.app_id, f"打开 {app.title}", action="fullscreen", run_id=run_id)
                        yield event_dict(AppCreateEvent(app=app, link=link))
                        yield event_dict(AppLinkCreateEvent(link=link))
                    for resource in materialized.resources:
                        yield event_dict(ResourceCreateEvent(resource=resource, message_id=message_id))
                    if step_status == "failed":
                        output = {
                            "status": "canvas_materializer_failed",
                            "summary": "画布物化失败，已继续进入最终导师回答。",
                            "resources": [],
                            "apps": [],
                            "reason": materialized.trace[0] if materialized.trace else "unknown",
                        }
                    else:
                        output = {
                            "summary": f"已将 {len(materialized.resources)} 个资源和 {len(materialized.apps)} 个 App 写入画布。",
                            "resources": [resource.model_dump() for resource in materialized.resources],
                            "apps": [app.model_dump() for app in materialized.apps],
                        }
            elif step == "artifact_verifier":
                output = self.verify_artifacts(plan, materialized, step_outputs)
                step_status = "completed" if output.get("passed") else "failed"
                completed_detail = (
                    f"产物校验通过：{output.get('created_app_count', 0)} 个 App，{output.get('created_resource_count', 0)} 个资源"
                    if output.get("passed")
                    else f"产物校验失败：缺少 {'、'.join(output.get('missing_artifacts') or [])}"
                )
            elif step == "profile_agent":
                output = ProfileAgent().run(ProfileAgentInput(student_id=context.student_id, course_id=context.course_id, message=context.message))
                for memory in output.payload.get("memories", []):
                    yield event_dict(MemoryUpdateEvent(memory=memory, summary="画像记忆已写入"))
            elif step == "memory_agent":
                output = MemoryAgent().run(MemoryAgentInput(student_id=context.student_id, course_id=context.course_id, message=context.message))
            elif step == "knowledge_agent":
                output = KnowledgeAgent().run(KnowledgeAgentInput(course_id=context.course_id, topic=plan.payload.get("topic", "梯度下降")))
            elif step == "planner_agent":
                output = PlannerAgent().run(PlannerAgentInput(student_id=context.student_id, course_id=context.course_id, topic=plan.payload.get("topic", "神经网络")))
                yield event_dict(PathUpdateEvent(path=output.payload["path"]))
            elif step == "recommender_agent":
                output = RecommenderAgent().run(RecommenderAgentInput(student_id=context.student_id, course_id=context.course_id, topic=plan.payload.get("topic", "梯度下降")))
            elif step == "resource_bundle_agent":
                output = ResourceBundleAgent().run(ResourceBundleAgentInput(student_id=context.student_id, course_id=context.course_id, topic=plan.payload.get("topic", "梯度下降")))
                for resource in output.payload.get("resources", []):
                    yield event_dict(ResourceCreateEvent(resource=resource, message_id=message_id))
            elif step == "app_canvas_agent":
                app = None
                if plan.payload.get("capability") == "learning_path":
                    path_output = step_outputs.get("planner_agent", {})
                    path = None
                    if isinstance(path_output, dict):
                        path = path_output.get("path")
                        if path is None and isinstance(path_output.get("payload"), dict):
                            path = path_output["payload"].get("path")
                    if isinstance(path, dict):
                        app = self.learning_path_app(
                            path=path,
                            student_id=context.student_id,
                            course_id=context.course_id,
                            conversation_id=context.conversation_id,
                            message_id=message_id,
                            run_id=run_id,
                        )
                if app is None:
                    app_id = plan.payload.get("app_id", "app-gradient")
                    app = self.store.get_app(app_id, student_id=context.student_id, course_id=context.course_id) or self.store.get_app(
                        "app-gradient", student_id=context.student_id, course_id=context.course_id
                    )
                link = None
                if app:
                    link = self.store.create_chat_link(message_id, app.app_id, f"打开 {app.title}", run_id=run_id)
                    yield event_dict(AppCreateEvent(app=app, link=link))
                    yield event_dict(AppLinkCreateEvent(link=link))
                output = {"app": app.model_dump() if app else None, "link": link.model_dump() if link else None}
            elif step == "notes_skill":
                output_obj = NotesSkill().run(
                    SkillInput(
                        student_id=context.student_id,
                        course_id=context.course_id,
                        topic=plan.payload.get("topic") or context.message,
                        payload={
                            "source_summary": context.last_assistant_answer or context.message,
                            "last_assistant_answer": context.last_assistant_answer,
                            "linked_app_ids": [item.get("app_id") for item in context.recent_apps[-4:] if isinstance(item, dict) and item.get("app_id")],
                        },
                    )
                )
                resource = output_obj.resource
                saved_resource = None
                if resource:
                    saved_resource = self.store.save_resource(resource, student_id=context.student_id, course_id=context.course_id, created_by_skill="notes_skill")
                    note_app = CanvasApp(
                        app_type="notes.session",
                        title=saved_resource.title,
                        icon="NotebookPen",
                        position=CanvasPosition(x=970, y=370),
                        size=CanvasSize(width=430, height=320),
                        z_index=30,
                        group_id="agent-generated-notes",
                        payload={**saved_resource.content, "resource_id": saved_resource.resource_id, "topic": saved_resource.target_topic},
                        source={
                            "student_id": context.student_id,
                            "course_id": context.course_id,
                            "conversation_id": context.conversation_id,
                            "message_id": message_id,
                            "run_id": run_id,
                            "resource_id": saved_resource.resource_id,
                            "skill_name": "notes_skill",
                        },
                        source_refs=saved_resource.source_refs,
                        personalized_reason=saved_resource.personalized_reason,
                        actions=[{"label": "保存笔记", "action": "notes.save"}, {"label": "让导师总结", "action": "tutor.explain"}],
                    )
                    saved_app = self.store.save_app(note_app, student_id=context.student_id, course_id=context.course_id, agent="orchestrator_agent", skill="notes_skill")
                    link = self.store.create_chat_link(message_id, saved_app.app_id, f"打开 {saved_app.title}", action="fullscreen", run_id=run_id)
                    yield event_dict(AppCreateEvent(app=saved_app, link=link))
                    yield event_dict(AppLinkCreateEvent(link=link))
                    yield event_dict(ResourceCreateEvent(resource=saved_resource, message_id=message_id))
                    note_memory = self.store.create_memory(
                        EduMemoryItem(
                            student_id=context.student_id,
                            course_id=context.course_id,
                            memory_type="session_notes",
                            content=f"学习笔记：{saved_resource.title}。主题：{saved_resource.target_topic}。",
                            structured_payload={
                                "topic": saved_resource.target_topic,
                                "resource_id": saved_resource.resource_id,
                                "app_id": saved_app.app_id,
                                "conversation_id": context.conversation_id,
                                "summary": saved_resource.content,
                            },
                            confidence=0.86,
                            importance=0.72,
                            decay_rate=0.01,
                            evidence_type="notes_app",
                            source_event_id=saved_app.app_id,
                            source_agent="notes_skill",
                            tags=["session_notes", saved_resource.target_topic],
                        )
                    )
                    yield event_dict(MemoryUpdateEvent(memory=note_memory, summary=f"已记住 {saved_resource.target_topic} 学习笔记"))
                output = output_obj.model_dump()
                if saved_resource:
                    output["resource"] = saved_resource.model_dump()
                    output["app"] = saved_app.model_dump()
                    output["link"] = link.model_dump()
            elif step == "quiz_skill":
                app = self.store.get_app("app-quiz", student_id=context.student_id, course_id=context.course_id)
                link = self.store.create_chat_link(message_id, "app-quiz", "打开诊断题", run_id=run_id) if app else None
                if app:
                    yield event_dict(AppCreateEvent(app=app, link=link))
                    yield event_dict(AppLinkCreateEvent(link=link))
                output = {"app_id": "app-quiz", "link": link.model_dump() if link else None}
            elif step == "tutor_agent":
                output = TutorAgent().run(
                    TutorAgentInput(
                        student_id=context.student_id,
                        course_id=context.course_id,
                        message=context.message,
                        topic=plan.payload.get("topic", "梯度下降"),
                        app_id=plan.payload.get("app_id"),
                    )
                )
            elif step == "verifier_agent":
                output = {"summary": "资源验证流已完成。"}
            elif step == "dashboard_skill":
                dashboard = self.store.dashboard(context.student_id, course_id=context.course_id, conversation_id=context.conversation_id)
                yield event_dict(DashboardUpdateEvent(dashboard=dashboard))
                output = {"dashboard": dashboard.model_dump()}
            else:
                output = {"summary": f"{step} completed"}
            self.record_trace(run_id, step, step_order, output if isinstance(output, dict) else output.model_dump(), status=step_status)
            step_outputs[step] = output if isinstance(output, dict) else output.model_dump()
            yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status=step_status, detail=completed_detail))
            step_order += 1
            await asyncio.sleep(0.01)

        artifact_verifier = step_outputs.get("artifact_verifier")
        if isinstance(artifact_verifier, dict) and not artifact_verifier.get("passed"):
            yield event_dict(
                RunStepEvent(
                    run_id=run_id,
                    step_name="artifact_verifier",
                    status="failed",
                    detail=self.artifact_failure_text(artifact_verifier),
                )
            )

        if plan.task_type == "video_recommendations":
            retriever = step_outputs.get("video_retriever", {})
            resources = [
                LearningResource.model_validate(item)
                for item in (retriever.get("resources", []) if isinstance(retriever, dict) else [])
                if isinstance(item, dict)
            ]
            topic = str((retriever.get("query") if isinstance(retriever, dict) else None) or plan.payload.get("topic") or context.message)
            source = str((retriever.get("source") if isinstance(retriever, dict) else None) or "none")
            text = self.video_recommendation_text(topic, resources, source)
            output = {
                "provider": "local_video_recommender",
                "model": "screened_bilibili_results",
                "status": "completed",
                "resource_count": len(resources),
            }
            self.record_trace(run_id, "model_gateway", step_order, output, status="completed")
            yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="completed", detail="已生成视频推荐回答"))
            self.save_chat_message(
                context,
                "assistant",
                strip_generation_markers(text),
                run_id=run_id,
                metadata={
                    "capability": plan.payload.get("capability"),
                    "model_gateway": output,
                    "artifact_verifier": step_outputs.get("artifact_verifier"),
                },
            )
            for chunk in self._chunk_text(text):
                yield event_dict(AssistantDelta(message_id=message_id, text=chunk))
                await asyncio.sleep(0.005)
            async for artifact_event in self.emit_video_artifacts(step_outputs):
                yield artifact_event
            dashboard = self.store.dashboard(context.student_id, course_id=context.course_id, conversation_id=context.conversation_id)
            yield event_dict(DashboardUpdateEvent(dashboard=dashboard))
            self.store.finish_run(
                run_id,
                {
                    "assistant": strip_generation_markers(text),
                    "source_refs": source_refs,
                    "capability": plan.payload.get("capability"),
                    "artifact_verifier": step_outputs.get("artifact_verifier"),
                    "video_count": len(resources),
                },
                "completed",
            )
            yield event_dict(RunDone(run_id=run_id, status="completed"))
            yield event_dict(AssistantDone(message_id=message_id))
            return

        provider = self.model_gateway.normalize_provider(context.model_provider)
        provider_label = self.model_provider_label(provider)
        yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="running", detail=f"调用 {provider_label} 大模型"))
        try:
            text, model_trace = await self.generate_model_tutor_response(plan, context, rag_context, step_outputs)
            text = f"{text}{self.generation_suggestion_marker(plan, context)}"
        except ProviderBlocked as exc:
            user_reason = self.model_failure_text(provider, f"{exc.code}: {exc.reason}")
            local_text = self.local_artifact_success_text(plan, context, materialized, step_outputs, user_reason)
            if local_text:
                output = {"provider": provider, "status": "local_artifact_fallback", "reason": exc.reason, "user_message": local_text}
                self.record_trace(run_id, "model_gateway", step_order, output, status="completed")
                yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="completed", detail="模型不可用，已使用本地画布摘要回复"))
                self.save_chat_message(
                    context,
                    "assistant",
                    strip_generation_markers(local_text),
                    run_id=run_id,
                    metadata={
                        "capability": plan.payload.get("capability"),
                        "model_gateway": output,
                        "artifact_verifier": step_outputs.get("artifact_verifier"),
                    },
                )
                for chunk in self._chunk_text(local_text):
                    yield event_dict(AssistantDelta(message_id=message_id, text=chunk))
                    await asyncio.sleep(0.005)
                dashboard = self.store.dashboard(context.student_id, course_id=context.course_id, conversation_id=context.conversation_id)
                yield event_dict(DashboardUpdateEvent(dashboard=dashboard))
                self.store.finish_run(run_id, {"assistant": strip_generation_markers(local_text), "capability": plan.payload.get("capability"), "model_gateway": output}, "completed")
                yield event_dict(RunDone(run_id=run_id, status="completed"))
                yield event_dict(AssistantDone(message_id=message_id))
                return
            output = {"provider": provider, "status": exc.code, "reason": exc.reason, "user_message": user_reason}
            self.record_trace(run_id, "model_gateway", step_order, output, status="blocked")
            self.store.finish_run(run_id, output, "blocked")
            yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="failed", detail=user_reason))
            yield event_dict(AssistantDelta(message_id=message_id, text=user_reason))
            yield event_dict(RunDone(run_id=run_id, status="blocked"))
            yield event_dict(AssistantDone(message_id=message_id))
            return
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            user_reason = self.model_failure_text(provider, reason)
            local_text = self.local_artifact_success_text(plan, context, materialized, step_outputs, user_reason)
            if local_text:
                output = {"provider": provider, "status": "local_artifact_fallback", "reason": reason, "user_message": local_text}
                self.record_trace(run_id, "model_gateway", step_order, output, status="completed")
                yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="completed", detail="模型不可用，已使用本地画布摘要回复"))
                self.save_chat_message(
                    context,
                    "assistant",
                    strip_generation_markers(local_text),
                    run_id=run_id,
                    metadata={
                        "capability": plan.payload.get("capability"),
                        "model_gateway": output,
                        "artifact_verifier": step_outputs.get("artifact_verifier"),
                    },
                )
                for chunk in self._chunk_text(local_text):
                    yield event_dict(AssistantDelta(message_id=message_id, text=chunk))
                    await asyncio.sleep(0.005)
                dashboard = self.store.dashboard(context.student_id, course_id=context.course_id, conversation_id=context.conversation_id)
                yield event_dict(DashboardUpdateEvent(dashboard=dashboard))
                self.store.finish_run(run_id, {"assistant": strip_generation_markers(local_text), "capability": plan.payload.get("capability"), "model_gateway": output}, "completed")
                yield event_dict(RunDone(run_id=run_id, status="completed"))
                yield event_dict(AssistantDone(message_id=message_id))
                return
            output = {"provider": provider, "status": "failed", "reason": reason, "user_message": user_reason}
            self.record_trace(run_id, "model_gateway", step_order, output, status="failed")
            self.store.finish_run(run_id, output, "failed")
            yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="failed", detail=user_reason))
            yield event_dict(AssistantDelta(message_id=message_id, text=user_reason))
            yield event_dict(RunDone(run_id=run_id, status="failed"))
            yield event_dict(AssistantDone(message_id=message_id))
            return
        self.record_trace(run_id, "model_gateway", step_order, model_trace)
        actual_provider = str(model_trace.get("provider") or provider)
        actual_label = self.model_provider_label(actual_provider)
        if model_trace.get("provider_fallback_used"):
            detail = f"{provider_label} 不可用，已切换到 {actual_label} {model_trace['model']} 生成回复"
        else:
            detail = f"{actual_label} {model_trace['model']} 已生成回复"
        yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="completed", detail=detail))
        step_order += 1
        self.save_chat_message(
            context,
            "assistant",
            strip_generation_markers(text),
            run_id=run_id,
            metadata={
                "capability": plan.payload.get("capability"),
                "model_gateway": model_trace,
                "artifact_verifier": step_outputs.get("artifact_verifier"),
            },
        )
        for chunk in self._chunk_text(text):
            yield event_dict(AssistantDelta(message_id=message_id, text=chunk))
            await asyncio.sleep(0.005)
        dashboard = self.store.dashboard(context.student_id, course_id=context.course_id, conversation_id=context.conversation_id)
        yield event_dict(DashboardUpdateEvent(dashboard=dashboard))
        self.store.finish_run(
            run_id,
            {
                "assistant": strip_generation_markers(text),
                "source_refs": source_refs,
                "capability": plan.payload.get("capability"),
                "artifact_verifier": step_outputs.get("artifact_verifier"),
            },
            "completed",
        )
        yield event_dict(RunDone(run_id=run_id, status="completed"))
        yield event_dict(AssistantDone(message_id=message_id))

    async def run_turn(self, context: TutorTurnContext) -> list[dict[str, Any]]:
        plan = self.plan_turn(context)
        return [event async for event in self.execute_plan(plan, context)]

    def _chunk_text(self, text: str) -> list[str]:
        pieces = []
        current = ""
        for char in text:
            current += char
            if len(current) >= 18 or char in "。！？":
                pieces.append(current)
                current = ""
        if current:
            pieces.append(current)
        return pieces

    def sse_line(self, event: dict[str, Any]) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class UnifiedOrchestrator(OrchestratorAgent):
    """Hermes-First 统一编排器 —— Hermes 自主决定意图和 skill 选择。

    继承 OrchestratorAgent 以复用所有辅助方法（视频搜索、SSE、model gateway 等），
    只覆盖 plan_turn() 和 execute_plan() 两个核心方法。
    """

    name = "unified_orchestrator"

    def plan_turn(self, context: TutorTurnContext) -> AgentPlan:
        """简化版 plan_turn：只做 profile / video 特殊检测，其余全部交给 Hermes。"""
        message = context.message.lower()

        # Profile build detection
        if any(term in message for term in ["我是", "画像", "喜欢", "大一"]):
            return AgentPlan(
                task_type="profile_build",
                steps=["intent_detect", "profile_agent", "memory_agent", "dashboard_skill"],
                payload={"topic": "学习画像", "capability": "dashboard", "requires_canvas": False},
            )

        # Video search detection (B站实时搜索，Python 侧操作，不走 Hermes)
        if is_video_search_request(context.message):
            topic = extract_learning_topic(context.message)
            video_topic = clean_video_query(context.message, topic)
            is_contextual = any(
                marker in context.message
                for marker in ["相关", "这个", "这方面", "这类", "这些", "上面", "刚才", "刚刚", "上述", "该主题", "这部分", "此类"]
            )
            if is_contextual or len(video_topic) < 3 or is_generic_topic(video_topic):
                ctx_topic = self._recent_conversation_topic(context)
                if ctx_topic:
                    video_topic = ctx_topic
            if len(video_topic) < 3:
                video_topic = clean_video_query(context.message, None)
            payload: dict[str, Any] = {
                "capability": "video_recommendations",
                "topic": video_topic,
                "source_material": context.message,
                "context_source": "current_message",
                "expected_app_types": ["video.player"],
                "expected_resource_types": ["video"],
                "requires_canvas": True,
                "original_message": context.message,
            }
            return AgentPlan(
                task_type="video_recommendations",
                steps=["intent_detect", "video_retriever", "video_canvas", "artifact_verifier"],
                payload=payload,
            )

        # ── 简单问候/闲聊 → 轻量快速回复（不启动 Hermes 全管线）──
        if self._is_quick_chat(context.message):
            return AgentPlan(
                task_type="quick_answer",
                steps=["quick_answer"],
                payload={
                    "topic": context.message,
                    "source_material": context.message,
                    "capability": "answer_only",
                    "requires_canvas": False,
                    "original_message": context.message,
                },
            )

        # ── 其余一切 → Hermes 决定 ──
        return AgentPlan(
            task_type="unified_hermes",
            steps=["intent_detect", "hermes_runtime", "canvas_materializer", "artifact_verifier"],
            payload={
                "topic": context.message,
                "source_material": context.message,
                "context_source": "current_message",
                "capability": "unified_hermes",
                "requires_canvas": True,
                "original_message": context.message,
            },
        )

    @staticmethod
    def _is_quick_chat(message: str) -> bool:
        """判断是否为简单问候/闲聊，不需要 Hermes 全管线处理。"""
        stripped = message.strip().lower()
        # 纯粹的问候
        GREETINGS = {
            "你好", "嗨", "hello", "hi", "hey", "在吗", "在不在", "早上好", "晚上好", "下午好",
            "早安", "晚安", "good morning", "good evening",
        }
        if stripped in GREETINGS:
            return True
        # 以问候开头且整条消息很短（≤15字）
        SHORT_GREETING_STARTS = ["你好", "嗨", "hello", "hi", "hey"]
        if len(stripped) <= 15 and any(stripped.startswith(g) for g in SHORT_GREETING_STARTS):
            return True
        # 纯粹的致谢/道别
        FAREWELLS = {"谢谢", "多谢", "感谢", "再见", "拜拜", "bye", "thanks", "thank you", "see you"}
        if stripped in FAREWELLS:
            return True
        return False

    async def _quick_answer_stream(
        self, plan: AgentPlan, context: TutorTurnContext
    ) -> AsyncIterator[dict[str, Any]]:
        """轻量快速回复：直接用模型网关生成文本，不启动 Hermes 全管线。"""
        run_id = self.store.create_run(context.student_id, plan.task_type,
                                       {"message": context.message, "plan": plan.model_dump()})
        self.save_chat_message(context, "user", context.message, run_id=run_id,
                               metadata={"plan": plan.model_dump()})
        yield event_dict(RunStarted(run_id=run_id, task_type=plan.task_type))

        message_id = new_id("msg")
        try:
            gateway = ModelGatewayRouter()
            provider = gateway.normalize_provider(context.model_provider)
            client = gateway.client(provider)
            system_prompt = (
                "你是 LearnForge AI 学习助手，一个友好、专业的教育 AI。"
                "请用简洁、温暖的中文回复用户的问候或闲聊。"
                "回复控制在 2-3 句话以内，不要展开长篇大论。"
                "如果用户打招呼，你也友好地打招呼并简要介绍自己。"
            )
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=context.message),
            ]
            response = await client.complete(messages, stream=False)
            text = client.extract_assistant_text(response)
        except (ProviderBlocked, ModelGatewayError) as exc:
            code = exc.code if isinstance(exc, ProviderBlocked) else "model_gateway_error"
            reason = exc.reason if isinstance(exc, ProviderBlocked) else str(exc)
            yield event_dict(RunStepEvent(run_id=run_id, step_name="quick_answer",
                                          status="failed", detail=reason))
            yield event_dict(RunDone(run_id=run_id, status="failed"))
            yield event_dict(AssistantDone(message_id=message_id))
            return

        yield event_dict(AssistantDelta(message_id=message_id, text=text))
        self.save_chat_message(context, "assistant", text, run_id=run_id,
                               metadata={"capability": "answer_only"})
        yield event_dict(RunStepEvent(run_id=run_id, step_name="quick_answer",
                                      status="completed", detail="快速回复完成"))
        yield event_dict(RunDone(run_id=run_id, status="completed"))
        yield event_dict(AssistantDone(message_id=message_id))

    async def execute_plan(
        self, plan: AgentPlan, context: TutorTurnContext
    ) -> AsyncIterator[dict[str, Any]]:
        """统一执行路径：profile/video 走父类，其余 4 步主线。"""
        # 特殊路径：video_recommendations 和 profile_build 复用父类完整逻辑
        if plan.task_type in ("video_recommendations", "profile_build"):
            async for event in super().execute_plan(plan, context):
                yield event
            return

        # ── 快速闲聊：直接用模型网关，不启动 Hermes 全管线 ──
        if plan.task_type == "quick_answer":
            async for event in self._quick_answer_stream(plan, context):
                yield event
            return

        # ── unified_hermes 主线 ──
        run_id = self.store.create_run(
            context.student_id, plan.task_type,
            {"message": context.message, "plan": plan.model_dump()}
        )
        self.save_chat_message(context, "user", context.message, run_id=run_id, metadata={"plan": plan.model_dump()})
        yield event_dict(RunStarted(run_id=run_id, task_type=plan.task_type))
        self.hermes.prepare()

        topic = plan.payload.get("topic", "") or context.message
        rag_context = CourseRetriever().context_with_refs(topic, course_id=context.course_id)
        source_refs = self.source_refs_for_plan(plan, context, rag_context["source_refs"])
        rag_context = {**rag_context, "source_refs": source_refs}

        message_id = new_id("msg")
        step_order = 1
        step_outputs: dict[str, Any] = {}
        hermes_result: HermesTaskResult | None = None
        materialized: MaterializedBundle | None = None

        for step in plan.steps:
            yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="running", detail="执行中"))
            step_status = "completed"
            completed_detail = "已完成"

            if step == "intent_detect":
                # Emit context update for TopBar
                detected_topic = str(plan.payload.get("topic") or context.message)[:120].strip()
                course_label = self._course_label(context.course_id)
                yield event_dict(ContextUpdateEvent(
                    topic=detected_topic,
                    capability="unified_hermes",
                    course_label=course_label,
                    learning_objective=f"深入理解「{detected_topic}」",
                ))
                self.store.save_learning_focus(
                    context.student_id, context.course_id,
                    topic=detected_topic,
                    objective=f"深入理解「{detected_topic}」",
                    course_label=course_label,
                )
                output = {
                    "summary": f"Hermes 自主意图检测",
                    "capability": "unified_hermes",
                    "requires_canvas": True,
                    "expected_app_types": [],
                    "expected_resource_types": [],
                    "context_source": plan.payload.get("context_source"),
                }
                completed_detail = "已启动统一 Hermes 编排"

            elif step == "hermes_runtime":
                yield event_dict(RunStepEvent(
                    run_id=run_id, step_name="hermes_runtime", status="running",
                    detail="加载 LearnForge profile、全部 Skills、Toolsets/MCP"
                ))
                try:
                    hermes_result = await self.hermes_executor.run_hermes(plan, context, rag_context)
                except (ProviderBlocked, ModelGatewayError) as exc:
                    code = exc.code if isinstance(exc, ProviderBlocked) else "hermes_execution_failed"
                    reason = exc.reason if isinstance(exc, ProviderBlocked) else str(exc)
                    output = {"status": code, "reason": reason}
                    self.record_trace(run_id, step, step_order, output, status="failed")
                    self.store.finish_run(run_id, output, "failed")
                    yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="failed", detail=reason))
                    yield event_dict(AssistantDelta(message_id=message_id, text=f"Hermes 执行失败：{reason}"))
                    yield event_dict(RunDone(run_id=run_id, status="failed"))
                    yield event_dict(AssistantDone(message_id=message_id))
                    return

                # Emit capability detected by Hermes
                detected_cap = hermes_result.capability or "unified_hermes"
                yield event_dict(RunStepEvent(
                    run_id=run_id, step_name="capability_contract", status="completed",
                    detail=f"{detected_cap} · Hermes 自主判定"
                ))
                # Emit trace as skill_call events
                for trace_item in hermes_result.trace[-10:]:
                    yield event_dict(RunStepEvent(
                        run_id=run_id, step_name="skill_call", status="completed",
                        detail=str(trace_item)[:180]
                    ))

                # Handle background tasks (detailed_analysis)
                if hermes_result.mode == "background":
                    ack_text = "正在深度分析题目…"
                    yield event_dict({"type": "assistant.delta", "message_id": message_id, "text": f"✅ {ack_text}\n\n> 💡 你可以在后台运行期间继续提问，分析完成后会自动推送到画布。"})
                    yield event_dict({"type": "assistant.done", "message_id": message_id})
                    yield event_dict({"type": "background.task_started", "run_id": run_id, "label": ack_text, "task_type": plan.task_type})
                    self.save_chat_message(context, "assistant", f"✅ {ack_text}", run_id=run_id)

                completed_detail = f"Hermes 完成：{detected_cap} · {hermes_result.summary[:100]}"
                output = {
                    "summary": hermes_result.summary,
                    "capability": detected_cap,
                    "app_count": len(hermes_result.apps),
                    "resource_count": len(hermes_result.resources),
                    "trace": hermes_result.trace,
                }

            elif step == "canvas_materializer":
                if not hermes_result:
                    output = {"summary": "没有可物化的 Hermes 产物。", "apps": []}
                elif hermes_result.raw_html:
                    # detailed_analysis HTML 路径
                    html_content = hermes_result.raw_html
                    app_id = new_id("app")
                    app = CanvasApp(
                        app_id=app_id,
                        app_type="custom.html",
                        title=plan.payload.get("topic", "题目分析报告"),
                        payload={"html": html_content, "title": plan.payload.get("topic", "题目分析报告")},
                        position={"x": 100, "y": 80},
                        size={"width": 900, "height": 700},
                    )
                    materialized = MaterializedBundle(
                        resources=[],
                        apps=[app],
                        trace=["detailed_analysis_report"],
                    )
                    yield event_dict(RunStepEvent(run_id=run_id, step_name="canvas_materializer", status="completed", detail="HTML分析报告已推送到画布"))
                    yield event_dict({"type": "background.task_completed", "run_id": run_id, "detail": "分析完成！报告已推送到画布"})
                    # Persist and emit
                    for a in materialized.apps:
                        self.store.save_app(a, student_id=context.student_id, course_id=context.course_id, agent="unified_orchestrator", skill="detailed-analysis-skill")
                        link = self.store.create_chat_link(message_id, a.app_id, f"打开 {a.title}", action="fullscreen", run_id=run_id)
                        yield event_dict(AppCreateEvent(app=a, link=link))
                        yield event_dict(AppLinkCreateEvent(link=link))
                    output = {"status": "materialized", "app_type": "custom.html", "app_id": app_id}
                elif hermes_result.apps or hermes_result.resources:
                    # Standard JSON path → use CanvasMaterializer
                    try:
                        materialized = await CanvasMaterializer(self.store).materialize(
                            hermes_result,
                            student_id=context.student_id,
                            course_id=context.course_id,
                            conversation_id=context.conversation_id,
                            message_id=message_id,
                            run_id=run_id,
                            fallback_refs=source_refs,
                            capability=hermes_result.capability or "",
                            source_material=str(plan.payload.get("source_material") or context.message),
                        )
                    except Exception as exc:
                        materialized = MaterializedBundle(resources=[], apps=[], trace=[f"canvas_materializer_failed:{exc}"])
                        step_status = "failed"
                        completed_detail = f"画布物化失败：{exc}"
                        output = {"status": "canvas_materializer_failed", "reason": str(exc)}
                        yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status="failed", detail=str(exc)))
                    for a in materialized.apps:
                        link = self.store.create_chat_link(message_id, a.app_id, f"打开 {a.title}", action="fullscreen", run_id=run_id)
                        yield event_dict(AppCreateEvent(app=a, link=link))
                        yield event_dict(AppLinkCreateEvent(link=link))
                    for r in materialized.resources:
                        yield event_dict(ResourceCreateEvent(resource=r, message_id=message_id))
                    if step_status != "failed":
                        output = {
                            "summary": f"已将 {len(materialized.resources)} 个资源和 {len(materialized.apps)} 个 App 写入画布。",
                            "resources": [r.model_dump() for r in materialized.resources],
                            "apps": [a.model_dump() for a in materialized.apps],
                        }
                else:
                    output = {"summary": "Hermes 判定为纯文本回答，无画布产物。", "apps": []}
                    materialized = MaterializedBundle(resources=[], apps=[], trace=["answer_only_no_canvas"])

                step_outputs[step] = output

            elif step == "artifact_verifier":
                output = self.verify_artifacts(plan, materialized, step_outputs)
                step_status = "completed" if output.get("passed") else "failed"
                completed_detail = (
                    f"产物校验通过：{output.get('created_app_count', 0)} 个 App，{output.get('created_resource_count', 0)} 个资源"
                    if output.get("passed")
                    else f"产物校验失败：缺少 {'、'.join(output.get('missing_artifacts') or [])}"
                )

            else:
                output = {"summary": f"{step} completed"}

            self.record_trace(run_id, step, step_order, output if isinstance(output, dict) else output.model_dump(), status=step_status)
            step_outputs[step] = output if isinstance(output, dict) else output.model_dump()
            yield event_dict(RunStepEvent(run_id=run_id, step_name=step, status=step_status, detail=completed_detail))
            step_order += 1
            await asyncio.sleep(0.01)

        # ── Model Gateway: 生成最终导师回复 ──
        provider = self.model_gateway.normalize_provider(context.model_provider)
        provider_label = self.model_provider_label(provider)
        yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="running", detail=f"调用 {provider_label} 大模型"))

        try:
            text, model_trace = await self.generate_model_tutor_response(plan, context, rag_context, step_outputs)
        except (ProviderBlocked, Exception) as exc:
            user_reason = (
                self.model_failure_text(provider, f"{exc.code}: {exc.reason}")
                if isinstance(exc, ProviderBlocked)
                else self.model_failure_text(provider, f"{type(exc).__name__}: {exc}")
            )
            yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="failed", detail=user_reason))
            yield event_dict(AssistantDelta(message_id=message_id, text=user_reason))
            yield event_dict(RunDone(run_id=run_id, status="failed"))
            yield event_dict(AssistantDone(message_id=message_id))
            return

        self.record_trace(run_id, "model_gateway", step_order, model_trace)
        actual_provider = str(model_trace.get("provider") or provider)
        actual_label = self.model_provider_label(actual_provider)
        yield event_dict(RunStepEvent(run_id=run_id, step_name="model_gateway", status="completed", detail=f"{actual_label} {model_trace['model']} 已生成回复"))

        self.save_chat_message(
            context, "assistant", strip_generation_markers(text),
            run_id=run_id,
            metadata={
                "capability": hermes_result.capability if hermes_result else "unified_hermes",
                "model_gateway": model_trace,
                "artifact_verifier": step_outputs.get("artifact_verifier"),
            },
        )
        for chunk in self._chunk_text(text):
            yield event_dict(AssistantDelta(message_id=message_id, text=chunk))
            await asyncio.sleep(0.005)

        dashboard = self.store.dashboard(context.student_id, course_id=context.course_id, conversation_id=context.conversation_id)
        yield event_dict(DashboardUpdateEvent(dashboard=dashboard))
        self.store.finish_run(
            run_id,
            {
                "assistant": strip_generation_markers(text),
                "source_refs": source_refs,
                "capability": hermes_result.capability if hermes_result else "unified_hermes",
                "artifact_verifier": step_outputs.get("artifact_verifier"),
            },
            "completed",
        )
        yield event_dict(RunDone(run_id=run_id, status="completed"))
        yield event_dict(AssistantDone(message_id=message_id))
