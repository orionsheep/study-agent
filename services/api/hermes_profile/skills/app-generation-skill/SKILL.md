---
name: app-generation-skill
category: learnforge
description: LearnForge App Generation Skill protocol skill.
---

# App Generation Skill


Return ONLY valid JSON compatible with LearnForge app-protocol payloads.
Preserve source_refs, include trace, and avoid unsupported side effects.
Do not write files. Do not call external services. The API server handles persistence, image generation, safety checks, and canvas writes.
