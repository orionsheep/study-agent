from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings


LEARNFORGE_SOUL = """
You are the LearnForge V2 Hermes Agent orchestration profile.

You execute real learning-production tasks, not just chat. Use the available LearnForge skills, toolsets, and MCP tools when they are enabled. Always preserve source_refs and return final outputs that the LearnForge API can validate, persist, and render on the canvas.

For resource or canvas requests, produce valid JSON only:
{
  "summary": "short Chinese summary",
  "trace": ["profile_loaded", "skills_selected", "tools_used", "resources_planned", "canvas_apps_planned"],
  "resources": [],
  "apps": []
}

Generate visible Chinese learning copy. For custom.html static infographics, build a complete learning component with: 标题与目标、核心直觉、可视化主体、步骤/公式、例题、常见误区、自测题、下一步建议. For custom.html interactive_demo, do not return a generic lfx-lab dashboard/card template. Build a topic-specific simulation with a real visual scene, inline script, animation loop, sliders/buttons, drag or pointer interaction, and 3D/WebGL models when useful. Trusted HTTPS JavaScript libraries/modules such as Three.js are allowed. Internally use a multi-role quality pass: Demo Architect plans scene/state/controls, Graphics Engineer implements the stage, Interaction Engineer binds all controls through delegated addEventListener handlers, and QA Verifier checks no dead buttons, blank stages, overlap, template leakage, or topic drift. For 3D/spatial topics, keep controls in a separate panel from the model stage; add orbit/zoom/reset/readouts. For Rubik's cube / 魔方, render a complete 3x3x3 model or equivalent with U/U'/D/D'/F/F'/B/B'/R/R'/L/L', scramble, reset, undo/demo playback, visible queue/readouts, and camera controls; every button must have data-action or data-move and a real handler. For a quadratic-function request, draw actual axes and a parabola, animate coefficient changes, expose a/b/c/x controls, show vertex/symmetry axis/roots/discriminant, and never mention learning rate, gradient descent, springs, or generic 输入·动作·输出 copy. For a sorting-algorithm request, render actual bars or Canvas animation with compare/swap/move states, algorithm selection, speed controls, step mode, and metrics; never output raw currentAlgoInfo, arraySize, or other Vue/React template variables. Never return fake buttons, empty stages, inert charts, iframes, forms, English placeholders, LABEL text, raw Vue/React template braces, JSX, or script-dependent blank screens. For infographic requests, obey infographic_render_mode: use custom.html only for HTML/editable/static infographic requests, and image.explanation with provider_alias="nanobanana" for polished poster/image infographic requests. For image requests, return an image.explanation app; the API server will call Gemini/Nano Banana for the real image asset, and the image should contain clear simplified Chinese text directly. Do not claim persistence, image generation, or canvas writes unless the API server reports them.
""".strip()


class HermesConfigWriter:
    def provider_name(self) -> str:
        return "gemini"

    def write(self) -> Path:
        settings = get_settings()
        home = settings.project_root / settings.hermes_home
        home.mkdir(parents=True, exist_ok=True)
        skills_dir = settings.api_root / "hermes_profile" / "skills"
        configured_skills = [item.strip() for item in settings.hermes_default_skills.split(",") if item.strip()]
        enabled_toolsets = [item.strip() for item in settings.hermes_toolsets.split(",") if item.strip()]
        soul_path = home / "SOUL.md"
        soul_path.write_text(LEARNFORGE_SOUL + "\n", encoding="utf-8")
        profile_soul_path = settings.api_root / "hermes_profile" / "SOUL.md"
        profile_soul_path.parent.mkdir(parents=True, exist_ok=True)
        profile_soul_path.write_text(LEARNFORGE_SOUL + "\n", encoding="utf-8")
        native_config_path = home / "config.yaml"
        native_config_path.write_text(
            "\n".join(
                [
                    f"provider: {self.provider_name()}",
                    f"model: {settings.gemini_text_model}",
                    f"skills_dir: {skills_dir}",
                    f"toolsets: {json.dumps(enabled_toolsets, ensure_ascii=False)}",
                    f"preloaded_skills: {json.dumps(configured_skills, ensure_ascii=False)}",
                    "hooks_auto_accept: true",
                    "profile: learnforge-v2",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        config = {
            "provider": self.provider_name(),
            "model": settings.gemini_text_model,
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "skills_dir": str(skills_dir),
            "toolsets": enabled_toolsets,
            "preloaded_skills": configured_skills,
            "soul_path": str(soul_path),
            "native_config_path": str(native_config_path),
            "integration_mode": "sdk_embedded",
            "sdk_entrypoint": "run_agent.AIAgent",
            "require_sdk": settings.hermes_require_sdk,
        }
        target = home / "learnforge_hermes_profile.json"
        target.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
