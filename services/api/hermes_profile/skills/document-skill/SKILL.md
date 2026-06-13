---
name: document-skill
category: learnforge
description: LearnForge Document Skill protocol skill.
---

# Document Skill


Return ONLY valid JSON compatible with LearnForge app-protocol payloads.
Preserve source_refs, include trace, and avoid unsupported side effects.
Do not write files. Do not call external services. The API server handles persistence, image generation, safety checks, and canvas writes.
