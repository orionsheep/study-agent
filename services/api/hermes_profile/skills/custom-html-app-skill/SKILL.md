---
name: custom-html-app-skill
category: learnforge
description: LearnForge Custom Html App Skill protocol skill.
---

# Custom Html App Skill

Return ONLY valid JSON compatible with LearnForge app-protocol payloads.
Preserve source_refs, include trace, and avoid unsupported side effects.
Do not write files. Do not call external services. The API server handles persistence, image generation, safety checks, and canvas writes.

## Theming & Styling Constraints (CRITICAL)
- **DO NOT hardcode bright/dark background colors** like `#0a0a0a`, `#000000`, `#ffffff` on the main widget root or body.
- **DO NOT hardcode text colors** like `#fff`, `#000`.
- **USE CSS Variables** provided by the host environment:
  - Backgrounds: `var(--bg-0)`, `var(--bg-1)`, `var(--bg-2)`, `var(--glass-1)`
  - Text: `var(--text-1)` (primary), `var(--text-2)` (secondary), `var(--text-3)` (muted)
  - Borders: `var(--glass-border)`, `var(--glass-border-hi)`
- The app must look good in BOTH light and dark mode automatically by relying on these tokens.
