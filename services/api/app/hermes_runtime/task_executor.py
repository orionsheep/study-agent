from __future__ import annotations

import asyncio
import ast
import base64
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import AgentPlan, TutorTurnContext
from app.core.config import get_settings
from app.hermes_runtime.command import resolve_hermes_command
from app.model_gateway.errors import ProviderBlocked, ModelGatewayError
from app.skills.custom_html_app_skill import CustomHtmlAppSkill


class HermesTaskResult(BaseModel):
    summary: str = ""
    trace: list[str] = Field(default_factory=list)
    resources: list[dict[str, Any]] = Field(default_factory=list)
    apps: list[dict[str, Any]] = Field(default_factory=list)
    raw_text: str = ""


class HermesTaskExecutor:
    def __init__(self) -> None:
        self.settings = get_settings()

    def provider_name(self) -> str:
        provider = getattr(self.settings, "hermes_provider", "gemini")
        return "xiaomi" if provider == "mimo" else provider

    def provider_attempts(self) -> list[tuple[str, str]]:
        attempts: list[tuple[str, str]] = []
        provider = getattr(self.settings, "hermes_provider", "gemini")
        if provider == "mimo" and getattr(self.settings, "mimo_api_key", ""):
            attempts.append(("xiaomi", self.settings.mimo_text_model))
            if getattr(self.settings, "gemini_api_key", ""):
                attempts.append(("gemini", self.settings.gemini_text_model))
        elif provider == "gemini" and getattr(self.settings, "gemini_api_key", ""):
            attempts.append(("gemini", self.settings.gemini_text_model))
            if getattr(self.settings, "mimo_api_key", ""):
                attempts.append(("xiaomi", self.settings.mimo_text_model))
        if not attempts:
            attempts.append((self.provider_name(), self.settings.gemini_text_model if provider == "gemini" else self.settings.mimo_text_model))
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
            ]
        )

    def command_path(self) -> str:
        configured = self.settings.hermes_command.strip()
        resolved = resolve_hermes_command(configured)
        if resolved:
            return resolved
        raise ProviderBlocked("blocked_missing_runtime", f"Hermes CLI is not available at {configured or 'hermes'}.")

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["HERMES_HOME"] = str(self.settings.project_root / self.settings.hermes_home)
        env["HERMES_ACCEPT_HOOKS"] = "1"
        provider = self.provider_name()
        model = self.settings.mimo_text_model if provider == "xiaomi" else self.settings.gemini_text_model
        env["HERMES_PROVIDER"] = provider
        env["HERMES_INFERENCE_PROVIDER"] = provider
        env["HERMES_INFERENCE_MODEL"] = model
        if self.settings.mimo_api_key:
            env["MIMO_API_KEY"] = self.settings.mimo_api_key
            env["XIAOMI_API_KEY"] = self.settings.mimo_api_key
        env["MIMO_BASE_URL"] = self.settings.mimo_base_url
        env["MIMO_TEXT_MODEL"] = self.settings.mimo_text_model
        mimo_max_tokens = int(getattr(self.settings, "mimo_max_tokens", 16384))
        gemini_max_tokens = int(getattr(self.settings, "gemini_max_tokens", 32768))
        env["MIMO_MAX_TOKENS"] = str(mimo_max_tokens)
        env["XIAOMI_BASE_URL"] = self.settings.mimo_base_url
        if self.settings.gemini_api_key:
            env.setdefault("GEMINI_API_KEY", self.settings.gemini_api_key)
        env.setdefault("GEMINI_TEXT_MODEL", self.settings.gemini_text_model)
        env.setdefault("GEMINI_IMAGE_MODEL", self.settings.gemini_image_model)
        env["GEMINI_MAX_TOKENS"] = str(gemini_max_tokens)
        env["HERMES_MAX_OUTPUT_TOKENS"] = str(max(gemini_max_tokens, mimo_max_tokens))
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

    def build_resource_bundle_prompt(self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any]) -> str:
        expected_app_types = plan.payload.get("expected_app_types", [])
        expected_resource_types = plan.payload.get("expected_resource_types", [])
        required_outputs = list(dict.fromkeys([*expected_resource_types, *expected_app_types]))
        if plan.payload.get("requires_canvas") and not expected_resource_types:
            required_outputs = ["document", *required_outputs]
        repair_missing = plan.payload.get("protocol_repair_missing", [])
        # Include image data for vision-based analysis
        # Save base64 images to temp files so the Hermes agent can use its vision tool
        image_data_list = getattr(context, "image_data", None) or []
        image_file_paths: list[str] = []
        if image_data_list:
            images_dir = Path(self.settings.project_root) / ".data" / "hermes_images"
            images_dir.mkdir(parents=True, exist_ok=True)
            for i, img in enumerate(image_data_list):
                if not isinstance(img, str) or len(img) < 128:
                    continue
                try:
                    # Extract base64 data and determine mime type
                    if img.startswith("data:image/"):
                        header, b64_data = img.split(",", 1)
                        mime = header.split(";")[0].replace("data:", "")
                        ext = mime.split("/")[-1] if "/" in mime else "png"
                    else:
                        b64_data = img
                        ext = "png"
                    img_bytes = base64.b64decode(b64_data)
                    img_path = images_dir / f"user_upload_{i + 1}.{ext}"
                    img_path.write_bytes(img_bytes)
                    image_file_paths.append(str(img_path))
                except Exception:
                    continue
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
            "recent_messages": [self._compact_item(m, text_limit=600) for m in context.recent_messages[-6:]],
            "recent_apps": [self._compact_item(a) for a in context.recent_apps[-6:]],
            "recent_resources": [self._compact_item(r) for r in context.recent_resources[-6:]],
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
        repair_instruction = ""
        if repair_missing:
            repair_instruction = (
                "This is a protocol repair attempt. The previous JSON missed these required artifacts: "
                f"{json.dumps(repair_missing, ensure_ascii=False)}. Return the missing artifacts exactly, with valid payloads.\n"
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
                "DO NOT use generic text layouts or the LearnForge 'lfx-lab' dashboard layout. Instead, build a highly advanced, visually stunning graphical simulation. "
                "Use an internal multi-agent production workflow before writing the final JSON: "
                "Demo Architect defines the scene graph, state schema, topic-specific variables, control contract, and first-frame composition; "
                "Graphics Engineer implements the visual system with Canvas/SVG/CSS 3D/WebGL/Three.js when useful, including responsive sizing and nonblank first render; "
                "Interaction Engineer binds every control through delegated addEventListener handlers and verifies each button/slider/drag gesture mutates state and causes a visible scene update; "
                "QA Verifier checks selectors, no overlap, no dead controls, no template leakage, no blank stage, no fake data, no unrelated topic drift, and no unsupported native app_type. "
                "Do not reveal this workflow; use it only to improve the final custom.html payload. "
                "If you use React/Vue-style state, output the fully runnable compiled DOM/JavaScript pattern, never raw template syntax such as {{ value }}, JSX, SFC blocks, or Babel-only code. "
                "Use framework-like architecture with a state object, render() function, component sections, SVG/Canvas drawing, and delegated event handling that works in a plain sandbox. "
                "Focus on rendering REAL mathematical curves, scientific phenomena, 3D/WebGL models, or dynamic data. Include smooth animations and interactive controls (sliders, drag-and-drop, camera orbit/zoom when useful). "
                "For spatial or 3D topics, prefer a split layout with controls in a fixed side panel and the model in a separate stage so controls never cover the object; include drag orbit, wheel/slider zoom, reset, and live state readouts. "
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
                "ABSOLUTELY FORBIDDEN: When capability is interactive_demo, the app_type MUST be custom.html. You are STRICTLY FORBIDDEN from returning physics.work_energy_demo, math.gradient_descent_demo, or any other native demo app_type, EVEN IF the topic relates to work, energy, kinetic energy, the work-energy theorem, gradient descent, or any concept those native demos cover. Those native demos are generic mass/velocity/force or learning-rate sliders with NO topic-specific visualization and are NOT acceptable here. "
                "DO NOT reinterpret or generalize the user's topic into a different concept (e.g. do NOT turn '伯努利定律/Bernoulli' into '动能定理/work-energy theorem', do NOT turn a fluid request into a generic block-on-track demo). Build a custom.html simulation that DIRECTLY depicts the user's actual topic — for a Bernoulli/fluid/Venturi request, draw a real pipe with a narrowing throat, animated flowing fluid particles that speed up in the throat, and live pressure/velocity gauges showing the pressure drop. "
                "CRITICAL: The entire generated HTML string MUST be placed inside the `html` key of the `payload` dictionary (i.e. `payload: {\"html\": \"...\"}`).\n"
            )
        if capability == "ppt":
            custom_html_instruction = (
                "For PPT / slide deck requests, use guizang-ppt-skill as the primary design skill. "
                "Create a complete single-file HTML horizontal-swipe deck, not a tiny outline preview. "
                "Return exactly one app with app_type custom.html and payload.html containing the full deck HTML. "
                "Also return a ppt resource whose content summarizes slide_count, style, outline, speaker_notes, and html_deck=true. "
                "The HTML deck should follow one of guizang-ppt-skill's two visual systems: "
                "Style A 电子杂志 × 电子墨水 for narrative / salon / personal talks, or Style B 瑞士国际主义 for product / data / method / technology presentations. "
                "If the user does not specify a style, choose the one that best fits the content and record it in payload.deck_style. "
                "The deck must be self-contained, 16:9 or 21:9 responsive, keyboard/touch navigable, and suitable for fullscreen display in a sandbox iframe. "
                "Include visible Chinese slide copy, strong typography hierarchy, slide numbers, section rhythm, and speaker notes in the ppt resource. "
                "Do not output markdown, external file paths, or a placeholder `slides` list without HTML. "
                "CRITICAL: expected_app_types is [\"custom.html\"] for PPT requests; therefore the app_type MUST be custom.html and the complete deck MUST be inside payload.html.\n"
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
        return (
            "You are the LearnForge Hermes execution agent. Execute the resource-bundle-skill.\n"
            "Return ONLY valid JSON matching the Resource Bundle Skill contract. No markdown fences.\n"
            "For Chinese user requests, all titles and visible learning copy should be Chinese.\n"
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
        result = HermesTaskResult.model_validate({**data, "raw_text": text})
        if not result.resources and not result.apps:
            raise ModelGatewayError("Hermes JSON must include at least one resource or app.")
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
        chose (e.g. physics.work_energy_demo for a Bernoulli request) into a custom.html app
        backed by a real interactive HTML widget."""
        capability = plan.payload.get("capability", "resource_bundle")
        expected_app_types = plan.payload.get("expected_app_types", []) or []
        if capability != "interactive_demo" or "custom.html" not in expected_app_types:
            return result
        topic = self._short_topic(plan.payload.get("topic") or plan.payload.get("learning_topic") or "互动演示")
        for app in result.apps:
            app_type = str(app.get("app_type", ""))
            if app_type in self._FORBIDDEN_DEMO_APP_TYPES:
                title = self._short_topic(app.get("title") or topic, topic)
                widget_topic = title or topic
                app["app_type"] = "custom.html"
                app["title"] = title
                app["payload"] = {
                    "html": CustomHtmlAppSkill().fallback_widget(widget_topic, "", ""),
                    "topic": widget_topic,
                }
                trace = result.trace if isinstance(result.trace, list) else []
                trace.append(f"corrected_app_type:{app_type}->custom.html")
                result.trace = trace
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
        self, command: str, prompt: str, provider: str, model: str, toolsets: str, skills: list[str]
    ) -> tuple[int, str, str]:
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
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.settings.hermes_task_timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise ModelGatewayError(
                f"Hermes task timed out after {self.settings.hermes_task_timeout_seconds}s."
            ) from exc
        return (
            process.returncode or 0,
            stdout.decode("utf-8", errors="replace").strip(),
            stderr.decode("utf-8", errors="replace").strip(),
        )

    # How many times to re-ask the SAME model to fix non-JSON output before moving on.
    JSON_REPAIR_RETRIES = 2

    async def run_resource_bundle(self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any]) -> HermesTaskResult:
        command = self.command_path()
        base_prompt = self.build_resource_bundle_prompt(plan, context, rag_context)
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
                returncode, output, error = await self._invoke_hermes(command, prompt, provider, model, toolsets, skills)
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

    # ── detailed_analysis 专用方法 ──────────────────────────────────────────

    def _save_image_attachments(self, context: TutorTurnContext) -> list[str]:
        """将 context.image_data 中的 base64 图片保存到本地文件，返回文件路径列表。"""
        image_data_list = getattr(context, "image_data", None) or []
        image_file_paths: list[str] = []
        if not image_data_list:
            return image_file_paths
        images_dir = Path(self.settings.project_root) / ".data" / "hermes_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for i, img in enumerate(image_data_list):
            if not isinstance(img, str) or len(img) < 128:
                continue
            try:
                if img.startswith("data:image/"):
                    header, b64_data = img.split(",", 1)
                    mime = header.split(";")[0].replace("data:", "")
                    ext = mime.split("/")[-1] if "/" in mime else "png"
                else:
                    b64_data = img
                    ext = "png"
                img_bytes = base64.b64decode(b64_data)
                img_path = images_dir / f"user_upload_{i + 1}.{ext}"
                img_path.write_bytes(img_bytes)
                image_file_paths.append(str(img_path))
            except Exception:
                continue
        return image_file_paths

    def build_detailed_analysis_prompt(
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any]
    ) -> str:
        """构建 detailed_analysis 专用 prompt —— 要求输出 HTML，而非 JSON。"""
        image_file_paths = self._save_image_attachments(context)

        parts: list[str] = []
        parts.append("你是 LearnForge 的「详细分析和讲解」专家 Agent。")

        # 用户消息
        parts.append(f"\n## 用户消息\n{context.message}")

        # 学习上下文
        parts.append(f"\n## 学习上下文\n- 学生ID: {context.student_id}\n- 课程ID: {context.course_id}")
        if rag_context.get("context"):
            parts.append(f"\n## 课程资料参考\n{self._truncate_text(rag_context.get('context', ''), 6000)}")

        # 图片附件
        if image_file_paths:
            parts.append(f"\n## 🖼️ 用户上传的图片/截图 ({len(image_file_paths)} 张)")
            parts.append("请使用你的 **file** 工具读取每张图片文件，然后使用 **vision** 能力逐张仔细分析。")
            parts.append("如果图片中包含手写题目、试卷截图、公式、图表等，请精确提取所有文字和数字信息。")
            for i, img_path in enumerate(image_file_paths, 1):
                parts.append(f"**图片 {i} 文件路径:** `{img_path}`")

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
        self, plan: AgentPlan, context: TutorTurnContext, rag_context: dict[str, Any]
    ) -> str:
        """为 detailed_analysis 能力执行 Hermes，直接返回原始 HTML 文本。

        与 run_resource_bundle() 不同，此方法不要求 JSON 输出，不经过 JSON 解析。
        """
        command = self.command_path()
        prompt = self.build_detailed_analysis_prompt(plan, context, rag_context)
        toolsets = self.settings.hermes_toolsets.strip()
        skills = self.skills_for_plan(plan, context)

        attempts = self.provider_attempts()
        last_error: str | None = None
        for provider, model in attempts:
            returncode, output, error = await self._invoke_hermes(
                command, prompt, provider, model, toolsets, skills
            )
            combined = error or output or "no output"
            if returncode != 0:
                last_error = f"Hermes exited {returncode}: {combined[:300]}"
                if self.looks_like_provider_failure(combined):
                    continue
                # Non-provider failure — try next provider anyway
                continue
            if not output:
                last_error = f"Hermes returned empty output: {error[:300]}"
                continue
            # 成功 —— 返回原始文本（应该是 HTML）
            return output.strip()

        raise ModelGatewayError(last_error or "detailed_analysis: Hermes 未返回有效输出")
