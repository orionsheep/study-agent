---
name: resource-bundle-skill
category: learnforge
description: LearnForge resource bundle orchestration skill.
---

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
- Escape all newlines inside string values as 
. Never emit raw multiline strings in JSON.
- Inline script tags and trusted HTTPS script/module URLs are allowed for custom.html interactive demos. Do not use storage APIs, dangerous protocols, event handler attributes, iframes, or forms.
- Preserve or synthesize source_refs from the supplied RAG/source_refs.
- Every app must be renderable by the LearnForge CanvasApp protocol.
- Prefer concrete app payloads over placeholders; the API server will validate, persist, call Gemini for image pixels, and stream canvas events.
