# Blocked Real Integration Report

Status: not complete for external readiness.

Generated: `2026-06-04T04:52:39+00:00`

The product implements real integration paths, but this machine does not currently prove all external providers ready.

Current `/api/system/status` proof:

- `overall`: `blocked_external`
- `database`: `ready`
- `edumem0`: `ready`
- `rag`: `ready`

External blockers:

- MiMo: `ready` - MiMo OpenAI-compatible endpoint responded.
- image2: `blocked_missing_credentials` - IMAGE2_API_KEY or IMAGE2_BASE_URL is missing; real provider check was not attempted.
- Hermes: `ready` - Hermes SDK embedded via run_agent.AIAgent; provider=mimo; api_mode=chat_completions; model=mimo-v2.5-pro.

Next commands:

```bash
test -f .env || cp .env.example .env
# MiMo is currently ready; keep MIMO_API_KEY and MIMO_BASE_URL in local .env for future checks.
# Add IMAGE2_API_KEY and IMAGE2_BASE_URL when image2 should be enabled.
# Hermes SDK is currently ready; keep hermes-agent installed in the API venv or set HERMES_SDK_PATH.
docker compose up -d postgres redis
. .venv/bin/activate
export HERMES_REQUIRE_SDK=true
DATABASE_URL=postgresql+asyncpg://learnforge:learnforge@localhost:5432/learnforge uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/api/system/status
python scripts/check_hermes_sdk_embedding.py
hermes version  # optional CLI diagnostic; SDK embedding is the product integration path
```

Do not mark the goal complete until `/api/system/status` reports MiMo, image2, and Hermes ready or the user provides a runtime environment where those checks can succeed.
