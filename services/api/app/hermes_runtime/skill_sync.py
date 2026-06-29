from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from app.core.config import get_settings


REQUIRED_HERMES_SKILLS = [
    "document-skill",
    "mindmap-skill",
    "quiz-skill",
    "guizang-ppt-skill",
    "code-practice-skill",
    "image-generation-skill",
    "video-script-skill",
    "reading-material-skill",
    "notes-skill",
    "dashboard-skill",
    "cram-engine-skill",
    "resource-bundle-skill",
    "app-generation-skill",
    "custom-html-app-skill",
    "verifier-skill",
    "memory-update-skill",
    "course-ingestion-skill",
    "detailed-analysis-skill",
]

VENDORED_HERMES_SKILLS = {
    "guizang-ppt-skill": Path("hermes_profile/vendor/guizang-ppt-skill"),
    "detailed-analysis-skill": Path("hermes_profile/vendor/detailed-analysis-skill"),
}

RESOURCE_BUNDLE_CONTRACT = """
# Resource Bundle Skill

Use this skill when LearnForge asks for learning resources, infographic, mindmap, quiz, PPT, code lab, video script, or canvas apps.

Return ONLY valid JSON. No markdown fences. No prose outside JSON.

Required shape:
{
  "summary": "short Chinese summary",
  "trace": ["detected_intent", "generated_resources", "planned_canvas_apps"],
  "resources": [
    {
      "type": "document|mindmap|quiz|reading|code_practice|ppt|video_script|image|notes",
      "title": "Chinese title",
      "target_topic": "topic",
      "difficulty": "adaptive",
      "content": {},
      "source_refs": [{"source_id":"...","title":"...","locator":"..."}],
      "personalized_reason": "why it fits the student",
      "tags": ["..."]
    }
  ],
  "apps": [
    {
      "app_type": "custom.html|mindmap.concept|quiz.practice|code.lab|ppt.preview|video.script|video.player|image.explanation|notes.session|resource.center|physics.work_energy_demo|math.gradient_descent_demo",
      "title": "Chinese title",
      "resource_index": 0,
      "payload": {},
      "personalized_reason": "why this app should appear on canvas"
    }
  ]
}

Rules:
- Generate at least 5 resources for a resource bundle.
- For infographic requests, obey expected_app_types and infographic_render_mode.
- If infographic_render_mode is image or expected_app_types contains image.explanation, include an image.explanation app with payload.topic, payload.teaching_goal, payload.visual_brief, payload.provider_alias="nanobanana", and payload.overlay_labels. Do not include custom.html unless explicitly requested.
- If infographic_render_mode is html or expected_app_types contains custom.html, include a polished self-contained custom.html app with inline CSS and real visible Chinese learning content. Static infographics should cover: 标题与目标、核心直觉、可视化主体、步骤/公式、例题、常见误区、自测题、下一步建议. For interactive_demo, do not return the generic lfx-lab dashboard/card layout. Build a topic-specific simulation with a real visual scene, inline script, animation loop, sliders/buttons, and drag or pointer interaction where useful. You may use trusted HTTPS JavaScript libraries/modules such as Three.js for 3D/WebGL models when appropriate. For a quadratic-function request, draw actual axes and a parabola, animate coefficient changes, expose a/b/c/x controls, show vertex/symmetry axis/roots/discriminant, and never mention learning rate, gradient descent, springs, or generic 输入·动作·输出 copy. For a sorting-algorithm request, render actual bars or Canvas animation with compare/swap/move states, algorithm selection, speed controls, step mode, and metrics; never output raw currentAlgoInfo, arraySize, or other Vue/React template variables. Do not include fake buttons, empty containers, inert charts, iframes, forms, event handler attributes, English placeholder text, LABEL placeholders, raw Vue/React template braces, JSX, or script-dependent blank stages.
- For interactive_demo quality, internally follow four roles before final JSON: Demo Architect, Graphics Engineer, Interaction Engineer, and QA Verifier. Build an actual topic-specific demo runtime with state, compute/update, render, input-controller, and a nonblank first frame. Do not return generic concept cards, lfx-lab dashboards, Input/Action/Output shells, or backend-template placeholders. Infer the topic's variables, objects, equations, states, and interactions at generation time. For science/physics topics, use a continuous animated model with particles/vector fields/force or energy overlays, live readouts, conservation/error readouts when applicable, and equation terms that visibly change with controls. For 3D/spatial topics, use a separate control panel plus model stage so controls never cover the scene; add orbit/zoom/reset/readouts. For Bernoulli/fluid/Venturi, render a narrowing pipe, continuity-driven velocity, accelerated particles with trails, pressure-color field, streamlines/velocity arrows, manometers, and live Bernoulli energy-term bars. For Rubik's cube / 魔方, render a complete 3x3x3 model or equivalent with U/U'/D/D'/F/F'/B/B'/R/R'/L/L', scramble, reset, undo/demo playback, visible queue/readouts, and camera controls. Every button must have data-action or data-move and a delegated addEventListener handler; no dead buttons.
- For image, drawing, illustration, or teaching-diagram requests, include an image resource and an image.explanation app with payload.topic, payload.teaching_goal, payload.visual_brief, payload.provider_alias, and payload.overlay_labels. Ask the image model for simplified Chinese text inside the image, not English labels or frontend-only label areas.
- For physics.work_energy_demo or math.gradient_descent_demo, return compact JSON payload values only; do not return custom HTML or code.
- Escape all newlines inside string values as \n. Never emit raw multiline strings in JSON.
- Inline script tags and trusted HTTPS script/module URLs are allowed for custom.html interactive demos. Do not use storage APIs, dangerous protocols, event handler attributes, iframes, or forms.
- Preserve or synthesize source_refs from the supplied RAG/source_refs.
- Every app must be renderable by the LearnForge CanvasApp protocol.
- Prefer concrete app payloads over placeholders; the API server will validate, persist, call Gemini for image pixels, and stream canvas events.
"""

CRAM_ENGINE_CONTRACT = """
# Cram Engine Skill

Use this skill when LearnForge asks for exam sprint learning,期末速成,考前冲刺,突击复习,or Cram-style study planning.

Return ONLY valid JSON. No markdown fences. No prose outside JSON.

Required shape:
{
  "capability": "exam_cram",
  "summary": "short Chinese summary",
  "trace": ["exam_mode_classified", "openstax_sources_selected", "cram_session_created"],
  "resources": [
    {
      "type": "reading|quiz|notes",
      "title": "Chinese title",
      "target_topic": "topic",
      "difficulty": "adaptive",
      "content": {},
      "source_refs": [{"source_id":"openstax:<slug>","title":"OpenStax book title","locator":"chapter or concept"}],
      "personalized_reason": "why it supports the sprint",
      "tags": ["cram","openstax"]
    }
  ],
  "apps": [
    {
      "app_type": "exam.cram",
      "title": "期末速成",
      "payload": {
        "course_title": "course or exam title",
        "stage": "deconstruct|teach|test|remediate|summary",
        "exam_mode": "conceptual_cram|practice_heavy",
        "must_know": ["high-priority knowledge point"],
        "key_points": ["supporting point"],
        "next_actions": ["下一步动作"]
      },
      "personalized_reason": "why this sprint is appropriate"
    },
    {
      "app_type": "dashboard.learning",
      "title": "学习仪表盘",
      "payload": {"active_tab":"overview"},
      "personalized_reason": "show cram progress with the rest of the student's learning data"
    },
    {
      "app_type": "quiz.practice",
      "title": "速成诊断题",
      "payload": {"questions":[]},
      "personalized_reason": "validate the current cram batch"
    }
  ]
}

Rules:
- Follow the cram-engine loop: 1) deconstruct exam scope into must-know/key-point nodes, 2) teach the next compact batch with memory hooks, 3) generate diagnostic questions, 4) remediate wrong/stubborn points and summarize.
- Prefer OpenStax sources when they match the course. Use source_refs with `openstax:<slug>` ids and real book titles.
- Classify exam_mode as `practice_heavy` for calculation/problem-heavy exams, otherwise `conceptual_cram`.
- Do not substitute generic resource.center or custom.html for the primary app. The primary app_type MUST be `exam.cram`.
- Keep generated content general and capability-level; do not hardcode one demo topic.
"""

GENERIC_SKILL_CONTRACT = """
Return ONLY valid JSON compatible with LearnForge app-protocol payloads.
Preserve source_refs, include trace, and avoid unsupported side effects.
Do not write files. Do not call external services. The API server handles persistence, image generation, safety checks, and canvas writes.
"""


class HermesSkillSync:
    def skills_root(self) -> Path:
        return get_settings().api_root / "hermes_profile" / "skills"

    def hermes_home_skills_root(self) -> Path:
        settings = get_settings()
        return settings.project_root / settings.hermes_home / "skills"

    def skill_body(self, name: str) -> str:
        title = name.replace("-", " ").title()
        description = (
            "LearnForge resource bundle orchestration skill."
            if name == "resource-bundle-skill"
            else "LearnForge exam sprint / Cram Engine orchestration skill."
            if name == "cram-engine-skill"
            else f"LearnForge {title} protocol skill."
        )
        if name == "resource-bundle-skill":
            contract = RESOURCE_BUNDLE_CONTRACT
        elif name == "cram-engine-skill":
            contract = CRAM_ENGINE_CONTRACT
        else:
            contract = f"# {title}\n\n{GENERIC_SKILL_CONTRACT}\n"
        return (
            "---\n"
            f"name: {name}\n"
            "category: learnforge\n"
            f"description: {description}\n"
            "---\n\n"
            f"{contract.strip()}\n"
        )

    def vendor_skill_source(self, name: str) -> Path | None:
        relative = VENDORED_HERMES_SKILLS.get(name)
        if not relative:
            return None
        return get_settings().api_root / relative

    def build_skill_catalog(self) -> str:
        """Read all SKILL.md files and extract name + description from YAML frontmatter.

        Returns a Markdown-formatted catalog for inclusion in the unified Hermes prompt.
        """
        entries: list[str] = []
        primary_root = self.skills_root()
        for name in REQUIRED_HERMES_SKILLS:
            skill_dir = primary_root / name
            md_path = skill_dir / "SKILL.md"
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
                if frontmatter_match:
                    try:
                        metadata = yaml.safe_load(frontmatter_match.group(1)) or {}
                    except Exception:
                        metadata = {}
                    desc = metadata.get("description", f"LearnForge {name}")
                else:
                    desc = f"LearnForge {name}"
            else:
                desc = f"LearnForge {name}"
            entries.append(f"- **{name}**: {desc}")
        return "\n".join(entries)

    def sync_vendored_skill(self, name: str, destination: Path) -> None:
        source = self.vendor_skill_source(name)
        if not source or not source.exists():
            raise FileNotFoundError(f"vendored Hermes skill is missing: {name} at {source}")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)

    def sync(self) -> list[Path]:
        written: list[Path] = []
        primary_root = self.skills_root()
        for root in (self.skills_root(), self.hermes_home_skills_root()):
            root.mkdir(parents=True, exist_ok=True)
            for name in REQUIRED_HERMES_SKILLS:
                skill_dir = root / name
                path = skill_dir / "SKILL.md"
                if name in VENDORED_HERMES_SKILLS:
                    self.sync_vendored_skill(name, skill_dir)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(self.skill_body(name), encoding="utf-8")
                if root == primary_root:
                    written.append(path)
        return written

    def complete(self) -> bool:
        return all((root / name / "SKILL.md").exists() for root in (self.skills_root(), self.hermes_home_skills_root()) for name in REQUIRED_HERMES_SKILLS)
