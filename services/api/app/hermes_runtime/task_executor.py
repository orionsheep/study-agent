from __future__ import annotations

import asyncio
import ast
import base64
import hashlib
import io
import json
import logging
import os
import re
import tempfile
from html import escape
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agents.base import AgentPlan, TutorTurnContext
from app.core.config import get_settings
from app.hermes_runtime.command import resolve_hermes_command
from app.hermes_runtime.python_agent_adapter import HermesPythonAgentAdapter
from app.hermes_runtime.skill_sync import HermesSkillSync
from app.model_gateway.base import ChatMessage
from app.model_gateway.errors import ProviderBlocked, ModelGatewayError
from app.model_gateway.gemini_client import GeminiClient
from app.storage.artifacts import ObjectStorage, artifact_object_key

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Guards for user-uploaded image attachments (M10).
MAX_IMAGE_ATTACHMENTS = 10
MAX_IMAGE_ATTACHMENT_BYTES = 8 * 1024 * 1024   # 8 MB per image after base64 decode
MIN_IMAGE_ATTACHMENT_BYTES = 64                # filter out stray junk / empty payloads

def _get_logger() -> logging.Logger:
    return logging.getLogger("learnforge")

async def _safe_terminate(process: asyncio.subprocess.Process) -> None:
    """Best-effort SIGKILL + reap for a subprocess, tolerant of it already being dead.

    Guards against ProcessLookupError on kill() and races where communicate()/wait()
    find the process already reaped. Always returns without raising.
    """
    if process.returncode is not None:
        return
    try:
        process.kill()
    except ProcessLookupError:
        return
    try:
        await process.wait()
    except ProcessLookupError:
        return

class HermesTaskResult(BaseModel):
    summary: str = ""
    trace: list[str] = Field(default_factory=list)
    resources: list[dict[str, Any]] = Field(default_factory=list)
    apps: list[dict[str, Any]] = Field(default_factory=list)
    raw_text: str = ""
    # Unified Hermes fields — Hermes decides the capability and output format
    capability: str = ""       # e.g. "detailed_analysis", "resource_bundle", "answer_only"
    topic: str = ""
    mode: str = "synchronous"  # "synchronous" | "background"
    raw_html: str = ""         # direct HTML output (detailed_analysis path)
    text_response: str = ""    # plain-text tutor response (answer_only path)

class HermesTaskExecutor:
    _ACTIVE_PROCESSES: dict[str, asyncio.subprocess.Process] = {}
    _ACTIVE_SDK_AGENTS: dict[str, Any] = {}
    _CANCELLED_RUNS: set[str] = set()
    _VISION_CACHE: dict[str, str] = {}

    def __init__(self) -> None:
        self.settings = get_settings()

    @classmethod
    def request_cancel(cls, run_id: str) -> bool:
        """Mark a run as cancelled and terminate its active Hermes subprocess."""
        if not run_id:
            return False
        cls._CANCELLED_RUNS.add(run_id)
        process = cls._ACTIVE_PROCESSES.get(run_id)
        if process and process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            return True
        agent = cls._ACTIVE_SDK_AGENTS.get(run_id)
        if agent:
            interrupt = getattr(agent, "interrupt", None)
            if callable(interrupt):
                try:
                    interrupt()
                    return True
                except Exception:
                    return True
        return False

    @classmethod
    def is_cancelled(cls, run_id: str | None) -> bool:
        return bool(run_id and run_id in cls._CANCELLED_RUNS)

    @classmethod
    def clear_run(cls, run_id: str | None) -> None:
        if not run_id:
            return
        cls._ACTIVE_PROCESSES.pop(run_id, None)
        cls._ACTIVE_SDK_AGENTS.pop(run_id, None)
        cls._CANCELLED_RUNS.discard(run_id)

    @staticmethod
    def _has_uploaded_images(context: TutorTurnContext) -> bool:
        return bool((getattr(context, "image_data", None) or [])[:MAX_IMAGE_ATTACHMENTS])

    @staticmethod
    def _vision_failure_text() -> str:
        return (
            "图片无法可靠识别。请重新上传一张更清晰、无遮挡、完整包含题干和选项的图片；"
            "在可靠 OCR 完成前，我不会根据文件名或历史对话生成题解，以免讲成无关内容。"
        )

    @staticmethod
    def _vision_analysis_is_reliable(text: str) -> bool:
        cleaned = (text or "").strip()
        if len(cleaned) < 220:
            return False
        failure_markers = ["returned empty", "Vision 调用失败", "无法可靠识别", "Gemini Vision 未能"]
        return not any(marker in cleaned for marker in failure_markers)

    @classmethod
    def _image_cache_key(cls, image_data: list[str]) -> str:
        digest = hashlib.sha256()
        for item in image_data:
            try:
                img_bytes, _ = cls._decode_image_attachment(item)
            except Exception:
                digest.update(str(item[:128]).encode("utf-8", errors="ignore"))
                continue
            digest.update(hashlib.sha256(img_bytes).digest())
        return digest.hexdigest()

    def _normalize_images_for_vision(self, image_data: list[str]) -> tuple[list[str], list[str]]:
        """Convert uploads to plain RGB JPEG data URLs before sending to Gemini.

        Some phone photos carry HDR / Display-P3 / exotic JPEG metadata that Gemini
        intermittently rejects with "Unable to process input image". Pillow can read
        those files, so we normalize orientation, color mode, dimensions and encoding
        before any Vision round. This keeps OCR deterministic for browser uploads.
        """
        normalized: list[str] = []
        notes: list[str] = []
        try:
            from PIL import Image, ImageOps
        except Exception as exc:
            notes.append(f"图片标准化不可用，继续使用原始上传图：{type(exc).__name__}")
            return image_data, notes

        for index, item in enumerate(image_data, 1):
            try:
                img_bytes, _ = self._decode_image_attachment(item)
                source = Image.open(io.BytesIO(img_bytes))
                source = ImageOps.exif_transpose(source)
                if source.mode not in {"RGB", "L"}:
                    source = source.convert("RGB")
                elif source.mode == "L":
                    source = source.convert("RGB")
                width, height = source.size
                max_edge = max(width, height)
                if max_edge > 2600:
                    scale = 2600 / max_edge
                    source = source.resize(
                        (max(1, int(width * scale)), max(1, int(height * scale))),
                        Image.Resampling.LANCZOS,
                    )
                buffer = io.BytesIO()
                source.save(buffer, format="JPEG", quality=92, optimize=True, progressive=False)
                normalized.append(f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}")
                notes.append(
                    f"图片 {index}: 已转为标准 RGB JPEG，原始尺寸 {width}x{height}，"
                    f"Vision 输入尺寸 {source.width}x{source.height}"
                )
            except Exception as exc:
                _get_logger().warning(
                    "image_pre_analysis: failed to normalize image %d (%s: %s)",
                    index,
                    type(exc).__name__,
                    exc,
                )
                notes.append(f"图片 {index}: 标准化失败，已保留原始上传图 ({type(exc).__name__})")
                normalized.append(item)
        return normalized, notes

    def provider_name(self) -> str:
        return "gemini"

    def provider_attempts(self) -> list[tuple[str, str]]:
        attempts: list[tuple[str, str]] = []
        if getattr(self.settings, "gemini_api_key", ""):
            attempts.append(("gemini", self.settings.gemini_text_model))
            if getattr(self.settings, "gemini_text_fallback_model", "") and self.settings.gemini_text_fallback_model != self.settings.gemini_text_model:
                attempts.append(("gemini", self.settings.gemini_text_fallback_model))
        if not attempts:
            # No provider has credentials. Failing fast with a clear reason is better
            # than queueing a guaranteed 401/auth-failure round-trip to the gateway.
            raise ProviderBlocked(
                "blocked_missing_credentials",
                "No Gemini credentials configured (set GEMINI_API_KEY).",
            )
        return list(dict.fromkeys(attempts))

    def looks_like_provider_failure(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            marker in lowered
            for marker in [
                "api call failed",
                "insufficient account balance",
                "http 402",
                "provider error",
                "rate limit",
                "quota",
                "streaming request failed",
                "server disconnected",
                "unexpected_eof",
                "unexpected eof",
                "ssl:",
            ]
        )

    def command_path(self) -> str:
        if self.settings.hermes_require_sdk:
            probe = HermesPythonAgentAdapter().probe()
            raise ProviderBlocked(
                "blocked_sdk_required",
                (
                    "HERMES_REQUIRE_SDK=true forbids local Hermes CLI fallback. "
                    f"SDK status={probe.status}; {probe.reason}"
                ),
            )
        configured = self.settings.hermes_command.strip()
        resolved = resolve_hermes_command(configured)
        if resolved:
            return resolved
        raise ProviderBlocked("blocked_missing_runtime", f"Hermes CLI is not available at {configured or 'hermes'}.")

    def use_sdk_backend(self) -> bool:
        probe = HermesPythonAgentAdapter().probe()
        if probe.status == "ready":
            return True
        if self.settings.hermes_require_sdk:
            raise ProviderBlocked("blocked_missing_runtime", probe.reason)
        return False

    async def _invoke_hermes_sdk(
        self,
        prompt: Any,
        provider: str,
        model: str,
        on_stderr_line: "Callable[[str], Awaitable[None]] | None" = None,
        run_id: str | None = None,
        persist_user_message: str | None = None,
        student_id: str | None = None,
        on_hermes_event: "Callable[[dict], Awaitable[None]] | None" = None,
        conversation_id: str | None = None,
    ) -> tuple[int, str, str]:
        if self.is_cancelled(run_id):
            raise asyncio.CancelledError()
        adapter = HermesPythonAgentAdapter()
        probe = adapter.probe()
        if probe.status != "ready":
            return 2, "", f"Hermes SDK unavailable: {probe.reason}"
        # ── Hermes callback → async 事件 bridge ──
        # SDK 的 callback 是同步调用(在 asyncio.to_thread 的子线程里),需要通过
        # call_soon_threadsafe 把事件推回主事件循环,再交给 on_hermes_event。
        loop = asyncio.get_running_loop()
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        def _push(event: dict[str, Any]) -> None:
            """同步 callback 用:线程安全地把事件塞进 async queue。"""
            try:
                loop.call_soon_threadsafe(event_queue.put_nowait, event)
            except RuntimeError:
                pass  # loop 已关闭(收尾阶段),忽略

        hermes_callbacks = {
            "thinking_callback": lambda text: _push({"type": "hermes.thinking", "text": str(text or "")[:200], "run_id": run_id or ""}),
            "reasoning_callback": lambda text: _push({"type": "hermes.reasoning", "text": str(text or "")[:1500], "run_id": run_id or ""}),
            "status_callback": lambda text: _push({"type": "hermes.status", "text": str(text or "")[:200], "run_id": run_id or ""}),
            "step_callback": lambda count, prev_tools: _push({"type": "hermes.tool_call", "iteration": int(count), "tools": [t.get("name", "") for t in (prev_tools or [])][:5], "run_id": run_id or ""}),
        }
        try:
            agent = adapter.build_health_agent(
                # Phase B：session_id 用稳定的 conversation_id（每会话不变），让 Hermes
                # 像本地安装一样跨轮持有会话记忆。run_id 仍用于 _ACTIVE_SDK_AGENTS 追踪/取消。
                session_id=conversation_id or run_id or f"conv_{uuid4().hex}",
                max_iterations=16,
                provider_override=provider,
                model_override=model,
                user_id=student_id,
                hermes_callbacks=hermes_callbacks,
            )
            if run_id:
                self._ACTIVE_SDK_AGENTS[run_id] = agent
            entrypoints = ["run_conversation", "arun", "run", "achat", "chat", "ainvoke", "invoke", "aexecute", "execute", "ask", "aask"]
            last_error = ""
            for name in entrypoints:
                method = getattr(agent, name, None)
                if not callable(method):
                    continue
                if self.is_cancelled(run_id):
                    raise asyncio.CancelledError()
                if on_stderr_line:
                    await on_stderr_line(f"Hermes SDK embedded call: {name}")
                try:
                    if name == "run_conversation" and persist_user_message is not None:
                        call = lambda: method(prompt, persist_user_message=persist_user_message)
                    else:
                        call = lambda: method(prompt)
                    if asyncio.iscoroutinefunction(method):
                        if name == "run_conversation" and persist_user_message is not None:
                            result = await method(prompt, persist_user_message=persist_user_message)
                        else:
                            result = await method(prompt)
                    else:
                        result = await asyncio.to_thread(call)
                    if hasattr(result, "__await__"):
                        result = await result
                    # 排空 callback 事件 queue(运行期间累积,运行后统一转发)
                    while not event_queue.empty():
                        evt = event_queue.get_nowait()
                        if on_hermes_event:
                            try:
                                await on_hermes_event(evt)
                            except Exception:
                                pass
                    text = self._stringify_sdk_result(result)
                    if text.strip():
                        return 0, text.strip(), ""
                    last_error = f"{name} returned empty output"
                except TypeError as exc:
                    last_error = f"{name} signature mismatch: {exc}"
                    continue
                except Exception as exc:
                    last_error = f"{name} failed: {type(exc).__name__}: {exc}"
                    continue
            return 2, "", last_error or "Hermes SDK agent has no supported run/chat/invoke method."
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return 2, "", f"Hermes SDK invocation failed: {type(exc).__name__}: {exc}"
        finally:
            if run_id:
                self._ACTIVE_SDK_AGENTS.pop(run_id, None)

    @staticmethod
    def _normalize_image_bytes_for_artifact(img_bytes: bytes) -> tuple[bytes, str]:
        """Store chat uploads as ordinary RGB JPEGs so SDK/file/vision tools can read them.

        Phone images can arrive with uncommon color profiles or metadata. We keep the
        original visual content but normalize orientation, color mode, dimensions, and
        encoding before handing it to Hermes.
        """
        try:
            from PIL import Image, ImageOps
        except Exception:
            return img_bytes, "jpeg"
        source = Image.open(io.BytesIO(img_bytes))
        source = ImageOps.exif_transpose(source)
        if source.mode != "RGB":
            source = source.convert("RGB")
        max_edge = max(source.size)
        if max_edge > 2600:
            scale = 2600 / max_edge
            source = source.resize(
                (max(1, int(source.width * scale)), max(1, int(source.height * scale))),
                Image.Resampling.LANCZOS,
            )
        buffer = io.BytesIO()
        source.save(buffer, format="JPEG", quality=92, optimize=True, progressive=False)
        return buffer.getvalue(), "jpeg"

    @staticmethod
    def _stringify_sdk_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            for key in ("assistant_text", "text_response", "text", "content", "output", "message", "summary"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            return json.dumps(result, ensure_ascii=False)
        if hasattr(result, "model_dump"):
            return HermesTaskExecutor._stringify_sdk_result(result.model_dump())
        for attr in ("assistant_text", "text_response", "text", "content", "output", "message", "summary"):
            value = getattr(result, attr, None)
            if isinstance(value, str) and value.strip():
                return value
        return str(result)

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["HERMES_HOME"] = str(self.settings.project_root / self.settings.hermes_home)
        env["HERMES_ACCEPT_HOOKS"] = "1"
        provider = self.provider_name()
        model = self.settings.gemini_text_model
        env["HERMES_PROVIDER"] = provider
        env["HERMES_INFERENCE_PROVIDER"] = provider
        env["HERMES_INFERENCE_MODEL"] = model
        gemini_max_tokens = int(getattr(self.settings, "gemini_max_tokens", 32768))
        if self.settings.gemini_api_key:
            env.setdefault("GEMINI_API_KEY", self.settings.gemini_api_key)
        env.setdefault("GEMINI_TEXT_MODEL", self.settings.gemini_text_model)
        env.setdefault("GEMINI_IMAGE_MODEL", self.settings.gemini_image_model)
        env["GEMINI_MAX_TOKENS"] = str(gemini_max_tokens)
        return env

    def skills_for_plan(self, plan: AgentPlan, context: TutorTurnContext) -> list[str]:
        contract_skills = plan.payload.get("hermes_skills") if isinstance(plan.payload, dict) else None
        if isinstance(contract_skills, list) and contract_skills:
            defaults = [item.strip() for item in self.settings.hermes_default_skills.split(",") if item.strip()]
            normalized = [str(item).strip() for item in contract_skills if str(item).strip()]
            return list(dict.fromkeys(normalized + defaults))
        message = context.message.lower()
        defaults = [item.strip() for item in self.settings.hermes_default_skills.split(",") if item.strip()]
        if any(term in message for term in ["图片", "画图", "出图", "插图", "配图", "教学图", "图解"]):
            priority = ["image-generation-skill", "custom-html-app-skill", "verifier-skill", "app-generation-skill", "resource-bundle-skill"]
            return list(dict.fromkeys(priority + defaults))
        if any(term in message for term in ["信息图", "infographic", "海报", "可视化"]):
            priority = ["custom-html-app-skill", "document-skill", "verifier-skill", "app-generation-skill", "resource-bundle-skill"]
            return list(dict.fromkeys(priority + defaults))
        if any(term in message for term in ["ppt", "幻灯", "课件", "演示文稿", "deck", "slides", "瑞士风", "杂志风"]):
            priority = ["guizang-ppt-skill", "ppt-skill", "custom-html-app-skill", "verifier-skill", "app-generation-skill", "resource-bundle-skill"]
            return list(dict.fromkeys(priority + defaults))
        return defaults

    @staticmethod
    def _truncate_text(value: Any, limit: int) -> str:
        text = str(value or "")
        return text if len(text) <= limit else text[:limit] + "…[截断]"

    @classmethod
    def _compact_item(cls, item: Any, *, text_limit: int = 400) -> Any:
        """Drop heavy fields (html/content/payload bodies) so prompt args stay bounded."""
        if not isinstance(item, dict):
            return cls._truncate_text(item, text_limit)
        keep = ("id", "app_id", "resource_id", "title", "app_type", "type", "topic", "target_topic", "role", "text", "summary")
        compact: dict[str, Any] = {}
        for key in keep:
            if key in item and item[key] is not None:
                compact[key] = cls._truncate_text(item[key], text_limit) if isinstance(item[key], str) else item[key]
        return compact or {"_": cls._truncate_text(item, text_limit)}

    def build_resource_bundle_prompt(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any], image_analysis: str = ""
    ) -> str:
        expected_app_types = plan.payload.get("expected_app_types", [])
        expected_resource_types = plan.payload.get("expected_resource_types", [])
        required_outputs = list(dict.fromkeys([*expected_resource_types, *expected_app_types]))
        repair_missing = plan.payload.get("protocol_repair_missing", [])
        # SDK runs receive images as multimodal image_url parts. Local file paths are
        # only for the explicit non-SDK developer fallback.
        image_file_paths = [] if (rag_context.get("current_image_artifacts") or self.use_sdk_backend()) else self._save_image_attachments(context)
        payload = {
            "task": "learnforge_resource_bundle",
            "student_id": context.student_id,
            "course_id": context.course_id,
            "conversation_id": context.conversation_id,
            "user_message": context.message,
            "task_type": plan.task_type,
            "capability": plan.payload.get("capability", "resource_bundle"),
            "capability_contract": plan.payload.get("capability_contract", {}),
            "topic": plan.payload.get("topic") or context.message,
            "source_material": plan.payload.get("source_material") or context.message,
            "context_source": plan.payload.get("context_source"),
            "last_assistant_answer": self._truncate_text(context.last_assistant_answer, 2000),
            "recent_messages": [self._compact_item(m, text_limit=1200) for m in context.recent_messages[-10:]],
            "recent_apps": [self._compact_item(a) for a in context.recent_apps[-6:]],
            "recent_resources": [self._compact_item(r) for r in context.recent_resources[-6:]],
            "profile": self._truncate_text(json.dumps(context.profile, ensure_ascii=False), 1200) if context.profile else "",
            "student_memories": context.student_memories[-12:],
            "rag_context": self._truncate_text(rag_context.get("context", ""), 8000),
            "source_refs": (rag_context.get("source_refs", []) or [])[:20],
            "required_outputs": required_outputs,
            "expected_app_types": expected_app_types,
            "expected_resource_types": expected_resource_types,
            "repair_missing": repair_missing,
            "preloaded_skills": self.skills_for_plan(plan, context),
            "enabled_toolsets": [item.strip() for item in self.settings.hermes_toolsets.split(",") if item.strip()],
            "has_images": len(image_file_paths) > 0,
            "image_count": len(image_file_paths),
        }
        artifact_contract = (
            "HARD ARTIFACT CONTRACT:\n"
            f"- You MUST return every app_type in expected_app_types exactly once or more: {json.dumps(expected_app_types, ensure_ascii=False)}.\n"
            f"- You MUST return every resource type in expected_resource_types exactly once or more: {json.dumps(expected_resource_types, ensure_ascii=False)}.\n"
            "- Do not substitute app types. Do not omit resources because an app was generated. Do not only explain what you would generate.\n"
            "- If expected_app_types contains custom.html, apps MUST include an object with app_type='custom.html' and payload.html containing runnable HTML.\n"
            "- If expected_resource_types contains document, resources MUST include an object with type='document', title, content, source_refs, and personalized_reason.\n"
            "- If expected_resource_types contains ppt, resources MUST include an object with type='ppt', title, content, source_refs, and personalized_reason.\n"
            "- The final response is invalid unless the JSON contains both arrays: apps and resources, even when one array is empty.\n"
        )
        repair_instruction = ""
        if repair_missing:
            repair_instruction = (
                "This is a protocol repair attempt. The previous JSON missed these required artifacts: "
                f"{json.dumps(repair_missing, ensure_ascii=False)}. Return the missing artifacts exactly, with valid payloads, while preserving any already valid artifacts.\n"
            )
        if plan.payload.get("interactive_repair"):
            repair_instruction += (
                "This is an INTERACTIVE_APP_REPAIR attempt. The user is reporting that the current canvas "
                "custom.html model/module has broken controls, incorrect behavior, or a requested feature change. "
                "Treat INPUT_JSON.previous_html as the primary editable artifact, preserve the original learning topic "
                "and working interactions, apply INPUT_JSON.repair_reason, and return a corrected replacement custom.html app. "
                "Do not return a detailed-analysis report, static explanation, concept card, or unrelated resource bundle.\n"
            )
        capability = plan.payload.get("capability", "resource_bundle")
        custom_html_instruction = (
            "If expected_app_types contains custom.html, create a polished, self-contained HTML micro-app with real visible Chinese content. "
            "It must cover: 标题与目标、核心直觉、可视化主体、步骤/公式、例题、常见误区、自测题、下一步建议. Use the built-in LearnForge Lab Runtime as the front-end framework when useful: "
            "wrap the component in <section class='lfx-lab'>, use lfx-hero/lfx-title/lfx-grid/lfx-card/lfx-stage/lfx-toolbar classes, and call window.LF.store, window.LF.bars, "
            "window.LF.sparkline, window.LF.tabs, window.LF.ranges, or window.LF.quiz for state, charts, tabs, sliders, and self-checks. Prefer SVG, CSS motion, data-driven charts, "
            "and one strong interactive scene over static cards. You may use trusted HTTPS JavaScript libraries/modules such as Three.js when a 3D/WebGL model is the best representation; keep the app runnable in a browser sandbox. Do not create fake buttons, empty containers, inert charts, iframes, forms, "
            "event handler attributes, English placeholder text, LABEL placeholders, or script-dependent blank stages. "
            "CRITICAL: The entire generated HTML string MUST be placed inside the `html` key of the `payload` dictionary.\n"
        )
        if capability == "interactive_demo":
            custom_html_instruction = (
                "If expected_app_types contains custom.html (capability: interactive_demo), create an IMMERSIVE, FULL-SCREEN interactive simulation. "
                "DO NOT use generic text layouts, the LearnForge 'lfx-lab' dashboard layout, generic concept cards, or Input/Action/Output teaching shells. Instead, build a highly advanced, visually stunning graphical simulation generated for THIS topic. "
                "Use an internal multi-agent production workflow before writing the final JSON: "
                "Demo Architect defines the scene graph, state schema, topic-specific variables, control contract, and first-frame composition; "
                "Graphics Engineer implements the visual system with Canvas/SVG/CSS 3D/WebGL/Three.js when useful, including responsive sizing and nonblank first render; "
                "Interaction Engineer binds every control through delegated addEventListener handlers and verifies each button/slider/drag gesture mutates state and causes a visible scene update; "
                "QA Verifier checks selectors, no overlap, no dead controls, no template leakage, no blank stage, no fake data, no unrelated topic drift, and no unsupported native app_type. "
                "Do not reveal this workflow; use it only to improve the final custom.html payload. "
                "If you use React/Vue-style state, output the fully runnable compiled DOM/JavaScript pattern, never raw template syntax such as {{ value }}, JSX, SFC blocks, or Babel-only code. "
                "Use framework-like architecture with a state object, render() function, component sections, SVG/Canvas drawing, and delegated event handling that works in a plain sandbox. "
                "Advanced Demo Runtime requirements: define an explicit simulation state object, a pure-ish computeModel/updateSimulation step, a drawScene/render step, an input-controller map for every slider/button/drag gesture, and a visible first frame that does not depend on delayed user action. "
                "Focus on rendering REAL mathematical curves, scientific phenomena, 3D/WebGL models, or dynamic data. Include smooth animations and interactive controls (sliders, drag-and-drop, camera orbit/zoom when useful). "
                "For scientific or physics demos, the visual scene must be a continuous animated model, not a decorative infographic: include particles/vector fields/force or energy overlays when relevant, live numeric readouts, a conservation/error readout where applicable, and equation-term visualization that changes with user input. "
                "For spatial or 3D topics, prefer a split layout with controls in a fixed side panel and the model in a separate stage so controls never cover the object; include drag orbit, wheel/slider zoom, reset, and live state readouts. "
                "For Bernoulli/fluid/Venturi requests specifically, build a complete Venturi simulation: pipe geometry must visibly narrow, v2 must follow continuity v2=v1/(A2/A1), particles must accelerate in the throat with trails, pressure must drop in the throat through a pressure-color field and manometer/gauge readings, streamlines or velocity arrows must be toggleable, and the Bernoulli energy terms P, 1/2 rho v^2, and rho g h must be shown as live bars or readouts. "
                "For Rubik's cube / 魔方 requests, render a clearly visible 3x3x3 cube with 27 cubies or an equivalent complete 3D model; implement U, U', D, D', F, F', B, B', R, R', L, L' controls, scramble, reset, undo or demo playback, queue/readout text, camera orbit/zoom, and no obstructing overlay. Every move button MUST have data-move and MUST be handled by a delegated click listener. "
                "Ensure the mathematical or scientific logic is correct and fully visualized (e.g., draw the actual axes and curve for a quadratic function). "
                "Keep the context strictly bound to INPUT_JSON.topic and INPUT_JSON.source_material. For a quadratic-function request, discuss coefficients, parabola shape, vertex, symmetry axis, roots, discriminant, and function values; DO NOT mention learning rate, gradient descent, loss functions, parameter updates, springs, or elastic potential energy unless the user explicitly asks for those topics. "
                "For a sorting-algorithm request, render an actual sorting visualizer with bars or Canvas, animated compare/swap/move states, algorithm selection, speed controls, step mode, and metrics; DO NOT return uncompiled Vue/React template variables such as currentAlgoInfo or arraySize. "
                "MANDATORY REQUIREMENTS FOR EVERY INTERACTIVE DEMO: "
                "(1) Must include at least one <canvas> or <svg> element with a corresponding <script> block; WebGL/Three.js scenes are encouraged for spatial topics. "
                "(2) Must render VISIBLE objects (blocks, curves, particles, bars, arrows, shapes) — not just text cards. "
                "(3) Must have an animation loop (requestAnimationFrame or setInterval) that updates the canvas/svg. "
                "(4) Must provide interactive controls (sliders, buttons, drag) that produce visible effects. "
                "(4a) Every button MUST have a data-action or data-move attribute, and the script MUST include a click event listener that reads those attributes; no dead controls are allowed. "
                "(5) Must display real-time numeric readouts (position, velocity, energy, etc.) that update during animation. "
                "(6) For momentum/collision topics: draw two visible blocks with velocity arrows, implement 1D collision physics (m1*v1 + m2*v2 = const), show momentum and kinetic energy before/after, and allow dragging blocks. "
                "(7) For function/math topics: draw actual axes, grid lines, and the function curve; allow dragging observation points; show derivative/tangent/integral area. "
                "(8) SELF-CHECK: Before outputting, verify there is NO {{ }}, no Vue/React template syntax, no English placeholder text, no fake buttons, no overlapping control panel on top of the main object, and that at least one Canvas/SVG or complete CSS/WebGL 3D scene with script animation loop exists. "
                "Do not create fake inert charts, placeholder controls, blank stages, or script-dependent first screens. "
                "Do not rely on backend hardcoded demo templates. Infer the topic's variables, objects, equations, states, and interactions at generation time and implement them directly in payload.html. "
                "ABSOLUTELY FORBIDDEN: When capability is interactive_demo, the app_type MUST be custom.html. You are STRICTLY FORBIDDEN from returning physics.work_energy_demo, math.gradient_descent_demo, or any other native demo app_type, EVEN IF the topic relates to work, energy, kinetic energy, the work-energy theorem, gradient descent, or any concept those native demos cover. Those native demos are generic mass/velocity/force or learning-rate sliders with NO topic-specific visualization and are NOT acceptable here. "
                "DO NOT reinterpret or generalize the user's topic into a different concept (e.g. do NOT turn '伯努利定律/Bernoulli' into '动能定理/work-energy theorem', do NOT turn a fluid request into a generic block-on-track demo). Build a custom.html simulation that DIRECTLY depicts the user's actual topic — for a Bernoulli/fluid/Venturi request, draw a real pipe with a narrowing throat, animated flowing fluid particles that speed up in the throat, streamlines/velocity vectors, pressure-field coloring, manometers, energy-term bars, camera orbit/zoom, and live pressure/velocity gauges showing the pressure drop. "
                "CRITICAL: The entire generated HTML string MUST be placed inside the `html` key of the `payload` dictionary (i.e. `payload: {\"html\": \"...\"}`).\n"
            )
        if capability == "ppt":
            custom_html_instruction = (
                "For PPT / slide deck requests, create a complete single-file HTML horizontal-swipe deck. "
                "Return exactly one app with app_type='custom.html' and payload.html containing the full deck HTML. "
                "The deck must use <section class='slide'> for each page (at least 4 pages), "
                "a .deck container with scroll-snap-type:x mandatory, and ArrowRight/ArrowLeft keyboard navigation. "
                "Also return a type='ppt' resource. "
                "The deck must be self-contained, 16:9 responsive, keyboard/touch navigable. "
                "Include visible Chinese slide copy, strong typography hierarchy, and slide numbers. "
                "Do not output markdown, external file paths, or a placeholder slides list without HTML. "
                "CRITICAL: apps array MUST contain exactly one app_type='custom.html' object with full HTML in payload.html.\n"
            )
        if capability == "resource_bundle" and "custom.html" in expected_app_types and "ppt" in expected_resource_types:
            custom_html_instruction += (
                "If one of the requested resources is ppt and custom.html is also expected, the custom.html app should be a Guizang-style HTML slide deck, not an infographic.\n"
            )

        # Build image file paths block for vision analysis
        image_attachment_block = ""
        if image_file_paths:
            image_attachment_block = "\n\n## 🖼️ 用户上传的图片/截图 (User Uploaded Images)\n"
            image_attachment_block += f"共 {len(image_file_paths)} 张图片已保存到本地文件。\n"
            image_attachment_block += "请使用你的 **file** 工具读取每张图片文件，然后使用 **vision** 能力逐张仔细分析。\n"
            image_attachment_block += "如果图片中包含手写题目、试卷截图、公式、图表等，请精确提取所有文字和数字信息。\n"
            image_attachment_block += "分析完图片内容后，按照 detailed-analysis-skill 的五步法生成 HTML 报告。\n\n"
            for i, img_path in enumerate(image_file_paths, 1):
                image_attachment_block += f"**图片 {i} 文件路径:** `{img_path}`\n"
            if image_analysis:
                image_attachment_block += (
                    "\n### API 层多轮 Vision 预识别结果\n"
                    "下面内容来自：整体 OCR -> 局部放大复核 -> 原图回看合并。"
                    "请优先基于这份题面材料生成后续产物；如再次查看图片发现差异，以图片为准并说明修正。\n"
                    f"{image_analysis}\n"
                )
        return (
            "You are the LearnForge Hermes execution agent. Execute the resource-bundle-skill.\n"
            "Return ONLY valid JSON matching the Resource Bundle Skill contract. No markdown fences.\n"
            "For Chinese user requests, all titles and visible learning copy should be Chinese.\n"
            f"{artifact_contract}"
            "For infographic requests, obey expected_app_types. If expected_app_types contains image.explanation, create an image.explanation payload with topic, teaching_goal, visual_brief, provider_alias='nanobanana', and overlay_labels; do not create custom.html unless it is also explicitly expected.\n"
            f"{custom_html_instruction}"
            "STRICT COLOR CHECKING MECHANISM: You MUST implement a strict self-verification mechanism for your color schemes and aesthetics. Before finalizing the HTML, verify that your color palette is professional, modern, and harmonious. Ensure high contrast for readability (e.g., no light text on light backgrounds, avoid garish neon or problematic color combinations). If your color scheme is problematic or hard to read, you MUST self-correct and modify the CSS before outputting. Never deliver a demo with poor colors.\n"
            "For image, drawing, illustration, or teaching-diagram requests, create an image.explanation app payload with topic, teaching_goal, visual_brief, provider_alias, and overlay_labels. The API server will call Gemini/Nano Banana for image pixels; request simplified Chinese text inside the generated image, not English labels or frontend-only label areas.\n"
            "ONLY if expected_app_types EXPLICITLY contains physics.work_energy_demo, return that app_type with compact numeric payload keys such as mass, force, displacement, initialVelocity, finalVelocity, teaching_goal, and topic. Do not generate custom HTML for this case. NEVER choose physics.work_energy_demo on your own when it is not in expected_app_types — it is a generic mass/velocity/force slider with no topic-specific visualization.\n"
            "ONLY if expected_app_types EXPLICITLY contains math.gradient_descent_demo, return that app_type with compact numeric payload keys such as learning_rate, iterations, loss_curve, parameter_path, teaching_goal, and topic. Do not generate custom HTML for this case. NEVER choose math.gradient_descent_demo on your own when it is not in expected_app_types.\n"
            "STRICT APP_TYPE RULE: Choose app_type ONLY from expected_app_types. Do not substitute a native demo (physics.work_energy_demo / math.gradient_descent_demo) for a custom.html interactive_demo request just because the topic seems related to work, energy, or optimization. When expected_app_types is [\"custom.html\"], you MUST return custom.html.\n"
            "For mindmap, quiz, code lab, PPT, video script, notes, learning path, and dashboard requests, create the corresponding app_type from expected_app_types. For PPT requests, expected_app_types is custom.html because LearnForge renders Guizang web PPT decks as sandboxed HTML apps.\n"
            "If the user says based on the previous answer, use last_assistant_answer as the primary source material.\n"
            "Every app must include app_type, title, payload, and source_refs. Every resource must include type, title, content, source_refs, and personalized_reason.\n"
            "STRICT NAMING RULE: every app.title and resource.title must be generated from the actual content, topic, question stem, slide theme, code goal, visual brief, or script scene. Never use generic titles such as 测试题, 练习题, 学习资源, App, 组件, PPT预览, 视频脚本, 教学图解资产, or 自定义组件. If multiple components share a type, their titles must still be unique and content-specific.\n"
            "Escape every newline inside string values as \\n. Never emit raw multiline strings, trailing prose, comments, or markdown fences.\n"
            "Use preloaded skills, configured toolsets, and MCP tools when useful, but keep the final answer as the required JSON object.\n"
            "Do not write files, do not mutate the repository, and do not call image providers; the API server will persist and render.\n"
            f"{image_attachment_block}"
            "CRITICAL OUTPUT FORMAT — your entire response MUST be exactly ONE JSON object and nothing else: "
            "the first character is '{' and the last character is '}'. No greeting, no explanation, no reasoning, "
            "no markdown code fences, no text before or after the JSON. If you are unsure, still output your best valid JSON object.\n\n"
            f"{repair_instruction}"
            f"INPUT_JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )

    def _repair_json_candidate(self, candidate: str) -> dict[str, Any] | None:
        repaired = candidate.strip()
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        repaired = repaired.replace("\ufeff", "")
        for parser_input in (repaired, repaired.replace("True", "true").replace("False", "false").replace("None", "null")):
            try:
                data = json.loads(parser_input)
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                pass
        try:
            literal = ast.literal_eval(repaired)
            return literal if isinstance(literal, dict) else None
        except (SyntaxError, ValueError):
            return None

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove ```json ... ``` (or bare ```) fences anywhere in the text, keeping the inner
        content. Models often wrap JSON in a fenced block, sometimes after a prose preamble."""
        stripped = text.strip()
        fence = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)```", stripped)
        if fence and "{" in fence.group(1):
            return fence.group(1).strip()
        # leading-only fence with no closing fence (truncated)
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json|JSON)?\s*", "", stripped)
            stripped = re.sub(r"```\s*$", "", stripped)
        return stripped.strip()

    @staticmethod
    def _extract_json_object(text: str) -> str | None:
        """Return the first complete, brace-balanced JSON object in the text — robust to prose
        before/after the JSON and to nested braces inside string values. If the object is
        unterminated (model output got truncated), return from the first '{' to the end so the
        downstream repair pass can still attempt to close it."""
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return text[start:]

    def parse_json_result(self, text: str) -> HermesTaskResult:
        cleaned = self._strip_markdown_fences(text)
        data: dict[str, Any] | None = None
        # 1) direct parse
        try:
            parsed = json.loads(cleaned)
            data = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            data = None
        # 2) balanced-brace extraction (handles prose before/after, nested braces)
        if data is None:
            candidate = self._extract_json_object(cleaned)
            if candidate is None:
                raise ModelGatewayError("Hermes returned non-JSON output.")
            try:
                parsed = json.loads(candidate)
                data = parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError as exc:
                data = self._repair_json_candidate(candidate)
                if data is None:
                    raise ModelGatewayError(
                        f"Hermes returned malformed JSON output: {exc.msg} at char {exc.pos}."
                    ) from exc
        if not isinstance(data, dict):
            raise ModelGatewayError("Hermes JSON output must be an object.")
        # 穿透 final_response 封装:Hermes 有时返回 {"final_response": "{真实JSON}"},
        # 真正的 apps/resources/summary 被嵌套在 final_response 字符串里。
        # 如果顶层没有 apps/resources/summary,但 final_response 是 JSON 字符串,则解析它。
        if not any(k in data for k in ("apps", "resources", "summary", "trace")):
            inner = data.get("final_response") or data.get("response") or data.get("output") or data.get("result")
            if isinstance(inner, str) and inner.strip():
                inner_cleaned = self._strip_markdown_fences(inner)
                try:
                    inner_parsed = json.loads(inner_cleaned)
                    if isinstance(inner_parsed, dict) and any(k in inner_parsed for k in ("apps", "resources", "summary")):
                        data = inner_parsed
                except json.JSONDecodeError:
                    candidate = self._extract_json_object(inner_cleaned)
                    if candidate:
                        try:
                            inner_parsed = json.loads(candidate)
                            if isinstance(inner_parsed, dict) and any(k in inner_parsed for k in ("apps", "resources", "summary")):
                                data = inner_parsed
                        except json.JSONDecodeError:
                            pass
        result = HermesTaskResult.model_validate({**data, "raw_text": text})
        return result

    # Native demo app_types that have NO topic-specific visualization. They must never be
    # substituted for an interactive_demo request (which must be a custom.html simulation).
    _FORBIDDEN_DEMO_APP_TYPES = {"physics.work_energy_demo", "math.gradient_descent_demo"}

    @staticmethod
    def _short_topic(value: str, default: str = "互动演示") -> str:
        """Collapse a possibly-huge topic (e.g. a whole assistant reply pulled from context)
        into a clean short phrase so it never renders as a wall of text."""
        text = re.sub(r"<[^>]+>", " ", str(value or ""))
        text = re.sub(r"[*#`_>\[\]()$\\]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        segment = re.split(r"[，。！？!?,;；:：\n]", text)[0].strip()
        candidate = segment or text
        if not candidate or len(candidate) > 30:
            candidate = (candidate or "")[:24].strip()
        return candidate or default

    def enforce_interactive_demo_app_types(self, result: HermesTaskResult, plan: AgentPlan) -> HermesTaskResult:
        """When capability is interactive_demo, force any native-demo app the model wrongly
        chose (e.g. physics.work_energy_demo for a Bernoulli request) out of the result.

        Do not replace it here with a local topic-specific widget. The orchestrator owns the
        generic regeneration pass, which asks the model to produce a fresh topic-bound
        custom.html simulation under the universal interactive runtime contract.
        """
        capability = plan.payload.get("capability", "resource_bundle")
        expected_app_types = plan.payload.get("expected_app_types", []) or []
        if capability != "interactive_demo" or "custom.html" not in expected_app_types:
            return result
        filtered_apps: list[dict[str, Any]] = []
        rejected: list[str] = []
        for app in result.apps:
            app_type = str(app.get("app_type", ""))
            if app_type in self._FORBIDDEN_DEMO_APP_TYPES:
                rejected.append(app_type)
                continue
            filtered_apps.append(app)
        if rejected:
            trace = result.trace if isinstance(result.trace, list) else []
            trace.append(f"rejected_native_demo_app_type:{','.join(rejected)}")
            trace.append("needs_interactive_regeneration")
            result.trace = trace
            result.apps = filtered_apps
        return result

    @staticmethod
    def _json_repair_suffix(bad_output: str) -> str:
        """Corrective instruction appended when the model returned non-JSON / malformed JSON.
        Re-asking the SAME model to fix its own output is far more reliable than giving up, and
        avoids degrading to the simpler capability-contract fallback."""
        snippet = (bad_output or "").strip()[:600]
        return (
            "\n\n--- OUTPUT FORMAT CORRECTION ---\n"
            "Your previous response was REJECTED because it was not a single valid JSON object.\n"
            f"Previous response (truncated):\n{snippet}\n"
            "Now respond AGAIN with the SAME content, but as ONE strictly valid JSON object only.\n"
            "Hard rules: the very first character MUST be '{' and the very last character MUST be '}'. "
            "No prose, no explanation, no apology, no markdown code fences, nothing before or after the JSON. "
            "Escape every newline inside string values as \\n. Close every bracket and quote."
        )

    async def _invoke_hermes(
        self, command: str, prompt: str, provider: str, model: str, toolsets: str, skills: list[str],
        on_stderr_line: "Callable[[str], Awaitable[None]] | None" = None,
        run_id: str | None = None,
    ) -> tuple[int, str, str]:
        """启动 Hermes 子进程并等待完成。

        如果提供了 on_stderr_line，则实时流式读取 stderr 行并回调，
        用于向前端推送 Hermes 内部的进度事件（技能加载、工具调用、思考过程等）。
        """
        if self.is_cancelled(run_id):
            raise asyncio.CancelledError()

        args = [command]
        if provider:
            args.extend(["--provider", provider])
        if model:
            args.extend(["--model", model])
        if toolsets:
            args.extend(["--toolsets", toolsets])
        if skills:
            args.extend(["--skills", ",".join(skills)])
        args.extend(["-z", prompt])
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.settings.project_root),
            env=self.environment(),
        )
        if run_id:
            self._ACTIVE_PROCESSES[run_id] = process
            if self.is_cancelled(run_id):
                await _safe_terminate(process)
                raise asyncio.CancelledError()

        stderr_lines: list[str] = []

        async def _drain_stderr() -> None:
            """实时读取 stderr，逐行回调 + 收集。"""
            if not process.stderr:
                return
            async for line in process.stderr:
                decoded = line.decode("utf-8", errors="replace").rstrip("\n")
                if decoded:
                    stderr_lines.append(decoded)
                    if on_stderr_line:
                        try:
                            await on_stderr_line(decoded)
                        except Exception:
                            pass  # 回调失败不阻塞主流程

        try:
            if on_stderr_line:
                # Do not call communicate() while stderr is being drained: asyncio
                # allows only one reader per stream.
                stdout_task = asyncio.create_task(process.stdout.read() if process.stdout else asyncio.sleep(0, result=b""))
                stderr_task = asyncio.create_task(_drain_stderr())
                try:
                    await asyncio.wait_for(process.wait(), timeout=self.settings.hermes_task_timeout_seconds)
                    stdout = await stdout_task
                    await stderr_task
                except asyncio.TimeoutError as exc:
                    await _safe_terminate(process)
                    stdout_task.cancel()
                    stderr_task.cancel()
                    raise ModelGatewayError(
                        f"Hermes task timed out after {self.settings.hermes_task_timeout_seconds}s."
                    ) from exc
                stderr_text = "\n".join(stderr_lines)
            else:
                stdout, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=self.settings.hermes_task_timeout_seconds
                )
                stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
        except asyncio.CancelledError:
            await _safe_terminate(process)
            raise
        except asyncio.TimeoutError as exc:
            # Only reached by the non-streaming branch above. Guard against double-kill:
            # kill() raises ProcessLookupError if the process already exited, and
            # communicate() may race with the timeout cleanup.
            await _safe_terminate(process)
            raise ModelGatewayError(
                f"Hermes task timed out after {self.settings.hermes_task_timeout_seconds}s."
            ) from exc
        finally:
            if run_id and self._ACTIVE_PROCESSES.get(run_id) is process:
                self._ACTIVE_PROCESSES.pop(run_id, None)
        if self.is_cancelled(run_id):
            raise asyncio.CancelledError()
        return (
            process.returncode or 0,
            stdout.decode("utf-8", errors="replace").strip(),
            stderr_text,
        )

    # How many times to re-ask the SAME model to fix non-JSON output before moving on.
    JSON_REPAIR_RETRIES = 2

    async def run_resource_bundle(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any], run_id: str | None = None
    ) -> HermesTaskResult:
        use_sdk = self.use_sdk_backend()
        command = "" if use_sdk else self.command_path()
        image_artifacts = self._persist_uploaded_image_artifacts(context, run_id)
        carried_image_artifacts = rag_context.get("current_image_artifacts") if isinstance(rag_context.get("current_image_artifacts"), list) else []
        if carried_image_artifacts:
            image_artifacts = [*carried_image_artifacts, *image_artifacts]
        image_analysis = ""
        if self.settings.python_vision_fallback_enabled:
            image_analysis = await self.pre_analyze_uploaded_images(context, run_id=run_id)
        if self._has_uploaded_images(context) and self.settings.python_vision_fallback_enabled and not self._vision_analysis_is_reliable(image_analysis):
            failure = self._vision_failure_text()
            return HermesTaskResult(
                summary=failure,
                trace=["vision.failed_closed: 图片 OCR 未达到可靠阈值，已禁止生成猜测性报告"],
                capability="image_analysis_failed",
                text_response=failure,
                raw_text=failure,
            )
        base_prompt = self.build_resource_bundle_prompt(
            plan,
            context,
            {**rag_context, "current_image_artifacts": image_artifacts},
            image_analysis=image_analysis,
        )
        toolsets = self.settings.hermes_toolsets.strip()
        skills = self.skills_for_plan(plan, context)
        fallback_trace: list[str] = []
        last_error: ModelGatewayError | None = None
        attempts = self.provider_attempts()
        for index, (provider, model) in enumerate(attempts):
            has_next = index < len(attempts) - 1
            prompt = base_prompt
            # Inner loop: re-ask THIS provider to emit valid JSON before considering any fallback.
            for repair_round in range(self.JSON_REPAIR_RETRIES + 1):
                if self.is_cancelled(run_id):
                    raise asyncio.CancelledError()
                if use_sdk:
                    sdk_prompt = self.build_sdk_user_message(prompt, image_artifacts)
                    returncode, output, error = await self._invoke_hermes_sdk(
                        sdk_prompt,
                        provider,
                        model,
                        run_id=run_id,
                        persist_user_message=prompt,
                        student_id=context.student_id, conversation_id=context.conversation_id,
                    )
                else:
                    returncode, output, error = await self._invoke_hermes(
                        command, prompt, provider, model, toolsets, skills, run_id=run_id
                    )
                combined = error or output or "no output"
                if returncode != 0:
                    last_error = ModelGatewayError(f"Hermes exited {returncode}: {combined}")
                    if has_next and self.looks_like_provider_failure(combined):
                        fallback_trace.append(f"hermes_provider_fallback:{provider}->next:{combined[:160]}")
                    break
                if not output:
                    last_error = ModelGatewayError(f"Hermes returned empty output: {error}")
                    if has_next and self.looks_like_provider_failure(combined):
                        fallback_trace.append(f"hermes_provider_fallback:{provider}->next:{combined[:160]}")
                    break
                try:
                    result = self.parse_json_result(output)
                    result = self.enforce_interactive_demo_app_types(result, plan)
                    if fallback_trace:
                        result.trace = [*fallback_trace, *result.trace]
                    return result
                except ModelGatewayError as exc:
                    last_error = exc
                    # A real provider/quota failure should switch providers, not repair-retry.
                    if self.looks_like_provider_failure(output):
                        if has_next:
                            fallback_trace.append(f"hermes_provider_fallback:{provider}->next:{output[:160]}")
                        break
                    # Non-JSON / malformed: re-ask the SAME model with a strict correction.
                    if repair_round < self.JSON_REPAIR_RETRIES:
                        fallback_trace.append(f"hermes_json_repair_retry:{provider}#{repair_round + 1}:{str(exc)[:120]}")
                        prompt = base_prompt + self._json_repair_suffix(output)
                        continue
                    # Exhausted repair retries for this provider.
                    break
        raise last_error or ModelGatewayError("Hermes task failed.")

    # ── Unified Hermes Prompt ──────────────────────────────────────────────

    @staticmethod
    def _decode_image_attachment(img: str) -> tuple[bytes, str]:
        if img.startswith("data:image/"):
            header, b64_data = img.split(",", 1)
            mime = header.split(";")[0].replace("data:", "")
            ext = mime.split("/")[-1] if "/" in mime else "png"
        else:
            b64_data = img
            ext = "png"
        b64_data = b64_data.replace("-", "+").replace("_", "/")
        padding = 4 - len(b64_data) % 4
        if padding != 4:
            b64_data += "=" * padding
        return base64.b64decode(b64_data), ext

    def _persist_text_artifact(
        self,
        *,
        context: TutorTurnContext,
        run_id: str | None,
        kind: str,
        title: str,
        text: str,
    ) -> dict[str, Any] | None:
        try:
            from app.database.store import get_store

            artifact_id = f"artifact_{uuid4().hex[:12]}"
            object_key = artifact_object_key(kind=kind, artifact_id=artifact_id, filename=f"{artifact_id}.txt")
            stored = ObjectStorage().put_bytes(
                object_key=object_key,
                data=text.encode("utf-8"),
                content_type="text/plain; charset=utf-8",
            )
            return get_store().save_artifact(
                artifact_id=artifact_id,
                kind=kind,
                object_key=stored.object_key,
                content_type=stored.content_type,
                sha256=stored.sha256,
                size_bytes=stored.size_bytes,
                title=title,
                source_run_id=run_id,
                student_id=context.student_id,
                course_id=context.course_id,
                conversation_id=context.conversation_id,
                metadata={"source": "hermes_task_executor"},
            )
        except Exception as exc:
            _get_logger().warning("artifact_text_persist_failed: %s: %s", type(exc).__name__, exc)
            return None

    def _persist_uploaded_image_artifacts(
        self,
        context: TutorTurnContext,
        run_id: str | None,
    ) -> list[dict[str, Any]]:
        image_data_list = (getattr(context, "image_data", None) or [])[:MAX_IMAGE_ATTACHMENTS]
        if not image_data_list:
            return []
        artifacts: list[dict[str, Any]] = []
        try:
            from app.database.store import get_store

            store = get_store()
            storage = ObjectStorage()
            for index, img in enumerate(image_data_list, 1):
                try:
                    img_bytes, ext = self._decode_image_attachment(img)
                    if len(img_bytes) < MIN_IMAGE_ATTACHMENT_BYTES or len(img_bytes) > MAX_IMAGE_ATTACHMENT_BYTES:
                        continue
                    original_ext = ext.lower()
                    img_bytes, ext = self._normalize_image_bytes_for_artifact(img_bytes)
                    content_type = "image/jpeg"
                    artifact_id = f"artifact_{uuid4().hex[:12]}"
                    object_key = artifact_object_key(kind="source.image", artifact_id=artifact_id, filename=f"upload-{index}.{ext}")
                    stored = storage.put_bytes(object_key=object_key, data=img_bytes, content_type=content_type)
                    metadata = {
                        "index": index,
                        "source": "chat_upload",
                        "public_url": stored.public_url,
                        "normalized": "rgb_jpeg",
                        "original_extension": original_ext,
                    }
                    if storage.status().get("backend") == "local_development":
                        metadata["dev_file_path"] = storage.local_file_path(stored.object_key)
                    artifacts.append(
                        store.save_artifact(
                            artifact_id=artifact_id,
                            kind="source.image",
                            object_key=stored.object_key,
                            content_type=stored.content_type,
                            sha256=stored.sha256,
                            size_bytes=stored.size_bytes,
                            title=f"用户上传图片 {index}",
                            source_run_id=run_id,
                            student_id=context.student_id,
                            course_id=context.course_id,
                            conversation_id=context.conversation_id,
                            metadata=metadata,
                        )
                    )
                except Exception as exc:
                    _get_logger().warning("artifact_image_persist_failed[%d]: %s: %s", index, type(exc).__name__, exc)
        except Exception as exc:
            _get_logger().warning("artifact_image_store_unavailable: %s: %s", type(exc).__name__, exc)
        return artifacts

    def _zoom_tiles_for_vision(self, image_data: list[str]) -> tuple[list[str], list[str]]:
        """Create overlapping zoomed crops for small text / corner details.

        Pillow is optional at runtime. When available, this produces real cropped
        and enlarged image tiles; otherwise the caller still performs repeated
        full-image vision passes.
        """
        try:
            from PIL import Image, ImageOps
        except Exception as exc:
            _get_logger().warning("image_pre_analysis: Pillow unavailable, using full-image vision only (%s)", exc)
            return [], []

        zoom_images: list[str] = []
        notes: list[str] = []
        max_tiles_total = 12
        max_source_images = min(len(image_data), 3)
        for image_index, img in enumerate(image_data[:max_source_images], 1):
            try:
                img_bytes, _ext = self._decode_image_attachment(img)
                if len(img_bytes) < MIN_IMAGE_ATTACHMENT_BYTES or len(img_bytes) > MAX_IMAGE_ATTACHMENT_BYTES:
                    continue
                source = Image.open(io.BytesIO(img_bytes))
                source = ImageOps.exif_transpose(source).convert("RGB")
                width, height = source.size
                cols = 3 if width / max(height, 1) > 1.45 else 2
                rows = 3 if height / max(width, 1) > 1.35 else 2
                if width < 900:
                    cols = 1
                if height < 900:
                    rows = 1
                overlap = 0.10
                tile_width = width / cols
                tile_height = height / rows
                for row in range(rows):
                    for col in range(cols):
                        if len(zoom_images) >= max_tiles_total:
                            return zoom_images, notes
                        left = max(0, int(col * tile_width - tile_width * overlap))
                        top = max(0, int(row * tile_height - tile_height * overlap))
                        right = min(width, int((col + 1) * tile_width + tile_width * overlap))
                        bottom = min(height, int((row + 1) * tile_height + tile_height * overlap))
                        crop = source.crop((left, top, right, bottom))
                        long_edge = max(crop.size)
                        scale = min(2.4, max(1.0, 1800 / max(long_edge, 1)))
                        new_size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
                        if new_size != crop.size:
                            crop = crop.resize(new_size, Image.Resampling.LANCZOS)
                        if max(crop.size) > 2200:
                            shrink = 2200 / max(crop.size)
                            crop = crop.resize((max(1, int(crop.width * shrink)), max(1, int(crop.height * shrink))), Image.Resampling.LANCZOS)
                        buffer = io.BytesIO()
                        crop.save(buffer, format="PNG", optimize=True)
                        zoom_images.append(f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}")
                        notes.append(
                            f"局部图 {len(zoom_images)}: 原图{image_index} 第{row + 1}行第{col + 1}列，"
                            f"裁剪范围 x={left}-{right}, y={top}-{bottom}，已放大用于小字/OCR复核"
                        )
            except Exception as exc:
                _get_logger().warning("image_pre_analysis: failed to build zoom tiles for image %d (%s: %s)", image_index, type(exc).__name__, exc)
                continue
        return zoom_images, notes

    async def pre_analyze_uploaded_images(
        self,
        context: TutorTurnContext,
        on_trace_step: "Callable[[str, str, str], Awaitable[None]] | None" = None,
        run_id: str | None = None,
    ) -> str:
        """Run a direct multimodal OCR pass before Hermes.

        Hermes can use file/vision tools, but the web product should not depend on
        the external agent successfully discovering those tools before it can read
        an uploaded exam image. This lightweight pass turns image pixels into
        grounded text that the unified prompt can consume deterministically.
        """
        raw_image_data = (getattr(context, "image_data", None) or [])[:MAX_IMAGE_ATTACHMENTS]
        if not raw_image_data:
            return ""

        async def emit_trace(step_name: str, status: str, detail: str) -> None:
            if not on_trace_step:
                return
            try:
                await on_trace_step(step_name, status, detail)
            except Exception:
                pass

        cache_key = self._image_cache_key(raw_image_data)
        cached = self._VISION_CACHE.get(cache_key)
        if cached:
            await emit_trace("vision.cache", "running", "已找到同图历史 OCR；本轮仍会重新执行 Vision，失败时才兜底复用")
        image_data, normalize_notes = self._normalize_images_for_vision(raw_image_data)
        client = GeminiClient()

        async def vision_round(round_name: str, user_prompt: str, images: list[str], limit: int = 8000) -> str:
            messages = [
                ChatMessage(
                    role="system",
                    content=(
                        "你是 LearnForge 的图片题面识别助手。请只根据上传图片做 OCR 和题目结构识别，"
                        "不要凭文件名猜测。必须保留题号、选项、段落、空格、表格、图注和所有可见英文原文。"
                        "如果是英语试卷，请先转写原文，再用中文标注题型、题目要求和可解答的信息。"
                        "如果有局部模糊，请标记为【无法辨认】。"
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=f"【{round_name}】\n用户原始请求：{context.message}\n\n{user_prompt}",
                    images=images,
                ),
            ]
            response = await client.complete(messages, stream=False)
            text = client.extract_assistant_text(response).strip()
            if not text:
                raise ModelGatewayError(f"{round_name} returned empty vision analysis.")
            return self._truncate_text(text, limit)

        try:
            await emit_trace(
                "vision.normalize",
                "completed",
                "；".join(normalize_notes[:3]) if normalize_notes else "图片已准备为 Vision 输入",
            )
            await emit_trace("vision.overall_ocr", "running", "正在对标准化后的整张图片做 OCR 与版面识别")
            first_pass = await vision_round(
                "第一轮：整体 OCR 和版面识别",
                (
                    "注意：后端已把原始上传图转换为标准 RGB JPEG，以避免手机 HDR/P3 图片被模型拒绝。\n"
                    "请从整张图片全局识别：\n"
                    "1. 图片类型、页眉页脚、题号范围、题型\n"
                    "2. 按从上到下、从左到右顺序完整转写 OCR 原文\n"
                    "3. 保留英文大小写、标点、选项 A/B/C/D、空格/横线/括号\n"
                    "4. 列出你看不清、字体很小、疑似截断、需要放大复核的区域"
                ),
                image_data,
            )
            await emit_trace("vision.overall_ocr", "completed", f"整体 OCR 完成，提取 {len(first_pass)} 字符")

            zoom_images, zoom_notes = self._zoom_tiles_for_vision(raw_image_data)
            await emit_trace(
                "vision.zoom_tiles",
                "running",
                f"正在裁切并放大局部区域复核小字，图块数：{len(zoom_images) or len(image_data)}",
            )
            if zoom_images:
                second_images = zoom_images
                zoom_intro = "你现在看到的是后端从原图切出的重叠局部放大图块，顺序如下：\n" + "\n".join(zoom_notes)
            else:
                second_images = image_data
                zoom_intro = "当前运行环境没有生成真实裁切图块。请在同一原图中主动放大关注第一轮列出的不确定区域，逐块复核。"

            second_pass = await vision_round(
                "第二轮：局部放大复核和纠错",
                (
                    f"{zoom_intro}\n\n"
                    "第一轮识别结果如下，请重点复核其中所有【无法辨认】、小字、选项、题干尾部、图片边缘和换行处：\n"
                    f"{first_pass}\n\n"
                    "请输出：\n"
                    "1. 每个局部区域新识别到的文字\n"
                    "2. 对第一轮 OCR 的纠错表\n"
                    "3. 仍然无法确认的字符/单词/选项"
                ),
                second_images,
            )
            await emit_trace("vision.zoom_tiles", "completed", f"局部放大复核完成，提取 {len(second_pass)} 字符")

            await emit_trace("vision.final_merge", "running", "正在回看原图并合并 OCR、纠错和不确定项")
            final_pass = await vision_round(
                "第三轮：原图回看合并校对",
                (
                    "请再次回看原图，并结合前两轮结果，输出最终可用于讲题的题面材料。\n\n"
                    f"第一轮整体 OCR：\n{first_pass}\n\n"
                    f"第二轮局部放大复核：\n{second_pass}\n\n"
                    "最终输出必须包含：\n"
                    "1. 最终 OCR 原文（尽可能完整）\n"
                    "2. 题目要求/题型/选项/空格\n"
                    "3. 可以开始讲解的题目列表\n"
                    "4. 仍不确定的地方和原因\n"
                    "不要编造看不见的文字。"
                ),
                image_data,
                limit=10000,
            )
            await emit_trace("vision.final_merge", "completed", f"最终题面合并完成，提取 {len(final_pass)} 字符")

            result = self._truncate_text(
                (
                    "## 多轮 Vision 题面识别结果\n\n"
                    "### 第零步：图片标准化\n"
                    f"{chr(10).join(normalize_notes) if normalize_notes else '已使用原始图片。'}\n\n"
                    "### 第一轮：整体 OCR\n"
                    f"{first_pass}\n\n"
                    "### 第二轮：局部放大复核\n"
                    f"{second_pass}\n\n"
                    "### 第三轮：合并后的最终题面\n"
                    f"{final_pass}"
                ),
                14000,
            )
            if self._vision_analysis_is_reliable(result):
                self._VISION_CACHE[cache_key] = result
                self._persist_text_artifact(
                    context=context,
                    run_id=run_id,
                    kind="source.vision_text",
                    title="多轮 Vision 题面识别结果",
                    text=result,
                )
            return result
        except (ProviderBlocked, ModelGatewayError) as exc:
            _get_logger().warning("image_pre_analysis: skipped (%s)", exc)
            await emit_trace("vision.final_merge", "failed", f"Vision 调用失败：{str(exc)[:160]}")
            if cached:
                await emit_trace("vision.cache_fallback", "completed", "本轮 Vision 失败，已复用同一张图片上次成功的多轮 OCR 结果")
                return cached
        except Exception as exc:
            _get_logger().warning("image_pre_analysis: unexpected failure (%s: %s)", type(exc).__name__, exc)
            await emit_trace("vision.final_merge", "failed", f"Vision 识别异常：{type(exc).__name__}")
            if cached:
                await emit_trace("vision.cache_fallback", "completed", "本轮 Vision 异常，已复用同一张图片上次成功的多轮 OCR 结果")
                return cached
        return ""

    def build_unified_prompt(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any], image_analysis: str = ""
    ) -> str:
        """构建真·统一 prompt —— 包含 ALL 能力框架，Hermes 自主选择。

        不依赖 Python 侧的 detect_capability() 分类。
        所有场景的生成指导都在此 prompt 中，Hermes 自己读取并决定应用哪个。
        """
        image_file_paths = [] if self.use_sdk_backend() else self._save_image_attachments(context)
        image_artifacts = rag_context.get("current_image_artifacts") if isinstance(rag_context.get("current_image_artifacts"), list) else []
        artifact_context = rag_context.get("artifact_context") if isinstance(rag_context.get("artifact_context"), dict) else None
        priority_context = bool(image_file_paths or image_artifacts or artifact_context)
        skill_catalog = HermesSkillSync().build_skill_catalog()

        parts: list[str] = []

        # ── SYSTEM IDENTITY ──
        parts.append(
            "你是 LearnForge 的统一执行代理（Unified Execution Agent）。"
            "你全权负责识别用户意图、维护上下文一致性、选择最合适的技能、实时生成高质量产物。"
            "Python API 不再替你做产品意图路由；你是唯一的核心 Agent 决策层。"
            "后端只负责会话/SSE/存储/画布发布/产物验收。"
        )

        # ── Pre-decided capability (background task after user consent) ──
        plan_capability = str(plan.payload.get("capability") or "")
        route_source = str(plan.payload.get("route_source") or "")
        pre_decided = (
            plan_capability
            and plan_capability != "hermes_decides"
            and plan_capability != "answer_only"
            and route_source in ("user_approved",)
        )
        if pre_decided:
            parts.append(f"""
## 🎯 本轮 Capability 已由用户确认 —— 勿重新决策！

用户已在前端点击「确认生成」按钮。你的 **唯一任务** 是生成 **{plan_capability}** 产物。

- capability 已锁定为 `{plan_capability}`，不可更改为 answer_only 或其他任何类型
- 主题：**{plan.payload.get("topic", context.message)}**
- 必须输出 {plan_capability} 对应的完整产物（HTML / JSON / apps / resources）
- 禁止以「没有明确产物指令」「用户只是提问」等理由拒绝生成
- 直接跳到下方对应场景（场景 {plan_capability}）开始生成，忽略意图识别表
""")
        else:
            parts.append("""
## 🧭 Hermes 原生路由与 Skill 合同

你必须先基于当前用户消息、最近对话、学生画像、记忆、最近画布和资源，自主决定唯一 `capability`，然后执行对应 Skill。

允许的核心 capability（按优先级排序）:
- `answer_only` ⬅️ **默认！**: 直接文本回答，不创建任何画布产物。这是所有非明确产物请求的默认选择。
- `video_search`: 实时搜索/推荐视频；返回 topic，后端会按你的 topic 调用视频搜索工具。
- `ppt`: 使用 guizang-ppt-skill / ppt-skill 实时生成网页 PPT deck。
- `image_explanation`: 使用 image-generation-skill 规划图片生成；后端会调用 Gemini 图片接口生成真实图片。
- `interactive_demo`: 使用 custom-html-app-skill 实时生成动态/可交互模型。
- `detailed_analysis`: 使用 detailed-analysis-skill 生成题目/作业/图片分析 HTML。严格限定：只有用户上传了具体题目图片并明确要求讲解时才用。
- `custom_infographic`, `mindmap`, `quiz`, `code_lab`, `video_script`, `notes`, `learning_path`, `resource_bundle`: 按对应 Skill 实时生成。

	硬规则:
	- **默认 answer_only**：你没有收到明确产物指令 → 纯文本。绝不生成 HTML/apps/resources。这是最重要的规则。
	- 用户明确要搜索视频、PPT、图片、动态/可交互模型时，才选择对应 capability 并调用对应 Skill 实时生成。
	- 用户只是提问、确认记忆/上下文、询问「你还记得/前面聊了什么/刚才说了什么」、问候、闲聊、要求解释一个概念但没有要求生成产物时，必须选择 `answer_only`。
	- **概念解释（"什么是XXX"、"解释XXX"、"为什么XXX"）→ answer_only，不是 detailed_analysis。**
	- 禁止模板糊弄、写死内容、伪造搜索结果、跨类型降级或把失败产物说成成功。
	- PPT 不能变成交互模型；交互模型不能变成 HTML 报告；直接问答不能变成页面；图片生成不能只给文字描述。
	- 如果你选择 `answer_only`，只返回文本；不要输出 HTML、apps 或 resources。
	- 如果你选择产物类 capability，最终 JSON 必须包含 `capability`、`topic`、`summary`、`apps`、`resources`、`text_response`。
	- 生成失败时明确失败原因，不要给 placeholder/fallback/template。
""")

        # ── AVAILABLE SKILLS ──
        parts.append(f"\n## 📚 可用技能\n{skill_catalog}")

        # ── USER CONTEXT ──
        parts.append(f"\n## 👤 用户上下文\n- 学生ID: {context.student_id}\n- 课程ID: {context.course_id}")
        if context.profile:
            parts.append(f"\n## 🧠 学生画像与掌握度\n{self._truncate_text(json.dumps(context.profile, ensure_ascii=False), 1200)}")
        if context.student_memories:
            parts.append(f"\n### 历史记忆(弱点/掌握/偏好)\n{json.dumps(context.student_memories[-12:], ensure_ascii=False)}")
        parts.append(f"- 用户消息: {context.message}")
        if context.last_assistant_answer:
            # Phase B：priority_context 轮（图片/artifact）保留压缩版历史，避免"一上图就失忆"。
            # 图片仍是最高优先级（见下方图片段），但 Hermes 不应完全忘记刚才聊了什么。
            answer_limit = 500 if priority_context else 2000
            parts.append(f"- 上轮回复（可能作为上下文参考）: {self._truncate_text(context.last_assistant_answer, answer_limit)}")
        if context.recent_messages:
            msg_window = context.recent_messages[-4:] if priority_context else context.recent_messages[-10:]
            text_lim = 400 if priority_context else 1200
            parts.append(f"- 近期对话: {json.dumps([self._compact_item(m, text_limit=text_lim) for m in msg_window], ensure_ascii=False)}")
        if artifact_context:
            parts.append(
                "\n## 🧷 当前绑定 Artifact 上下文（优先级高于课程 RAG/历史对话）\n"
                f"- artifact_id: {artifact_context.get('artifact_id')}\n"
                f"- kind: {artifact_context.get('kind')}\n"
                f"- title: {artifact_context.get('title')}\n"
                "请把这个 artifact 视为用户当前追问的唯一主对象；禁止用课程资料或历史画布替代它。\n"
                f"{self._truncate_text(str(artifact_context.get('content') or ''), 12000)}"
            )
        if rag_context.get("context") and not priority_context:
            parts.append(f"\n## 📖 课程资料\n{self._truncate_text(rag_context.get('context', ''), 6000)}")

        # ── IMAGES ──
        if image_file_paths or image_artifacts:
            parts.append(f"\n## 🖼️ 用户上传图片 ({len(image_file_paths) or len(image_artifacts)} 张)")
            parts.append("本轮图片是最高优先级主上下文。必须基于图片/图片 artifact 理解题面，忽略冲突的历史对话、旧画布和课程 RAG。")
            if image_artifacts:
                parts.append("### 对象存储图片 Artifact")
                for artifact in image_artifacts:
                    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
                    public_url = metadata.get("public_url")
                    dev_file_path = metadata.get("dev_file_path")
                    content_url = f"{self.settings.api_public_base_url.rstrip('/')}/api/artifacts/{artifact.get('artifact_id')}/content"
                    parts.append(
                        "- "
                        f"artifact_id={artifact.get('artifact_id')} "
                        f"object_key={artifact.get('object_key')} "
                        f"content_url={content_url} "
                        f"content_type={artifact.get('content_type')} "
                        f"public_url={public_url or 'not_configured'} "
                        f"dev_file_path={dev_file_path or 'not_available'}"
                    )
                parts.append(
                    "Hermes SDK/Harmony 原生多模态必须直接读取以上图片 artifact。"
                    "生产环境优先使用 public_url/content_url；本地开发可使用 dev_file_path。"
                    "不要根据文件名猜题面。"
                )
                parts.append(
                    "硬性执行协议：在生成任何讲解或 HTML 前，必须先打开图片 artifact 并完成 OCR/视觉核验。"
                    "如果图片是英语试卷，报告中必须包含「题面 OCR 核验」小节，逐字保留可见英文标题/题型/题号/选项/词库，"
                    "例如 Reading Comprehension、Section A、Directions、题号 26-35 等可见信息。"
                    "如果这些内容无法可靠读取，必须输出图片无法可靠识别，不允许编造数学/物理/课程 RAG 内容。"
                )
            if image_file_paths:
                parts.append("使用 **file** 工具读取图片 → **vision** 分析。精确提取所有文字、数字、公式、图表。")
            for i, img_path in enumerate(image_file_paths, 1):
                parts.append(f"图片 {i}: `{img_path}`")
            if image_analysis:
                parts.append(
                    "\n## 🔎 Python Vision fallback 预识别内容（仅兜底，不是题面真相）\n"
                    "下面内容来自后端 fallback OCR。它只能辅助定位，不能覆盖你对原图/artifact 的直接读取；如果冲突，以原图为准。\n"
                    "硬性优先级：本轮上传图片 > API Vision 识别结果 > 用户当前消息 > 课程资料/RAG > 历史对话/上轮回答。"
                    "如果历史对话、RAG 或上轮回答与图片内容冲突，必须忽略冲突内容，禁止生成与图片无关的题解。\n"
                    f"{image_analysis}"
                )
            else:
                parts.append("如果无法读取图片 artifact/vision 工具，不要根据附件文件名猜题目；请明确说明图片无法识别。")

        # ── 意图识别指南 ──
        parts.append("""
## 🧭 意图识别

**🚨 最重要规则：默认一律使用 `answer_only`（纯文本回答）。**
你是导师，不是报告生成器。绝大多数学生消息都是提问、问候、闲聊、确认理解——这些都应该得到一个直接的文本回答，而不是 HTML 页面或画布产物。

只有用户**明确要求**以下产物时才生成对应内容，否则全部走 `answer_only`：

| 场景 | 用户必须明确说 | 输出格式 |
|------|--------------|---------|
| **默认：纯文本回答** | 所有其他情况。问候、闲聊、概念解释、知识问答、记忆确认、"XXX是什么"、"解释XXX"、"为什么XXX"、"能不能XXX"、"怎么XXX" | **纯文本 / answer_only** |
| **PPT/幻灯片** | "制作PPT"、"幻灯片"、"课件"、"做个演示"、"生成PPT" | JSON → custom.html |
| **视频搜索** | "搜索视频"、"找视频"、"B站搜XXX" | JSON → video_search |
| **可交互模型/演示** | "生成一个...模型"、"交互式演示"、"动态模拟"、"3D"、"做动画" | JSON → custom.html |
| **思维导图** | "思维导图"、"脑图" | JSON → mindmap.concept |
| **练习题/测验** | "出题"、"测试"、"练习题"、"给我出几道题" | JSON → quiz.practice |
| **代码实验** | "编程"、"写代码"、"代码演示" | JSON → code.lab |
| **生成图片** | "画图"、"生成图片"、"示意图" | JSON → image.explanation |
| **题目讲解/详细分析** | 上传了题目图片 + "讲解"、"分析这道题" | HTML 报告 |
| **笔记整理** | "记笔记"、"整理笔记" | JSON → notes.session |

### 🔑 关键判断规则

1. **DEFAULT = answer_only**：你没有收到明确产物指令 → 纯文本回答。绝不上传 HTML/apps/resources。
2. **概念解释 ≠ 报告**："什么是机器学习"、"解释一下快速排序"、"微积分怎么理解" — 这些都是 answer_only，**不是** detailed_analysis。
3. **detailed_analysis 严格限定**：只用于用户上传了具体题目图片/文件 + 明确要求讲解/分析。没有上传图片的纯文字提问不能变成 HTML 报告。
4. **记忆确认 → answer_only**："你还记得吗"、"我之前说过什么"、"我的弱点是什么" → 纯文本回答。
5. **PPT ≠ 普通解释**：只有用户说「做PPT/幻灯片/课件/deck」才是 PPT。解释一个概念不是 PPT。
6. **宁可少生成，不要多生成**：模棱两可时，选 answer_only。用户真的需要产物会再明确说。
7. **禁止跨类型降级**：如果用户要求 PPT 但你做不出来，不要降级为 HTML 报告。诚实说明失败。

### 具体示例

| 用户消息 | ✅ 正确 capability | ❌ 错误 |
|---------|-------------------|--------|
| "你好" | answer_only | detailed_analysis |
| "什么是傅里叶变换" | answer_only | detailed_analysis / ppt |
| "解释一下牛顿第二定律" | answer_only | interactive_demo |
| "你觉得我数学哪里弱" | answer_only | detailed_analysis |
| "帮我做个傅里叶变换的PPT" | ppt | answer_only |
| "生成一个单摆运动的交互演示" | interactive_demo | answer_only |
| [上传数学题图片] "帮我看看这道题" | detailed_analysis | answer_only |
| "帮我搜一下B站上的微积分视频" | video_search | answer_only |
| "画一个细胞结构示意图" | image_explanation | answer_only |
| "帮我出5道一元二次方程练习题" | quiz | answer_only |
	""")

        # ── 场景 A: 详细分析/题目讲解 ──
        parts.append("""
## 🔬 场景 A: 题目讲解/详细分析

使用 **detailed-analysis-skill**。遵循五步法：
1. **读题** — 完整呈现题目原文，提取已知条件、未知量
2. **析题** — 分析考察的知识点、解题突破口、思路选择
3. **解题** — 逐步展示完整解答过程，数学公式用 KaTeX
4. **品题** — 总结核心方法、易错点、可迁移技巧
5. **练题** — 设计 1-2 道变式练习题并给出简略解答

### 学科特定规则
- **数学**: 所有公式用 KaTeX，展示代数变形，注意分类讨论
- **物理**: 先列已知条件和所求量，明确物理模型，单位换算，量纲检查
- **化学**: 写出配平方程式，摩尔换算，反应条件
- **英语**: 阅读理解→分析文章结构/定位关键句/解释选项；语法→解释规则+例句；翻译→句子结构分析+译法比较；作文→框架+范文
- **语文**: 阅读→主旨/手法/感情；文言→逐字翻译/实词虚词；作文→审题/结构/素材
- **历史/地理/政治**: 历史→时间线/因果关系；地理→图表分析/区位因素；政治→知识点定位/理论联系实际

### HTML 设计原则
- 必须包含 `<!DOCTYPE html>` 和完整 `<head>`/`<body>`
- 引入 KaTeX CDN 渲染公式
- 美观现代设计：渐变背景、卡片布局、合理色彩编码
- 色彩建议：数学蓝紫、物理深蓝、化学绿、英语暖橙、语文棕红、文科青绿
- 移动端响应式：viewport meta + 相对单位
- 可加入折叠面板、tab 切换等交互

### 输出格式
以 `---HERMES_HTML_OUTPUT---` 开头，后跟完整 HTML。
HTML 之前可加简短 Markdown 摘要（`## 📝 分析完成` 开头）。
""")

        # ── 场景 B: 可交互模型/动态演示 ──
        parts.append("""
## 🎮 场景 B: 可交互模型/动态演示

使用 **custom-html-app-skill** + **app-generation-skill**。
这是最高质量要求的场景 —— 用户期望一个沉浸式、全功能的交互式可视化。

### 架构要求
- 内部工作流: Demo Architect(场景/状态/控制设计) → Graphics Engineer(Canvas/SVG/WebGL实现) → Interaction Engineer(事件绑定/控制验证) → QA Verifier(最终检查)
- 框架式架构: state对象 + render()函数 + 组件section + SVG/Canvas + 委托事件处理
- **禁止使用** Vue/React 模板语法({{ }}, JSX, SFC)

### 强制要求 (每一项都必须满足)
1. ⬜ 至少一个 `<canvas>` 或 `<svg>` 元素 + 对应 `<script>` 块
2. ⬜ 渲染**可见对象**(方块/曲线/粒子/柱状图/箭头/形状) — 不只是文字卡片
3. ⬜ `requestAnimationFrame` 或 `setInterval` 动画循环
4. ⬜ 交互控件(滑块/按钮/拖拽)产生可见效果，每个按钮有 `data-action` 属性 + 委托 click 监听
5. ⬜ 实时数值显示(位置/速度/能量等)随动画更新
6. ⬜ 动量/碰撞: 两个可见方块+速度箭头，m1v1+m2v2=const，显示碰撞前后动量和动能
7. ⬜ 函数/数学: 实际坐标轴+网格线+函数曲线，可拖拽观测点，显示导数/切线/积分面积
8. ⬜ 自检: 无{{ }}模板、无死控件、无空白舞台、无与主题无关的内容

### 空间/3D 专题
- 分体布局: 固定控制侧面板 + 独立模型舞台
- 拖拽轨道/滚轮缩放/重置/实时状态读数
- 魔方: 完整3x3x3，27个cubie，U/U'/D/D'/F/F'/B/B'/R/R'/L/L'控制，scramble/reset/undo

### 严格禁止
- 用 physics.work_energy_demo 或 math.gradient_descent_demo 代替 custom.html
- 用通用滑块替代主题特定的可视化
- 把伯努利/流体请求变成动能定理/滑块轨道demo

### 输出格式: JSON
```json
{"capability": "interactive_demo", "topic": "具体主题", "mode": "synchronous", "apps": [{"app_type": "custom.html", "title": "具体标题", "payload": {"html": "完整HTML"}}], "text_response": "简短说明"}
```
""")

        # ── 场景 C: PPT ──
        parts.append("""
## 📊 场景 C: PPT/幻灯片

使用 **guizang-ppt-skill**。创建完整单文件 HTML 横滑 deck。
- 二选一风格: A) 电子杂志×电子墨水 (叙事/个人) B) 瑞士国际主义 (产品/数据/技术)
- 16:9或21:9响应式，键盘/触摸导航，适合全屏iframe
- 可见中文slide文案，强排版层次，页码，节奏分段
- 输出: JSON → app_type: "custom.html", payload.html: 完整deck HTML
""")

        # ── 场景 D: 其他资源类型 ──
        parts.append("""
## 🧩 场景 D: 思维导图/测验/代码/图片/笔记

根据用户需要选择对应 app_type:
- **思维导图**: `mindmap.concept`
- **测验**: `quiz.practice`
- **代码实验**: `code.lab`
- **图片生成**: `image.explanation` (topic + teaching_goal + visual_brief + provider_alias)
- **视频脚本**: `video.script`
- **笔记**: `notes.session`
- **学习路径**: `learning.path`

每个 app 都要有 content-specific 的 title，禁止使用「测试题」「学习资源」等泛化标题。
""")

        # ── 通用规则 ──
        parts.append("""
## 📋 通用规则

1. **自主判断**：你是唯一的决策者，没有外部告诉你「这是什么场景」
2. **内容驱动标题**：所有 app/resource 标题必须来自实际内容
3. **中文优先**：所有面向用户的文案必须是中文
4. **禁止泛化/跑题**：不要把一个主题强行解读成另一个概念
5. **不写文件**：API 服务器负责持久化和渲染
6. **图片优先**：如果用户上传了图片，图片中的信息是核心

## 📤 输出格式

	### 纯文本 (聊天/简单问答)
	直接回复，不加任何标记；或者返回 JSON：`{"capability":"answer_only","topic":"...","summary":"...","apps":[],"resources":[],"text_response":"..."}`。
	无论使用哪种形式，都禁止包含 HTML、apps、resources、artifact、canvas 或报告字段。

### HTML 报告 (题目讲解)
```
---HERMES_HTML_OUTPUT---
<!DOCTYPE html>
<html>...</html>
```

### JSON 产物 (App/资源)
```json
{"capability": "...", "topic": "具体主题", "mode": "synchronous", "summary": "...", "apps": [...], "resources": [...], "text_response": "..."}
```
JSON 必须是纯 JSON，无 markdown fence，无前后文字。`apps` 中每个 app 含 `app_type`, `title`, `payload`。`resources` 中每个 resource 含 `type`, `title`, `content`。
""")

        return "\n".join(parts)

    def build_sdk_user_message(self, prompt: str, image_artifacts: list[dict[str, Any]]) -> Any:
        if not image_artifacts:
            return prompt
        parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        storage = ObjectStorage()
        for artifact in image_artifacts[:MAX_IMAGE_ATTACHMENTS]:
            metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
            image_url = ""
            try:
                image_bytes, content_type = storage.get_bytes(str(artifact.get("object_key") or ""))
                mime = str(artifact.get("content_type") or content_type or "image/jpeg").split(";", 1)[0]
                image_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
            except Exception as exc:
                _get_logger().warning("sdk_image_part_data_url_failed: %s: %s", type(exc).__name__, exc)
            if not image_url:
                image_url = str(metadata.get("public_url") or "")
            if not image_url:
                image_url = f"{self.settings.api_public_base_url.rstrip('/')}/api/artifacts/{artifact.get('artifact_id')}/content"
            parts.append({"type": "image_url", "image_url": {"url": str(image_url)}})
        return parts

    @staticmethod
    def has_explicit_artifact_request(message: str) -> bool:
        """Check if user EXPLICITLY asks for an artifact (report, PPT, app, diagram, etc).

        BLACKLIST MODE: The default is answer_only. This function is the ONLY escape hatch.
        Only return True when the user unambiguously demands a generated artifact.
        """
        text = str(message or "").lower()
        # ── Strong artifact keywords ──
        # These terms indicate the user genuinely wants a generated artifact.
        # Be conservative: false negatives (missing a real request) are better than
        # false positives (generating junk for a casual question).
        artifact_terms = [
            # PPT / slides
            "ppt", "幻灯片", "课件", "演示文稿", "slide", "slides", "deck",
            "做一个演示", "生成一个演示", "做个ppt", "生成ppt", "给我做个ppt",
            # Video search
            "搜索视频", "找视频", "推荐视频", "b站搜", "哔哩搜", "bilibili搜",
            "搜一下视频", "帮我找视频",
            # Image generation
            "生成图片", "画图", "示意图", "图解", "生成一张图", "帮我画",
            # Interactive
            "动态模型", "可交互模型", "交互模型", "互动模型", "交互演示",
            "做个交互", "生成一个交互", "交互式",
            # Mind-map / exercises
            "思维导图", "脑图", "练习题", "出题", "测验", "代码实验",
            "整理成笔记", "笔记 app",
            # Explicit report request — MUST be an explicit ask, not casual mention
            "生成报告", "html报告", "html 报告", "出一份报告", "写一份报告",
            "给我报告", "生成一份报告", "出个报告", "详细分析报告",
            "做个报告", "创建报告", "生成html", "生成 html",
        ]
        return any(term in text for term in artifact_terms)

    @classmethod
    def should_force_answer_only_guard(cls, context: TutorTurnContext) -> bool:
        """BLACKLIST MODE: Default everything to answer_only (text-only).

        The vast majority of student messages are casual questions, greetings,
        or knowledge inquiries that should get a direct text answer — NOT an
        HTML report or canvas artifact.

        Only skip the guard (return False) when:
        1. User uploaded images (needs visual analysis, may legitimately produce HTML)
        2. User EXPLICITLY requests an artifact via has_explicit_artifact_request()
        3. Message is empty
        """
        # Images uploaded → Hermes may need to generate visual output
        if cls._has_uploaded_images(context):
            return False
        message = str(context.message or "").strip()
        # Empty message → don't guard
        if not message:
            return False
        # Explicit artifact request → let Hermes generate freely
        if cls.has_explicit_artifact_request(message):
            return False
        # ── DEFAULT: force answer_only for EVERYTHING else ──
        # Greetings, "你好", "今天天气", "什么是XXX", "帮我解释XXX",
        # "我觉得", "我想问", "能不能", and any other casual question
        # → ALL go to text-only answer, NO HTML report generated.
        return True

    def build_answer_only_prompt(self, context: TutorTurnContext, rag_context: dict[str, Any], rejected_capability: str = "") -> str:
        return "\n".join(
            [
                "你是 LearnForge Hermes answer-only tutor。",
                "上一轮产物选择被后端验收闸门拒绝，因为当前用户请求是直接问答/记忆确认，不是产物生成任务。",
                "请只用中文自然回答用户，不要输出 HTML，不要 JSON，不要 apps/resources，不要说已创建画布产物。",
                f"被拒绝的 capability: {rejected_capability or 'unknown'}",
                f"学生ID: {context.student_id}",
                f"课程ID: {context.course_id}",
                f"用户消息: {context.message}",
                f"学生画像: {self._truncate_text(json.dumps(context.profile or {}, ensure_ascii=False), 1200)}",
                f"学生记忆: {self._truncate_text(json.dumps(context.student_memories[-12:] if context.student_memories else [], ensure_ascii=False), 1800)}",
                f"近期对话: {self._truncate_text(json.dumps(context.recent_messages[-10:] if context.recent_messages else [], ensure_ascii=False), 2400)}",
                f"上轮回复: {self._truncate_text(context.last_assistant_answer or '', 1600)}",
                f"课程参考: {self._truncate_text(str(rag_context.get('context') or ''), 1800)}",
                "如果没有足够历史内容，就诚实说明你能看到的上下文有限，并基于现有记忆回答。",
            ]
        )

    @staticmethod
    def _plain_text_from_possible_html(text: str) -> str:
        stripped = str(text or "").strip()
        if not stripped:
            return ""
        stripped = re.sub(r"```(?:html|json)?|```", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"<[^>]+>", " ", stripped)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        return stripped

    async def run_answer_only(
        self,
        context: TutorTurnContext,
        rag_context: dict[str, Any],
        *,
        rejected_capability: str = "",
        run_id: str | None = None,
    ) -> HermesTaskResult:
        prompt = self.build_answer_only_prompt(context, rag_context, rejected_capability=rejected_capability)
        use_sdk = self.use_sdk_backend()
        command = "" if use_sdk else self.command_path()
        last_error = ""
        for provider, model in self.provider_attempts():
            if use_sdk:
                returncode, output, error = await self._invoke_hermes_sdk(
                    prompt,
                    provider,
                    model,
                    run_id=run_id,
                    persist_user_message=prompt,
                    student_id=context.student_id, conversation_id=context.conversation_id,
                )
            else:
                returncode, output, error = await self._invoke_hermes(
                    command,
                    prompt,
                    provider,
                    model,
                    self.settings.hermes_toolsets.strip(),
                    [],
                    run_id=run_id,
                )
            if returncode != 0 or not output or self.looks_like_provider_failure(output):
                last_error = (error or output or f"Hermes answer-only retry exited {returncode}")[:500]
                continue
            text = output.strip()
            direct_json = self._parse_json_dict(text)
            if direct_json:
                inner = (
                    direct_json.get("text_response")
                    or direct_json.get("final_response")
                    or direct_json.get("answer")
                    or direct_json.get("summary")
                    or direct_json.get("response")
                )
                if isinstance(inner, str) and inner.strip():
                    text = inner.strip()
            try:
                parsed = self.parse_json_result(text)
                text = parsed.text_response or parsed.summary or text
            except ModelGatewayError:
                pass
            text = self._plain_text_from_possible_html(text)[:4000]
            if text:
                return HermesTaskResult(
                    capability="answer_only",
                    mode="synchronous",
                    summary="Hermes answer-only 回复",
                    text_response=text,
                    raw_text=output,
                    trace=["answer_only_guard_retry", f"rejected_capability:{rejected_capability or 'unknown'}"],
                )
        raise ModelGatewayError(last_error or "Hermes answer-only retry returned empty output.")

    # ── detailed_analysis 专用方法 ──────────────────────────────────────────

    def _save_image_attachments(self, context: TutorTurnContext) -> list[str]:
        """将 context.image_data 中的 base64 图片保存到本地文件，返回文件路径列表。

        支持多种编码格式：
        - data:image/png;base64,<b64>
        - data:image/jpeg;base64,<b64>
        - 纯 base64 字符串（无 data: 前缀）
        - URL-safe base64（- → +, _ → /）

        Hard caps protect the service: at most MAX_IMAGE_ATTACHMENTS images per turn,
        each at most MAX_IMAGE_ATTACHMENT_BYTES after decode. Filenames are unique per
        call (uuid-based) so concurrent turns never clobber each other's uploads.
        """
        image_data_list = getattr(context, "image_data", None) or []
        image_file_paths: list[str] = []
        if not image_data_list:
            return image_file_paths
        images_dir = Path(self.settings.project_root) / ".data" / "hermes_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        logger = _get_logger()
        for i, img in enumerate(image_data_list):
            if i >= MAX_IMAGE_ATTACHMENTS:
                logger.warning("hermes_image: reached %d-image cap, ignoring the rest", MAX_IMAGE_ATTACHMENTS)
                break
            if not isinstance(img, str) or not img.strip():
                continue
            try:
                # Parse data URL or raw base64
                if img.startswith("data:image/"):
                    header, b64_data = img.split(",", 1)
                    mime = header.split(";")[0].replace("data:", "")
                    ext = mime.split("/")[-1] if "/" in mime else "png"
                else:
                    b64_data = img
                    ext = "png"
                # Fix URL-safe base64 if needed
                b64_data = b64_data.replace("-", "+").replace("_", "/")
                # Pad missing = signs
                padding = 4 - len(b64_data) % 4
                if padding != 4:
                    b64_data += "=" * padding
                img_bytes = base64.b64decode(b64_data)
                # Size guard on DECODED bytes (the prior len(img)<64 char-count check
                # was an unreliable proxy for "is this a real image").
                if len(img_bytes) < MIN_IMAGE_ATTACHMENT_BYTES:
                    logger.warning("hermes_image: skipping image %d — decoded payload too small (%d bytes)", i + 1, len(img_bytes))
                    continue
                if len(img_bytes) > MAX_IMAGE_ATTACHMENT_BYTES:
                    logger.warning("hermes_image: skipping image %d — decoded payload too large (%d bytes)", i + 1, len(img_bytes))
                    continue
                # Unique filename per call so concurrent turns never overwrite each other.
                img_path = images_dir / f"{uuid4().hex[:12]}_{i + 1}.{ext}"
                img_path.write_bytes(img_bytes)
                image_file_paths.append(str(img_path))
            except Exception as exc:
                logger.warning(
                    "hermes_image: failed to decode image %d (%d chars, starts with: %s...): %s",
                    i + 1, len(img), img[:50], exc,
                )
                continue
        return image_file_paths

    def build_detailed_analysis_prompt(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any], image_analysis: str = ""
    ) -> str:
        """构建 detailed_analysis 专用 prompt —— 要求输出 HTML，而非 JSON。"""
        has_uploaded_images = self._has_uploaded_images(context)
        image_artifacts = rag_context.get("current_image_artifacts") if isinstance(rag_context.get("current_image_artifacts"), list) else []
        artifact_context = rag_context.get("artifact_context") if isinstance(rag_context.get("artifact_context"), dict) else None
        image_file_paths: list[str] = []
        if has_uploaded_images and not image_artifacts:
            image_file_paths = [] if self.use_sdk_backend() else self._save_image_attachments(context)
        priority_context = bool(has_uploaded_images or image_file_paths or image_artifacts or artifact_context)

        parts: list[str] = []
        parts.append("你是 LearnForge 的「详细分析和讲解」专家 Agent。")

        # 用户消息
        parts.append(f"\n## 用户消息\n{context.message}")

        # 学习上下文
        parts.append(f"\n## 学习上下文\n- 学生ID: {context.student_id}\n- 课程ID: {context.course_id}")
        if context.profile:
            parts.append(f"\n## 🧠 学生画像\n{self._truncate_text(json.dumps(context.profile, ensure_ascii=False), 1200)}")
        if context.student_memories:
            parts.append(f"\n### 掌握度与典型误区\n{json.dumps(context.student_memories[-12:], ensure_ascii=False)}")
        if rag_context.get("context") and not priority_context:
            parts.append(f"\n## 课程资料参考\n{self._truncate_text(rag_context.get('context', ''), 6000)}")
        elif priority_context:
            parts.append(
                "\n## 上下文优先级锁定\n"
                "本轮存在当前附件或当前 artifact。它是唯一主上下文；课程 RAG、历史对话、旧画布内容只能在不冲突时作为背景，"
                "不得替代当前图片/文章 artifact。若无法读取当前附件，请明确说明无法可靠识别，不要从课程资料猜题。"
            )
        if artifact_context:
            parts.append(
                "\n## 当前绑定 Artifact 上下文\n"
                f"- artifact_id: {artifact_context.get('artifact_id')}\n"
                f"- kind: {artifact_context.get('kind')}\n"
                f"- title: {artifact_context.get('title')}\n"
                f"{self._truncate_text(str(artifact_context.get('content') or ''), 12000)}"
            )

        # 图片附件
        if has_uploaded_images or image_file_paths or image_artifacts:
            parts.append(f"\n## 🖼️ 用户上传的图片/截图 ({len(image_file_paths) or len(image_artifacts) or 1} 张)")
            parts.append("本轮图片是最高优先级主上下文。必须直接读取图片内容后再生成报告，禁止用课程 RAG、历史题目或旧 artifact 替代。")
            if image_artifacts:
                parts.append("### 对象存储图片 Artifact")
                for artifact in image_artifacts:
                    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
                    content_url = f"{self.settings.api_public_base_url.rstrip('/')}/api/artifacts/{artifact.get('artifact_id')}/content"
                    parts.append(
                        "- "
                        f"artifact_id={artifact.get('artifact_id')} "
                        f"object_key={artifact.get('object_key')} "
                        f"content_url={content_url} "
                        f"content_type={artifact.get('content_type')} "
                        f"public_url={metadata.get('public_url') or 'not_configured'} "
                        f"dev_file_path={metadata.get('dev_file_path') or 'not_available'}"
                    )
                parts.append(
                    "Hermes SDK/Harmony 原生多模态必须直接读取以上图片 artifact；生产环境优先使用随消息传入的 image_url part。"
                    "如果图片是英语试卷，HTML 报告必须包含题面 OCR 核验小节，逐字保留可见英文标题/题型/题号/词库/关键句。"
                )
            if image_file_paths:
                parts.append("请使用你的 **file** 工具读取每张图片文件，然后使用 **vision** 能力逐张仔细分析。")
                parts.append("如果图片中包含手写题目、试卷截图、公式、图表等，请精确提取所有文字和数字信息。")
            for i, img_path in enumerate(image_file_paths, 1):
                parts.append(f"**图片 {i} 文件路径:** `{img_path}`")
            if image_analysis:
                parts.append(
                    "\n## Python Vision fallback 预识别内容\n"
                    "以下内容来自 API 层 OCR 兜底，只用于辅助核验；最终题面仍以你对当前图片 artifact 的直接读取为准。"
                    "若 fallback 与原图冲突，以原图为准；若无法读取原图，不允许改用课程 RAG 编造题目。\n"
                    f"{image_analysis}"
                )
            else:
                parts.append("如果无法读取图片 artifact/vision 工具，不要根据附件文件名或历史记录猜题，请输出图片无法可靠识别。")

        # 输出要求 —— 关键：要求 HTML，不是 JSON
        parts.append("""
## 输出要求

请按照你的 detailed-analysis-skill 进行**五步法分析**：
1. **读题** —— 完整呈现题目原文，提取已知条件、未知量
2. **析题** —— 分析考察的知识点、解题突破口、思路选择
3. **解题** —— 逐步展示完整解答过程，使用 KaTeX 渲染所有数学公式
4. **品题** —— 总结核心方法、易错点、可迁移技巧
5. **练题** —— 设计 1-2 道变式练习题并给出简略解答

**最终输出一个完整的、可直接渲染的 HTML 文档。**

### 关键规则
- **直接输出 HTML**，不要包裹在 JSON 里，不要用 markdown code fence
- HTML 前可以有一个简短的 Markdown 摘要（用 `## 📝 分析完成` 开头），方便阅读
- HTML 必须包含 `<!DOCTYPE html>` 和完整的 `<head>` / `<body>`
- 在 `<head>` 中引入 KaTeX CDN 渲染数学公式：
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {delimiters: [{left: '\\\\\\\\(', right: '\\\\\\\\)', display: false}, {left: '\\\\\\\\[', right: '\\\\\\\\]', display: true}]});"></script>
  ```
- 使用美观的现代设计：渐变背景、卡片布局、合适的色彩编码
- HTML 结构必须根据题目内容现场设计，**禁止使用固定模板**
- 移动端响应式：使用 viewport meta 标签和相对单位
""")
        return "\n".join(parts)

    async def run_detailed_analysis(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any], run_id: str | None = None
    ) -> str:
        """为 detailed_analysis 能力执行 Hermes，直接返回原始 HTML 文本。

        与 run_resource_bundle() 不同，此方法不要求 JSON 输出，不经过 JSON 解析。
        """
        use_sdk = self.use_sdk_backend()
        command = "" if use_sdk else self.command_path()
        image_artifacts = self._persist_uploaded_image_artifacts(context, run_id)
        if image_artifacts:
            rag_context["current_image_artifacts"] = image_artifacts
        image_analysis = ""
        if self.settings.python_vision_fallback_enabled:
            image_analysis = await self.pre_analyze_uploaded_images(context, run_id=run_id)
            if image_analysis:
                rag_context["image_analysis"] = image_analysis
        if self._has_uploaded_images(context) and self.settings.python_vision_fallback_enabled and not self._vision_analysis_is_reliable(image_analysis):
            failure = self._vision_failure_text()
            return (
                "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">"
                "<title>图片无法可靠识别</title></head><body>"
                f"<h1>图片无法可靠识别</h1><p>{failure}</p>"
                "</body></html>"
            )
        prompt = self.build_detailed_analysis_prompt(plan, context, rag_context, image_analysis=image_analysis)
        sdk_prompt = self.build_sdk_user_message(prompt, image_artifacts) if use_sdk else prompt
        toolsets = self.settings.hermes_toolsets.strip()
        skills = self.skills_for_plan(plan, context)

        attempts = self.provider_attempts()
        last_error: str | None = None
        for provider, model in attempts:
            if use_sdk:
                returncode, output, error = await self._invoke_hermes_sdk(
                    sdk_prompt,
                    provider,
                    model,
                    run_id=run_id,
                    persist_user_message=prompt,
                    student_id=context.student_id, conversation_id=context.conversation_id,
                )
            else:
                returncode, output, error = await self._invoke_hermes(
                    command, prompt, provider, model, toolsets, skills, run_id=run_id
                )
            combined = error or output or "no output"
            if returncode != 0:
                last_error = f"Hermes exited {returncode}: {combined[:300]}"
                # Whether this looks like a provider failure or a Hermes crash, the
                # next attempt may use a different provider, so always try it.
                continue
            if not output:
                last_error = f"Hermes returned empty output: {error[:300]}"
                continue
            # 成功 —— 返回原始文本（应该是 HTML）
            return output.strip()

        raise ModelGatewayError(last_error or "detailed_analysis: Hermes 未返回有效输出")

    # ── Unified run_hermes() ───────────────────────────────────────────────

    async def run_hermes(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any],
        on_stderr_line: "Callable[[str], Awaitable[None]] | None" = None,
        on_trace_step: "Callable[[str, str, str], Awaitable[None]] | None" = None,
        run_id: str | None = None,
        on_hermes_event: "Callable[[dict], Awaitable[None]] | None" = None,
    ) -> HermesTaskResult:
        """统一 Hermes 调用 —— 薄管道：加载全部 skill，调用一次，直接返回 Hermes 的输出。

        Python 层不干预 Hermes 的决策。不强制 JSON 格式，不强制 app 类型，不重试。
        如果提供 on_stderr_line，则实时转发 Hermes 的 stderr 行作为进度事件。
        """
        use_sdk = self.use_sdk_backend()
        command = "" if use_sdk else self.command_path()
        image_artifacts = self._persist_uploaded_image_artifacts(context, run_id)
        if image_artifacts and on_trace_step:
            await on_trace_step("artifact.source_image", "completed", f"已写入 {len(image_artifacts)} 个图片 artifact")
        image_analysis = ""
        if self.settings.python_vision_fallback_enabled:
            image_analysis = await self.pre_analyze_uploaded_images(context, on_trace_step=on_trace_step, run_id=run_id)
        elif self._has_uploaded_images(context) and on_trace_step:
            await on_trace_step("vision.native_handoff", "completed", "Python OCR 已关闭；图片 artifact 交由 Hermes SDK/Harmony 原生多模态读取")
        if self.is_cancelled(run_id):
            raise asyncio.CancelledError()
        if self._has_uploaded_images(context) and self.settings.python_vision_fallback_enabled and not self._vision_analysis_is_reliable(image_analysis):
            failure = self._vision_failure_text()
            if on_trace_step:
                await on_trace_step("vision.final_merge", "failed", "图片 OCR 未达到可靠阈值，已停止生成")
            return HermesTaskResult(
                summary=failure,
                trace=["vision.failed_closed: 图片 OCR 未达到可靠阈值，已禁止生成猜测性报告"],
                capability="image_analysis_failed",
                text_response=failure,
                raw_text=failure,
            )
        prompt = self.build_unified_prompt(
            plan,
            context,
            {**rag_context, "current_image_artifacts": image_artifacts},
            image_analysis=image_analysis,
        )
        toolsets = self.settings.hermes_toolsets.strip()
        from app.hermes_runtime.skill_sync import REQUIRED_HERMES_SKILLS
        skills = list(REQUIRED_HERMES_SKILLS)

        attempts = self.provider_attempts()
        last_error = ""
        output = ""
        for provider, model in attempts:
            if on_trace_step:
                await on_trace_step("hermes.provider_attempt", "running", f"{provider}:{model}")
            sdk_prompt = self.build_sdk_user_message(prompt, image_artifacts) if use_sdk else prompt
            if use_sdk:
                if image_artifacts and on_trace_step:
                    await on_trace_step("vision.sdk_image_parts", "completed", f"已向 Hermes SDK 注入 {len(image_artifacts)} 个 image_url parts")
                returncode, candidate_output, error = await self._invoke_hermes_sdk(
                    sdk_prompt,
                    provider,
                    model,
                    on_stderr_line=on_stderr_line,
                    run_id=run_id,
                    persist_user_message=prompt,
                    student_id=context.student_id, conversation_id=context.conversation_id,
                    on_hermes_event=on_hermes_event,
                )
            else:
                returncode, candidate_output, error = await self._invoke_hermes(
                    command, prompt, provider, model, toolsets, skills,
                    on_stderr_line=on_stderr_line,
                    run_id=run_id,
                )
            combined = error or candidate_output or "no output"
            if returncode != 0:
                last_error = f"Hermes exited {returncode}: {combined[:500]}"
                if on_trace_step:
                    await on_trace_step("hermes.provider_attempt", "failed", last_error[:180])
                continue
            if not candidate_output:
                last_error = f"Hermes returned empty output: {error[:500]}"
                if on_trace_step:
                    await on_trace_step("hermes.provider_attempt", "failed", last_error[:180])
                continue
            if self.looks_like_provider_failure(candidate_output):
                last_error = f"Hermes provider failure: {candidate_output[:500]}"
                if on_trace_step:
                    await on_trace_step("hermes.provider_attempt", "failed", last_error[:180])
                continue
            output = candidate_output
            if on_trace_step:
                await on_trace_step("hermes.provider_attempt", "completed", f"{provider}:{model}")
            break

        if not output:
            raise ModelGatewayError(last_error or "Hermes returned empty output.")

        # ── HTML sentinel 检测：marker/HTML 出现在任意位置都必须提取为 artifact ──
        assistant_text, html_content = self._extract_html_output(output)
        if html_content:
            # Try to extract capability from JSON declared alongside/before the HTML.
            # Hermes may output e.g. {"capability":"ppt","topic":"..."} then ---HERMES_HTML_OUTPUT---
            declared_capability = self._extract_capability_from_text(assistant_text) or self._extract_capability_from_text(output)
            if not declared_capability:
                # Last resort: infer from user message keywords (not Python routing —
                # just a fallback when Hermes's own JSON declaration can't be parsed).
                declared_capability = self._infer_capability_from_message(getattr(context, 'message', ''))
            return HermesTaskResult(
                capability=declared_capability or "detailed_analysis",
                mode="background",
                summary=assistant_text or "详细分析完成",
                raw_html=html_content,
                text_response="✅ 分析完成！报告已生成并推送到画布。",
                raw_text=output,
                trace=[f"{declared_capability or 'detailed_analysis'}_html_generated", "raw_html_extracted_from_chat"],
            )

        # ── JSON 解析 ──
        try:
            result = self.parse_json_result(output)
            data = self._parse_json_dict(output)
            if data:
                result.capability = str(data.get("capability", result.capability or ""))
                result.topic = str(data.get("topic", result.topic or ""))
                result.mode = str(data.get("mode", result.mode or "synchronous"))
                result.raw_html = str(data.get("raw_html", result.raw_html or ""))
                result.text_response = str(data.get("text_response", result.text_response or ""))
            if result.raw_html:
                assistant_text, html_content = self._extract_html_output(result.raw_html)
                if html_content:
                    result.raw_html = html_content
                    result.text_response = result.text_response if not self._looks_like_html(result.text_response) else ""
                    result.summary = result.summary or assistant_text or "详细分析完成"
            if result.text_response:
                assistant_text, html_content = self._extract_html_output(result.text_response)
                if html_content:
                    result.raw_html = html_content
                    result.text_response = "✅ 分析完成！报告已生成并推送到画布。"
                    result.summary = assistant_text or result.summary or "详细分析完成"
                    result.capability = result.capability or "detailed_analysis"
            if self._wants_html_report(plan, context) and not result.raw_html and not result.apps and not result.resources and result.text_response:
                result.raw_html = self._html_report_fallback_from_text(result.text_response, title=str(plan.payload.get("topic") or "学习报告"))
                result.text_response = "✅ 分析完成！报告已生成并推送到画布。"
                result.summary = result.summary or "详细分析完成"
                result.capability = "detailed_analysis"
                result.mode = "background"
            return result
        except ModelGatewayError:
            pass

        # ── 纯文本 fallback ──
        clean_output = output.strip()[:4000]
        if clean_output:
            if self._wants_html_report(plan, context):
                return HermesTaskResult(
                    capability="detailed_analysis",
                    mode="background",
                    summary="详细分析完成",
                    raw_html=self._html_report_fallback_from_text(clean_output, title=str(plan.payload.get("topic") or "学习报告")),
                    text_response="✅ 分析完成！报告已生成并推送到画布。",
                    raw_text=output,
                    trace=["text_fallback_wrapped_as_html"],
                )
            return HermesTaskResult(
                capability="answer_only",
                mode="synchronous",
                summary="Hermes 回复",
                text_response=clean_output,
                raw_text=output,
                trace=["text_fallback"],
            )

        raise ModelGatewayError("Hermes returned unrecognizable output.")

    @staticmethod
    def _extract_html_output(output: str) -> tuple[str, str]:
        text = (output or "").strip()
        if not text:
            return "", ""
        marker = "---HERMES_HTML_OUTPUT---"
        if marker in text:
            before, after = text.split(marker, 1)
            html = HermesTaskExecutor._normalize_html_artifact_text(after.strip())
            return before.strip(), html if HermesTaskExecutor._looks_like_html(html) else ""
        lower = text.lower()
        starts = [idx for idx in (lower.find("<!doctype html"), lower.find("<html")) if idx >= 0]
        if not starts:
            return "", ""
        start = min(starts)
        assistant_text = text[:start].strip()
        html = text[start:].strip()
        html = HermesTaskExecutor._normalize_html_artifact_text(html)
        return assistant_text, html if HermesTaskExecutor._looks_like_html(html) else ""

    @staticmethod
    def _infer_capability_from_message(message: str) -> str:
        """Fallback: infer likely capability from user message keywords.

        This is NOT Python-side routing — it only fires when Hermes already produced
        HTML but we cannot parse its explicit capability declaration from the output.
        Used as last resort before defaulting to 'detailed_analysis'.
        """
        if not message:
            return ""
        msg = message.lower()
        # PPT markers
        if any(kw in msg for kw in ["ppt", "幻灯", "课件", "演示文稿", "slide", "deck", "讲义"]):
            return "ppt"
        # Interactive demo markers
        if any(kw in msg for kw in ["交互", "可交互", "动态演示", "3d", "模拟", "动画演示", "可视化演示"]):
            return "interactive_demo"
        # Video search markers
        if any(kw in msg for kw in ["b站", "哔哩", "bilibili", "搜索视频", "找视频", "视频搜索", "推荐视频"]):
            return "video_search"
        return ""

    @staticmethod
    def _looks_like_html(value: str) -> bool:
        head = HermesTaskExecutor._normalize_html_artifact_text(value or "").strip()[:500].lower()
        return "<html" in head or "<!doctype html" in head

    @staticmethod
    def _extract_capability_from_text(text: str) -> str:
        """Try to parse a `capability` field from JSON embedded in free-form text.

        Hermes may output a JSON contract alongside/before HTML or free text,
        e.g. `{"capability":"ppt","topic":"..."}` before `---HERMES_HTML_OUTPUT---`.
        Also handles Hermes's `final_response` wrapper where the real capability JSON
        is nested inside a string field: `{"final_response":"{\\"capability\\":\\"ppt\\"}"}`.
        Returns the capability string or empty string.
        """
        if not text:
            return ""
        import re as _re
        # ── Strategy 1: find JSON objects in the text and parse each ──
        for obj_match in _re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", str(text)):
            try:
                obj = json.loads(obj_match.group())
                if isinstance(obj, dict):
                    cap = obj.get("capability")
                    if isinstance(cap, str) and cap.strip():
                        return cap.strip()
                    # Hermes final_response wrapper
                    inner = obj.get("final_response")
                    if isinstance(inner, str):
                        try:
                            inner_obj = json.loads(inner)
                            if isinstance(inner_obj, dict):
                                cap = inner_obj.get("capability")
                                if isinstance(cap, str) and cap.strip():
                                    return cap.strip()
                        except (json.JSONDecodeError, TypeError):
                            pass
            except (json.JSONDecodeError, TypeError):
                pass
        # ── Strategy 2: full-text parse (handles the case where text IS pure JSON) ──
        try:
            obj = json.loads(str(text))
            if isinstance(obj, dict):
                cap = obj.get("capability")
                if isinstance(cap, str) and cap.strip():
                    return cap.strip()
                inner = obj.get("final_response")
                if isinstance(inner, str):
                    try:
                        inner_obj = json.loads(inner)
                        if isinstance(inner_obj, dict):
                            cap = inner_obj.get("capability")
                            if isinstance(cap, str) and cap.strip():
                                return cap.strip()
                    except (json.JSONDecodeError, TypeError):
                        pass
        except (json.JSONDecodeError, TypeError):
            pass
        # ── Strategy 3: regex scan for "capability":"xxx" (regular + escaped quotes) ──
        for pattern in [
            r"\"capability\"\s*:\s*\"([^\"]+)\"",       # regular JSON quotes
            r"\\\"capability\\\"\s*:\s*\\\"([^\"\\]+)\\\"",  # JSON-escaped quotes (inside final_response)
        ]:
            candidates = _re.findall(pattern, str(text))
            if candidates:
                return candidates[-1]
        return ""

    @staticmethod
    def _normalize_html_artifact_text(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        for _ in range(4):
            stripped = text.strip()
            has_escaped_lines = "\\n" in stripped or "\\\\n" in stripped
            has_escaped_quotes = '\\"' in stripped or '\\\\"' in stripped
            if not (has_escaped_lines or has_escaped_quotes):
                break
            decoded = stripped
            try:
                decoded = json.loads(stripped) if stripped[:1] in {'"', "'"} else json.loads(f'"{stripped}"')
            except json.JSONDecodeError:
                decoded = (
                    stripped
                    .replace("\\\\r\\\\n", "\n")
                    .replace("\\\\n", "\n")
                    .replace("\\\\t", "\t")
                    .replace('\\\\"', '"')
                    .replace("\\\\/", "/")
                    .replace("\\r\\n", "\n")
                    .replace("\\n", "\n")
                    .replace("\\t", "\t")
                    .replace('\\"', '"')
                    .replace("\\/", "/")
                )
            if decoded == text:
                break
            text = decoded
        lower = text.lower()
        starts = [index for index in (lower.find("<!doctype html"), lower.find("<html")) if index >= 0]
        if starts:
            start = min(starts)
            end_match = re.search(r"<\s*/\s*html\s*>", text[start:], flags=re.IGNORECASE)
            if end_match:
                text = text[start : start + end_match.end()]
            else:
                text = text[start:]
        return text

    @staticmethod
    def _wants_html_report(plan: AgentPlan, context: TutorTurnContext) -> bool:
        payload = getattr(plan, "payload", {}) if getattr(plan, "payload", None) else {}
        return str(getattr(plan, "task_type", "") or "") == "detailed_analysis" or str(payload.get("capability") or "") == "detailed_analysis"

    @staticmethod
    def _html_report_fallback_from_text(text: str, *, title: str) -> str:
        safe_title = escape(title or "学习报告")
        safe_body = escape(text or "分析完成。")
        paragraphs = "".join(f"<p>{line}</p>" for line in safe_body.splitlines() if line.strip()) or f"<p>{safe_body}</p>"
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <style>
    :root {{ color-scheme: light; --ink:#102033; --muted:#5a6b82; --paper:#ffffff; --line:#dce7f5; --accent:#2563eb; }}
    body {{ margin:0; font-family: ui-serif, Georgia, "Songti SC", serif; color:var(--ink); background:linear-gradient(135deg,#eef5ff,#fff7ed); line-height:1.75; }}
    main {{ max-width:920px; margin:0 auto; padding:48px 22px 72px; }}
    .card {{ background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:28px; box-shadow:0 24px 70px rgba(30,64,175,.12); padding:34px; }}
    h1 {{ margin:0 0 10px; font-size:clamp(30px,5vw,54px); letter-spacing:-.04em; }}
    .eyebrow {{ color:var(--accent); font-weight:800; text-transform:uppercase; letter-spacing:.12em; font-size:13px; }}
    .note {{ margin:18px 0 28px; color:var(--muted); }}
    p {{ margin:0 0 16px; font-size:18px; }}
    @media (max-width:720px) {{ main {{ padding:24px 14px 48px; }} .card {{ padding:22px; border-radius:20px; }} p {{ font-size:16px; }} }}
  </style>
</head>
<body>
  <main>
    <section class="card">
      <div class="eyebrow">LearnForge HTML Artifact</div>
      <h1>{safe_title}</h1>
      <p class="note">Hermes 返回了纯文本讲解，系统已将其安全封装为可打开的 HTML 报告。</p>
      <section>{paragraphs}</section>
    </section>
  </main>
</body>
</html>"""

    async def run_background_hermes(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any],
        run_id: str | None = None,
    ) -> HermesTaskResult:
        """后台 Hermes 执行 —— 无 SSE 回调，适合 asyncio.create_task() 独立运行。

        与 run_hermes() 不同：不转发 stderr/trace/hermes_event 到 SSE 流，
        完全独立执行。用于重型产物生成（PPT、interactive_demo、detailed_analysis 等）
        在后台完成后直接写入 DB 和 Canvas。
        """
        return await self.run_hermes(
            plan, context, rag_context,
            on_stderr_line=None,
            on_trace_step=None,
            run_id=run_id,
            on_hermes_event=None,
        )

    @staticmethod
    def _parse_json_dict(output: str) -> dict[str, Any] | None:
        """轻量 JSON parse，不抛异常，用于提取 capability/mode 等元数据。"""
        try:
            cleaned = HermesTaskExecutor._strip_markdown_fences(output)
            candidate = HermesTaskExecutor._extract_json_object(cleaned)
            if candidate:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else None
        except Exception:
            pass
        return None
