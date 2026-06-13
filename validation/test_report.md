# LearnForge V2 Validation Report

Started: 2026-06-04T04:52:35Z
Project structure verified
Wrote 38 source-truth manifest entries
External readiness proof written
{
  "overall": "blocked_external",
  "mimo": "ready",
  "image2": "blocked_missing_credentials",
  "hermes": "ready",
  "hermes_adapter": "python_aiagent_sdk",
  "hermes_integration_mode": "sdk_embedded"
}
Hermes SDK embedding proof written
{
  "status": "ready",
  "adapter": "python_aiagent_sdk",
  "integration_mode": "sdk_embedded",
  "sdk_module": "run_agent",
  "sdk_version": "0.14.0",
  "embedded_agent_class": "run_agent.AIAgent",
  "sdk_path": "/Users/mychanging/Obsidian本地仓库/2026是最后的交汇点-起飞/.hermes/hermes-agent/run_agent.py"
}
...................................                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/mychanging/Downloads/learnforge-v2-product/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_agents_and_skills.py: 74 warnings
tests/test_edumem0_policies.py: 9 warnings
tests/test_memory_end_to_end.py: 19 warnings
tests/test_protocol_compatibility.py: 7 warnings
tests/test_streaming_events.py: 6 warnings
  /Users/mychanging/Downloads/learnforge-v2-product/services/api/app/schemas/app_protocol.py:49: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

tests/test_edumem0_policies.py::test_decay_policy_keeps_spatial_layout_stable
  /Users/mychanging/Downloads/learnforge-v2-product/services/api/tests/test_edumem0_policies.py:20: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    decayed = policy.apply(0.8, 0.08, datetime.utcnow() - timedelta(days=7))

tests/test_edumem0_policies.py::test_decay_policy_keeps_spatial_layout_stable
  /Users/mychanging/Downloads/learnforge-v2-product/services/api/app/edumem0/decay_policy.py:19: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    current = now or datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
35 passed, 118 warnings in 1.70s

> learnforge-v2-product@0.1.0 web:lint
> npm --workspace apps/web run lint


> @learnforge/web@0.1.0 lint
> tsc --noEmit


> learnforge-v2-product@0.1.0 web:build
> npm --workspace apps/web run build


> @learnforge/web@0.1.0 build
> tsc --noEmit && vite build

vite v6.4.3 building for production...
transforming...
✓ 2295 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-CrwRT1jx.css   37.95 kB │ gzip:   8.49 kB
dist/assets/index-CgPh1qqQ.js   540.65 kB │ gzip: 170.46 kB
✓ built in 1.09s

> learnforge-v2-product@0.1.0 web:test
> npm --workspace apps/web run test


> @learnforge/web@0.1.0 test
> vitest run


 RUN  v3.2.6 /Users/mychanging/Downloads/learnforge-v2-product/apps/web

 ✓ tests/focusApp.test.ts (1 test) 1ms
 ✓ tests/calculations.test.ts (2 tests) 2ms
 ✓ tests/widgetParser.test.ts (3 tests) 2ms
 ✓ tests/agentEvents.test.ts (1 test) 2ms
 ✓ tests/renderers.test.tsx (3 tests) 33ms

 Test Files  5 passed (5)
      Tests  10 passed (10)
   Start at  12:52:47
   Duration  668ms (transform 118ms, setup 0ms, collect 269ms, tests 39ms, environment 1.55s, prepare 196ms)

React Flow scope verified
No forbidden mock runtime patterns found
Secret scan passed
Backend smoke passed
Web smoke passed

> learnforge-v2-product@0.1.0 web:e2e
> npm --workspace apps/web run e2e


> @learnforge/web@0.1.0 e2e
> playwright test


Running 9 tests using 1 worker

  ✓  1 [chromium] › e2e/product-flow.spec.ts:51:1 › loads product with left canvas and right Tutor Chat (880ms)
  ✓  2 [chromium] › e2e/product-flow.spec.ts:73:1 › chat stream creates AppLink and AppLink Flight focuses target App (703ms)
  ✓  3 [chromium] › e2e/product-flow.spec.ts:96:1 › chat trace exposes the MiMo model gateway step (535ms)
  ✓  4 [chromium] › e2e/product-flow.spec.ts:119:1 › assistant output renders Markdown and show-widget rich content (551ms)
  ✓  5 [chromium] › e2e/product-flow.spec.ts:148:1 › WorkEnergy sliders update formula outputs (466ms)
  ✓  6 [chromium] › e2e/product-flow.spec.ts:155:1 › Quiz submit shows feedback and dashboard memory evidence (2.0s)
  ✓  7 [chromium] › e2e/product-flow.spec.ts:168:1 › LearningPath stage click focuses App and canvas controls work (1.1s)
  ✓  8 [chromium] › e2e/product-flow.spec.ts:194:1 › Notes App creation from chat summary works (514ms)
  ✓  9 [chromium] › e2e/product-flow.spec.ts:207:1 › enabled controls expose an action label or title (456ms)

  9 passed (8.3s)
Wrote 111 requirement results to /Users/mychanging/Downloads/learnforge-v2-product/validation/requirement_results.json
All 111 requirements pass
Full product contract verified

Finished: 2026-06-04T04:53:18Z
