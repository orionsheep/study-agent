# LearnForge Agent Smoke Checks

`npm run agent:smoke` is a manual end-to-end smoke suite for the Hermes + Canvas Agent loop. It is intentionally not part of the default `npm test` command because it can call live model providers and may take several minutes.

## Prerequisites

Start the API server first:

```bash
uv run --project services/api uvicorn app.main:app --host 127.0.0.1 --port 8001
```

By default the smoke suite targets:

```bash
http://127.0.0.1:8001
```

Override it when needed:

```bash
LEARNFORGE_API_BASE=http://127.0.0.1:8000 npm run agent:smoke -- --all
```

## Run all core checks

```bash
npm run agent:smoke -- --all
```

## Run selected checks

```bash
npm run agent:smoke -- fresh-canvas
npm run agent:smoke -- image
npm run agent:smoke -- interactive-demo
npm run agent:smoke -- notes-context
```

## What it verifies

- `fresh-canvas`: a new conversation shows only seed apps and does not leak generated apps from old conversations.
- `image`: a teaching image request creates an `image.explanation` app with a Gemini `data:image/...` URL and a fullscreen AppLink.
- `interactive-demo`: a physics work-energy request creates a `physics.work_energy_demo` app and a fullscreen AppLink. Hermes provider fallback must not leave `hermes_runtime` failed.
- `notes-context`: summarizing the previous sorting-algorithm answer creates exactly one generated `notes.session` app bound to `排序算法`, without stale gradient-descent context.

## Expected success output

The command prints one `ok` line per check and then a JSON summary with generated conversation IDs and app titles.

If a check fails, the script exits non-zero and prints the failing artifact details.
