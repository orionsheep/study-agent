# Source Truth Manifest

Pack root: `/Users/mychanging/Downloads/learnforge_v4_all_requirements_test_gated_goal_pack`

Every non-OS file in the requirement pack is inventoried here with a hash and product evidence path. `.DS_Store` is excluded as OS metadata.

| Pack file | SHA-256 | Role | Product evidence |
| --- | --- | --- | --- |
| `.omx/logs/omx-2026-06-03.jsonl` | `cc5c593dd34daee6` | pack operational metadata | `RUN_REPORT.md` |
| `.omx/state/native-stop-state.json` | `9b82d0fc504aa532` | pack operational metadata | `RUN_REPORT.md` |
| `.omx/state/session.json` | `bdd2ab80abc0dfc8` | pack operational metadata | `RUN_REPORT.md` |
| `AGENT_TOPOLOGY_REQUIRED.md` | `803c93a0d3d44e1b` | requirements source document | `services/api/app/agents`, `docs/agent_design.md`, `docs/agents` |
| `APP_CANVAS_REQUIRED.md` | `fc63076c54430566` | requirements source document | `apps/web/src/features/app-canvas`, `docs/app_canvas_design.md` |
| `APP_PROTOCOL_REQUIRED.md` | `b8affa0a4d9173b8` | requirements source document | `packages/app-protocol/src/types.ts`, `services/api/app/schemas/app_protocol.py` |
| `AUDIT_V3_GAPS.md` | `ccb377b7180e851f` | requirements source document | `validation/requirement_results.json`, `BLOCKED_REAL_INTEGRATION_REPORT.md` |
| `BACKEND_RUNTIME_REQUIRED.md` | `0cbca8566f12583d` | requirements source document | `services/api/app/main.py`, `services/api/tests/test_health_routes.py` |
| `COMPETITION_TRACEABILITY_REQUIRED.md` | `139601d695e02ad4` | requirements source document | `docs/competition_traceability.md`, `docs/demo_script.md` |
| `CUSTOM_GENERATIVE_UI_REQUIRED.md` | `aeb3c4868d799435` | requirements source document | `apps/web/src/features/custom-html-app`, `services/api/app/skills/custom_html_app_skill.py` |
| `DASHBOARD_LEARNING_LOOP_REQUIRED.md` | `4344ace4f6e8ab6e` | requirements source document | `apps/web/src/features/learning-apps/NativeAppRenderer.tsx`, `services/api/app/skills/dashboard_skill.py` |
| `DATABASE_SCHEMA_DRAFT.sql` | `017238b0ec6fb509` | database schema source | `services/api/app/database/postgres_schema.sql`, `services/api/app/database/schema.py` |
| `DELIVERABLES_REQUIRED.md` | `5f8604e01490bd70` | requirements source document | `RUN_REPORT.md`, `docs/test_report.md`, `validation/requirement_results.json` |
| `FRONTEND_PRODUCT_REQUIRED.md` | `bd75b2cf9e9c0585` | requirements source document | `apps/web/src/app/LearnForgeApp.tsx`, `apps/web/src/app/styles.css` |
| `FULL_GOAL_COMMAND.md` | `2e7c88eeb23ac394` | requirements source document | `RUN_REPORT.md`, `BLOCKED_REAL_INTEGRATION_REPORT.md`, `docs/runbook.md` |
| `HERMES_MIMO_IMAGE2_REQUIRED.md` | `47bdd3a6dd6402f8` | requirements source document | `services/api/app/hermes_runtime`, `services/api/app/model_gateway/mimo_client.py`, `services/api/app/image_gateway/image2_client.py` |
| `IMPLEMENT_FULL_PRODUCT.md` | `873d3034ee82569e` | requirements source document | `RUN_REPORT.md`, `scripts/run_full_validation.sh` |
| `MEMORY_SYSTEM_REQUIRED.md` | `404d666840a9cd90` | requirements source document | `services/api/app/edumem0`, `docs/memory_design.md` |
| `NATIVE_LEARNING_APPS_REQUIRED.md` | `f1ebaf090ac94734` | requirements source document | `apps/web/src/features/learning-apps/NativeAppRenderer.tsx`, `packages/learning-apps/src/index.ts` |
| `NO_MOCK_POLICY.md` | `4fbd3acf22d6cce5` | requirements source document | `scripts/verify_no_mock_runtime.sh`, `BLOCKED_REAL_INTEGRATION_REPORT.md` |
| `OPEN_SOURCE_RESEARCH_AND_CHOICES.md` | `bdb1abc44d43fb1e` | requirements source document | `docs/open_source_licenses.md`, `docs/provider_declaration.md` |
| `RAG_SAFETY_VERIFIER_REQUIRED.md` | `0309fd80528e87f4` | requirements source document | `services/api/app/rag`, `services/api/app/safety`, `docs/rag_safety_design.md` |
| `README.md` | `945db298dc7b16be` | requirements source document | `RUN_REPORT.md`, `docs/architecture.md` |
| `RESOURCE_SKILLS_REQUIRED.md` | `7344f49290e7b917` | requirements source document | `services/api/app/skills`, `services/api/hermes_profile/skills` |
| `SECRETS_POLICY.md` | `04b994a99f4effdb` | requirements source document | `scripts/secret_scan.sh`, `.gitignore`, `.env.example` |
| `TARGET_PROJECT_STRUCTURE.md` | `6098e7904b00cb09` | requirements source document | `scripts/verify_project_structure.py`, `docs/architecture.md` |
| `TEST_STANDARDS_REQUIRED.md` | `352f9cacab761e1d` | requirements source document | `scripts/run_full_validation.sh`, `docs/test_report.md` |
| `USER_REQUIREMENT_TRACE.md` | `0dece29ed248b6d2` | requirements source document | `validation/requirement_results.json`, `docs/competition_traceability.md` |
| `prompts/START_GOAL.md` | `23a33af2ea389d5d` | goal prompt | `RUN_REPORT.md`, `BLOCKED_REAL_INTEGRATION_REPORT.md`, `docs/runbook.md` |
| `requirements/requirements.json` | `c96394ac7e0fcb3a` | machine-readable acceptance contract | `requirements/requirements.json`, `validation/requirement_results.json`, `scripts/verify_requirement_results.py` |
| `scripts/verify_full_contract_template.py` | `64e7e040b9fe6a78` | validation template | `scripts/run_full_validation.sh`, `scripts/verify_full_contract.py`, `scripts/verify_no_mock_runtime.sh` |
| `scripts/verify_no_mock_runtime_template.sh` | `75bf650db458665b` | validation template | `scripts/run_full_validation.sh`, `scripts/verify_full_contract.py`, `scripts/verify_no_mock_runtime.sh` |
| `scripts/verify_pack_integrity.py` | `f279514a74453eba` | validation template | `scripts/run_full_validation.sh`, `scripts/verify_full_contract.py`, `scripts/verify_no_mock_runtime.sh` |
| `sources/RESEARCH_SOURCES.md` | `ff83782f21633e72` | research/source inventory | `docs/open_source_licenses.md`, `docs/provider_declaration.md`, `docs/competition_traceability.md` |
| `templates/.env.example` | `f0cbbb6352ae6205` | implementation template | `.env.example`, `.gitignore`, `packages/app-protocol/src/types.ts`, `services/api/app/edumem0/schemas.py` |
| `templates/.gitignore` | `4470c21021f764e2` | implementation template | `.env.example`, `.gitignore`, `packages/app-protocol/src/types.ts`, `services/api/app/edumem0/schemas.py` |
| `templates/app-protocol-types.ts` | `e7b33fddbc004abf` | implementation template | `.env.example`, `.gitignore`, `packages/app-protocol/src/types.ts`, `services/api/app/edumem0/schemas.py` |
| `templates/edumem0_schemas.py` | `e9828efe14dda66d` | implementation template | `.env.example`, `.gitignore`, `packages/app-protocol/src/types.ts`, `services/api/app/edumem0/schemas.py` |
