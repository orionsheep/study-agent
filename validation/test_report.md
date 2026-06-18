# LearnForge V2 Validation Report

Started: 2026-06-17T03:54:22Z
Project structure verified
Wrote 39 source-truth manifest entries
External readiness proof written
{
  "overall": "ready",
  "gemini": "ready",
  "gemini_image": "ready",
  "hermes": "ready",
  "object_storage": "ready",
  "image2_optional": "blocked_missing_credentials",
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
Artifact boundary validation passed
........................................................................ [ 47%]
...................................................................s.... [ 94%]
.........                                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /Users/mychanging/Downloads/learnforge-v2-product/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_agents_and_skills.py: 286 warnings
tests/test_auth_onboarding.py: 339 warnings
tests/test_chat_message_links.py: 14 warnings
tests/test_component_naming.py: 8 warnings
tests/test_edumem0_policies.py: 9 warnings
tests/test_memory_closed_loop.py: 141 warnings
tests/test_memory_end_to_end.py: 20 warnings
tests/test_memory_security_isolation.py: 17 warnings
tests/test_protocol_compatibility.py: 7 warnings
tests/test_rag_verifier.py: 9 warnings
tests/test_streaming_events.py: 51 warnings
  /Users/mychanging/Downloads/learnforge-v2-product/services/api/app/schemas/app_protocol.py:52: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

tests/test_edumem0_policies.py::test_decay_policy_keeps_spatial_layout_stable
  /Users/mychanging/Downloads/learnforge-v2-product/services/api/tests/test_edumem0_policies.py:20: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    decayed = policy.apply(0.8, 0.08, datetime.utcnow() - timedelta(days=7))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
152 passed, 1 skipped, 903 warnings in 49.50s

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
✓ 2342 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                         0.48 kB │ gzip:   0.31 kB
dist/assets/KaTeX_Size3-Regular-CTq5MqoE.woff           4.42 kB
dist/assets/KaTeX_Size4-Regular-Dl5lxZxV.woff2          4.93 kB
dist/assets/KaTeX_Size2-Regular-Dy4dx90m.woff2          5.21 kB
dist/assets/KaTeX_Size1-Regular-mCD8mA8B.woff2          5.47 kB
dist/assets/KaTeX_Size4-Regular-BF-4gkZK.woff           5.98 kB
dist/assets/KaTeX_Size2-Regular-oD1tc_U0.woff           6.19 kB
dist/assets/KaTeX_Size1-Regular-C195tn64.woff           6.50 kB
dist/assets/KaTeX_Caligraphic-Regular-Di6jR-x-.woff2    6.91 kB
dist/assets/KaTeX_Caligraphic-Bold-Dq_IR9rO.woff2       6.91 kB
dist/assets/KaTeX_Size3-Regular-DgpXs0kz.ttf            7.59 kB
dist/assets/KaTeX_Caligraphic-Regular-CTRA-rTL.woff     7.66 kB
dist/assets/KaTeX_Caligraphic-Bold-BEiXGLvX.woff        7.72 kB
dist/assets/KaTeX_Script-Regular-D3wIWfF6.woff2         9.64 kB
dist/assets/KaTeX_SansSerif-Regular-DDBCnlJ7.woff2     10.34 kB
dist/assets/KaTeX_Size4-Regular-DWFBv043.ttf           10.36 kB
dist/assets/KaTeX_Script-Regular-D5yQViql.woff         10.59 kB
dist/assets/KaTeX_Fraktur-Regular-CTYiF6lA.woff2       11.32 kB
dist/assets/KaTeX_Fraktur-Bold-CL6g_b3V.woff2          11.35 kB
dist/assets/KaTeX_Size2-Regular-B7gKUWhC.ttf           11.51 kB
dist/assets/KaTeX_SansSerif-Italic-C3H0VqGB.woff2      12.03 kB
dist/assets/KaTeX_SansSerif-Bold-D1sUS0GD.woff2        12.22 kB
dist/assets/KaTeX_Size1-Regular-Dbsnue_I.ttf           12.23 kB
dist/assets/KaTeX_SansSerif-Regular-CS6fqUqJ.woff      12.32 kB
dist/assets/KaTeX_Caligraphic-Regular-wX97UBjC.ttf     12.34 kB
dist/assets/KaTeX_Caligraphic-Bold-ATXxdsX0.ttf        12.37 kB
dist/assets/KaTeX_Fraktur-Regular-Dxdc4cR9.woff        13.21 kB
dist/assets/KaTeX_Fraktur-Bold-BsDP51OF.woff           13.30 kB
dist/assets/KaTeX_Typewriter-Regular-CO6r4hn1.woff2    13.57 kB
dist/assets/KaTeX_SansSerif-Italic-DN2j7dab.woff       14.11 kB
dist/assets/KaTeX_SansSerif-Bold-DbIhKOiC.woff         14.41 kB
dist/assets/KaTeX_Typewriter-Regular-C0xS9mPB.woff     16.03 kB
dist/assets/KaTeX_Math-BoldItalic-CZnvNsCZ.woff2       16.40 kB
dist/assets/KaTeX_Math-Italic-t53AETM-.woff2           16.44 kB
dist/assets/KaTeX_Script-Regular-C5JkGWo-.ttf          16.65 kB
dist/assets/KaTeX_Main-BoldItalic-DxDJ3AOS.woff2       16.78 kB
dist/assets/KaTeX_Main-Italic-NWA7e6Wa.woff2           16.99 kB
dist/assets/KaTeX_Math-BoldItalic-iY-2wyZ7.woff        18.67 kB
dist/assets/KaTeX_Math-Italic-DA0__PXp.woff            18.75 kB
dist/assets/KaTeX_Main-BoldItalic-SpSLRI95.woff        19.41 kB
dist/assets/KaTeX_SansSerif-Regular-BNo7hRIc.ttf       19.44 kB
dist/assets/KaTeX_Fraktur-Regular-CB_wures.ttf         19.57 kB
dist/assets/KaTeX_Fraktur-Bold-BdnERNNW.ttf            19.58 kB
dist/assets/KaTeX_Main-Italic-BMLOBm91.woff            19.68 kB
dist/assets/KaTeX_SansSerif-Italic-YYjJ1zSn.ttf        22.36 kB
dist/assets/KaTeX_SansSerif-Bold-CFMepnvq.ttf          24.50 kB
dist/assets/KaTeX_Main-Bold-Cx986IdX.woff2             25.32 kB
dist/assets/KaTeX_Main-Regular-B22Nviop.woff2          26.27 kB
dist/assets/KaTeX_Typewriter-Regular-D3Ib7_Hf.ttf      27.56 kB
dist/assets/KaTeX_AMS-Regular-BQhdFMY1.woff2           28.08 kB
dist/assets/KaTeX_Main-Bold-Jm3AIy58.woff              29.91 kB
dist/assets/KaTeX_Main-Regular-Dr94JaBh.woff           30.77 kB
dist/assets/KaTeX_Math-BoldItalic-B3XSjfu4.ttf         31.20 kB
dist/assets/KaTeX_Math-Italic-flOr_0UB.ttf             31.31 kB
dist/assets/KaTeX_Main-BoldItalic-DzxPMmG6.ttf         32.97 kB
dist/assets/KaTeX_AMS-Regular-DMm9YOAa.woff            33.52 kB
dist/assets/KaTeX_Main-Italic-3WenGoN9.ttf             33.58 kB
dist/assets/KaTeX_Main-Bold-waoOVXN0.ttf               51.34 kB
dist/assets/KaTeX_Main-Regular-ypZvNtVU.ttf            53.58 kB
dist/assets/KaTeX_AMS-Regular-DRggAlZN.ttf             63.63 kB
dist/assets/index-MtpkOVXm.css                        138.26 kB │ gzip:  29.11 kB
dist/assets/index-BS-CXd0h.js                         931.16 kB │ gzip: 289.49 kB
✓ built in 1.44s

> learnforge-v2-product@0.1.0 web:test
> npm --workspace apps/web run test


> @learnforge/web@0.1.0 test
> vitest run


 RUN  v3.2.6 /Users/mychanging/Downloads/learnforge-v2-product/apps/web

 ✓ tests/focusApp.test.ts (1 test) 1ms
 ✓ tests/calculations.test.ts (2 tests) 1ms
 ✓ tests/agentEvents.test.ts (2 tests) 3ms
 ✓ src/lib/events/agentEvents.test.ts (1 test) 2ms
 ✓ tests/widgetParser.test.ts (13 tests) 4ms
 ✓ tests/renderers.test.tsx (19 tests) 142ms

 Test Files  6 passed (6)
      Tests  38 passed (38)
   Start at  11:55:29
   Duration  932ms (transform 258ms, setup 0ms, collect 575ms, tests 153ms, environment 1.40s, prepare 294ms)

React Flow scope verified
No forbidden mock runtime patterns found
Secret scan passed
Artifact boundary validation passed
Backend smoke passed
Web smoke passed

> learnforge-v2-product@0.1.0 web:e2e
> npm --workspace apps/web run e2e


> @learnforge/web@0.1.0 e2e
> playwright test


Running 9 tests using 1 worker

  ✓  1 [chromium] › e2e/product-flow.spec.ts:76:1 › loads product with left canvas and right Tutor Chat (748ms)
  ✓  2 [chromium] › e2e/product-flow.spec.ts:98:1 › chat stream creates AppLink and AppLink Flight focuses target App (671ms)
  ✓  3 [chromium] › e2e/product-flow.spec.ts:118:1 › chat trace renders Hermes activity and Gemini answer (609ms)
  ✓  4 [chromium] › e2e/product-flow.spec.ts:140:1 › assistant output renders Markdown and show-widget rich content (603ms)
  ✓  5 [chromium] › e2e/product-flow.spec.ts:169:1 › WorkEnergy sliders update formula outputs (469ms)
  ✓  6 [chromium] › e2e/product-flow.spec.ts:174:1 › Quiz submit surface shows diagnostic resources and dashboard memory evidence (481ms)
  ✓  7 [chromium] › e2e/product-flow.spec.ts:181:1 › LearningPath dock and canvas controls work (813ms)
  ✓  8 [chromium] › e2e/product-flow.spec.ts:210:1 › Notes App summary action sends chat request (778ms)
  ✓  9 [chromium] › e2e/product-flow.spec.ts:224:1 › enabled controls expose an action label or title (485ms)

  9 passed (6.5s)
Wrote 111 requirement results to /Users/mychanging/Downloads/learnforge-v2-product/validation/requirement_results.json
All 111 requirements pass
Full product contract verified

Finished: 2026-06-17T03:55:45Z
