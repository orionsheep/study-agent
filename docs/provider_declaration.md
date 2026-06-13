# Provider Declaration

MiMo is the primary text/reasoning provider through `ModelGatewayRouter` and `MiMoClient`. The client reads `MIMO_API_KEY`, `MIMO_BASE_URL`, `MIMO_TEXT_MODEL`, `MIMO_FAST_MODEL`, and `MIMO_USE_THINKING`, and sends the official `api-key` request header. `MIMO_BASE_URL` can point at the MiMo pay-as-you-go API or the Token Plan API.

image2 is the image provider through `ImageGatewayRouter` and `Image2Client`. The client reads `IMAGE2_API_KEY`, `IMAGE2_BASE_URL`, and `IMAGE2_MODEL`.

Hermes is the orchestration runtime target. The runtime embeds the Hermes SDK through `run_agent.AIAgent` inside the FastAPI process, writes provider config for MiMo, and syncs Hermes `SKILL.md` files. The CLI adapter is retained for diagnostics or explicit fallback, but SDK embedding is required by default through `HERMES_REQUIRE_SDK=true`.

This repository never stores real provider credentials.
