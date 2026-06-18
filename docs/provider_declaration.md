# Provider Declaration

Gemini is the text/reasoning provider through `ModelGatewayRouter` and `GeminiClient`. The client reads `GEMINI_API_KEY`, `GEMINI_TEXT_MODEL`, `GEMINI_TEXT_FALLBACK_MODEL`, `GEMINI_TIMEOUT_SECONDS`, and `GEMINI_MAX_TOKENS`, and sends requests to Google Gemini `generateContent` with the official `x-goog-api-key` header.

Gemini Image is the image provider through `ImageGatewayRouter` and `GeminiImageClient`. The client reads `GEMINI_API_KEY`, `GEMINI_IMAGE_MODEL`, and `GEMINI_IMAGE_FALLBACK_MODEL`, then returns real inline image assets from Gemini. The older image2 adapter is retained only as optional compatibility status and is not part of required readiness.

Hermes is the orchestration runtime target. The runtime embeds the Hermes SDK through `run_agent.AIAgent` inside the FastAPI process, writes Gemini provider config, and syncs Hermes `SKILL.md` files. The CLI adapter is retained for diagnostics or explicit fallback, but SDK embedding is required by default through `HERMES_REQUIRE_SDK=true`.

This repository never stores real provider credentials.
