#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path.cwd()
PACK = ROOT.parent / "learnforge_v4_all_requirements_test_gated_goal_pack"
REQ_FILE = PACK / "requirements" / "requirements.json"
if not REQ_FILE.exists():
    REQ_FILE = ROOT / "requirements" / "requirements.json"


errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def must_exist(rel_path: str) -> Path:
    path = ROOT / rel_path
    if not path.exists():
        fail(f"missing required path: {rel_path}")
    return path


def read(rel_path: str) -> str:
    path = must_exist(rel_path)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def resolve_evidence(path_text: str) -> Path | None:
    candidates = [ROOT / path_text, PACK / path_text]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def check_source_manifest() -> None:
    manifest_file = must_exist("validation/source_truth_manifest.json")
    if not manifest_file.exists():
        return
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    if not entries:
        fail("source truth manifest has no entries")
        return
    by_path = {entry["path"]: entry for entry in entries}
    current_pack_files = [
        path.relative_to(PACK).as_posix()
        for path in PACK.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    ]
    missing = sorted(set(current_pack_files) - set(by_path))
    extra = sorted(set(by_path) - set(current_pack_files))
    if missing:
        fail(f"source truth manifest missing pack files: {missing}")
    if extra:
        fail(f"source truth manifest has stale pack files: {extra}")
    for entry in entries:
        if not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")):
            fail(f"invalid sha256 for source pack file: {entry.get('path')}")
        evidence = entry.get("product_evidence") or []
        if not evidence:
            fail(f"source pack file has no product evidence: {entry.get('path')}")
        for evidence_path in evidence:
            if resolve_evidence(evidence_path) is None:
                fail(f"source manifest evidence path missing for {entry.get('path')}: {evidence_path}")


def check_requirement_results() -> None:
    req = json.loads(REQ_FILE.read_text(encoding="utf-8"))["requirements"]
    results_file = must_exist("validation/requirement_results.json")
    if not results_file.exists():
        return
    payload = json.loads(results_file.read_text(encoding="utf-8"))
    results = payload.get("results", payload) if isinstance(payload, dict) else payload
    req_ids = [item["id"] for item in req]
    result_ids = [item.get("requirement_id") for item in results]
    if len(result_ids) != len(set(result_ids)):
        fail("duplicate requirement IDs in results")
    missing = sorted(set(req_ids) - set(result_ids))
    extra = sorted(set(result_ids) - set(req_ids))
    if missing:
        fail(f"requirement results missing IDs: {missing}")
    if extra:
        fail(f"requirement results contain extra IDs: {extra}")
    for result in results:
        rid = result.get("requirement_id")
        if result.get("status") != "pass":
            fail(f"requirement {rid} status is not pass: {result.get('status')}")
        if not result.get("notes"):
            fail(f"requirement {rid} has empty notes")
        evidence = result.get("evidence") or []
        tests = result.get("tests") or []
        if not evidence:
            fail(f"requirement {rid} has no evidence")
        if not tests:
            fail(f"requirement {rid} has no tests")
        for evidence_path in evidence:
            if resolve_evidence(evidence_path) is None:
                fail(f"requirement {rid} evidence path missing: {evidence_path}")


def check_project_shape() -> None:
    for rel_path in [
        "apps/web",
        "services/api",
        "packages/app-protocol",
        "packages/learning-apps",
        "docs",
        "scripts",
        "validation",
        ".env.example",
        ".gitignore",
        "docker-compose.yml",
        ".github/workflows/validation.yml",
    ]:
        must_exist(rel_path)


def check_backend_contract() -> None:
    main_text = read("services/api/app/main.py")
    required_routes = [
        "/health",
        "/api/system/status",
        "/api/chat/message",
        "/api/chat/stream",
        "/api/courses",
        "/api/courses/{course_id}/documents",
        "/api/courses/{course_id}/ingest",
        "/api/courses/{course_id}/knowledge-graph",
        "/api/profile/extract",
        "/api/profile/{student_id}",
        "/api/learning-path/generate",
        "/api/learning-path/{path_id}",
        "/api/resources/generate",
        "/api/resources/{resource_id}",
        "/api/quiz/{quiz_id}/submit",
        "/api/canvas/apps",
        "/api/canvas/apps/{app_id}",
        "/api/canvas/apps/{app_id}/events",
        "/api/canvas/applink/{link_id}/open",
        "/api/dashboard/{student_id}",
        "/api/dashboard/{student_id}/memory-evidence",
        "/api/agent-runs/{run_id}",
        "/api/memory/{student_id}",
        "/api/memory/search",
        "/api/memory/extract-from-chat",
        "/api/memory/app-event",
        "/api/memory/quiz-result",
        "/api/memory/layout-event",
        "/api/images/generate",
        "/api/protocol/fixtures",
    ]
    for route in required_routes:
        if route not in main_text:
            fail(f"missing API route text: {route}")
    for rel_path in [
        "services/api/app/database/schema.py",
        "services/api/app/database/postgres_schema.sql",
        "services/api/app/database/store.py",
    ]:
        must_exist(rel_path)
    schema_text = read("services/api/app/database/schema.py") + read("services/api/app/database/postgres_schema.sql")
    for table in [
        "students",
        "student_profiles",
        "edu_memories",
        "learning_events",
        "mastery_records",
        "courses",
        "course_documents",
        "document_chunks",
        "knowledge_points",
        "knowledge_edges",
        "learning_paths",
        "learning_path_nodes",
        "resources",
        "resource_versions",
        "canvas_apps",
        "chat_app_links",
        "app_events",
        "quiz_questions",
        "quiz_submissions",
        "agent_runs",
        "agent_steps",
        "verifier_results",
        "image_assets",
        "feedbacks",
    ]:
        if table not in schema_text:
            fail(f"database schema missing table: {table}")


def check_agents_skills_memory() -> None:
    agents = [
        "orchestrator_agent",
        "profile_agent",
        "knowledge_agent",
        "planner_agent",
        "recommender_agent",
        "tutor_agent",
        "app_canvas_agent",
        "evaluator_agent",
        "verifier_agent",
        "memory_agent",
        "resource_bundle_agent",
    ]
    for agent in agents:
        must_exist(f"services/api/app/agents/{agent}.py")
        must_exist(f"docs/agents/{agent}.md")

    skills = [
        "document_skill",
        "mindmap_skill",
        "quiz_skill",
        "ppt_skill",
        "code_practice_skill",
        "image_generation_skill",
        "video_script_skill",
        "reading_material_skill",
        "notes_skill",
        "dashboard_skill",
        "resource_bundle_skill",
        "app_generation_skill",
        "custom_html_app_skill",
        "verifier_skill",
        "memory_update_skill",
        "course_ingestion_skill",
    ]
    registry = read("services/api/app/skills/registry.py")
    for skill in skills:
        must_exist(f"services/api/app/skills/{skill}.py")
        if skill not in registry:
            fail(f"skill not registered: {skill}")
        hermes_name = skill.replace("_", "-")
        must_exist(f"services/api/hermes_profile/skills/{hermes_name}/SKILL.md")

    for rel_path in [
        "services/api/app/edumem0/schemas.py",
        "services/api/app/edumem0/confidence_policy.py",
        "services/api/app/edumem0/decay_policy.py",
        "services/api/app/edumem0/conflict_resolver.py",
        "services/api/app/edumem0/mem0_adapter.py",
        "services/api/app/edumem0/store.py",
    ]:
        must_exist(rel_path)


def check_external_truthfulness() -> None:
    for rel_path in [
        "services/api/app/model_gateway/mimo_client.py",
        "services/api/app/model_gateway/structured_output.py",
        "services/api/app/image_gateway/image2_client.py",
        "services/api/app/hermes_runtime/runtime.py",
        "services/api/app/hermes_runtime/cli_adapter.py",
        "services/api/app/hermes_runtime/python_agent_adapter.py",
        "scripts/check_hermes_sdk_embedding.py",
    ]:
        must_exist(rel_path)
    if "reasoning_content" not in read("services/api/app/model_gateway/mimo_client.py"):
        fail("MiMo client does not preserve reasoning_content")
    hermes_python_adapter = read("services/api/app/hermes_runtime/python_agent_adapter.py")
    for marker in ["run_agent", "AIAgent", "build_health_agent"]:
        if marker not in hermes_python_adapter:
            fail(f"Hermes Python adapter does not prove SDK embedding marker: {marker}")
    hermes_runtime = read("services/api/app/hermes_runtime/runtime.py")
    if "sdk_embedded" not in hermes_runtime or "python_aiagent_sdk" not in hermes_python_adapter:
        fail("Hermes runtime does not prefer embedded SDK mode")
    if "check_hermes_sdk_embedding.py" not in read("scripts/run_full_validation.sh"):
        fail("full validation does not write Hermes SDK embedding proof")
    env_example = read(".env.example")
    if "HERMES_REQUIRE_SDK=true" not in env_example:
        fail(".env.example does not require Hermes SDK embedding by default")
    blocked = read("BLOCKED_REAL_INTEGRATION_REPORT.md")
    if "Status: not complete for external readiness." not in blocked:
        fail("blocked report does not state external readiness is not complete")
    for marker in ["MIMO_API_KEY", "IMAGE2_API_KEY", "IMAGE2_BASE_URL", "HERMES_REQUIRE_SDK", "check_hermes_sdk_embedding.py"]:
        if marker not in blocked:
            fail(f"blocked report missing marker: {marker}")
    readiness_file = must_exist("validation/external_readiness.json")
    if readiness_file.exists():
        readiness = json.loads(readiness_file.read_text(encoding="utf-8"))
        if readiness.get("overall") == "ready" and "Status: not complete for external readiness." in blocked:
            fail("blocked report is stale: external readiness JSON is ready")
        for key in ["mimo", "image2", "hermes"]:
            component_status = readiness.get(key, {}).get("status")
            if component_status != "ready" and not str(component_status).startswith("blocked"):
                fail(f"external readiness status for {key} is not ready/blocked: {component_status}")


def check_frontend_contract() -> None:
    for rel_path in [
        "apps/web/src/app/LearnForgeApp.tsx",
        "apps/web/src/features/app-canvas/SpatialCanvas.tsx",
        "apps/web/src/features/applink-flight/AppLinkFlightLayer.tsx",
        "apps/web/src/features/tutor-chat/TutorChat.tsx",
        "apps/web/src/features/learning-apps/NativeAppRenderer.tsx",
        "apps/web/src/features/custom-html-app/CustomHtmlAppRenderer.tsx",
        "apps/web/e2e/product-flow.spec.ts",
    ]:
        must_exist(rel_path)
    native_text = read("apps/web/src/features/learning-apps/NativeAppRenderer.tsx")
    app_types = [
        "profile.dashboard",
        "learning.path",
        "knowledge.graph",
        "mindmap.concept",
        "quiz.practice",
        "physics.work_energy_demo",
        "math.gradient_descent_demo",
        "code.lab",
        "notes.session",
        "dashboard.learning",
        "ppt.preview",
        "image.explanation",
        "video.script",
        "resource.center",
        "custom.html",
    ]
    for app_type in app_types:
        if app_type not in native_text:
            fail(f"native app renderer missing app type: {app_type}")
    e2e_text = read("apps/web/e2e/product-flow.spec.ts")
    for marker in ["AppLink Flight", "WorkEnergy", "Quiz submit", "LearningPath", "Notes App", "enabled controls"]:
        if marker not in e2e_text:
            fail(f"E2E product flow missing marker: {marker}")


def check_docs_reports_validation() -> None:
    docs = [
        "docs/architecture.md",
        "docs/agent_design.md",
        "docs/memory_design.md",
        "docs/app_canvas_design.md",
        "docs/rag_safety_design.md",
        "docs/competition_traceability.md",
        "docs/open_source_licenses.md",
        "docs/provider_declaration.md",
        "docs/demo_script.md",
        "docs/runbook.md",
        "docs/test_report.md",
        "docs/source_truth_manifest.md",
        "RUN_REPORT.md",
        "BLOCKED_REAL_INTEGRATION_REPORT.md",
    ]
    for rel_path in docs:
        must_exist(rel_path)
    workflow = read(".github/workflows/validation.yml")
    if "run_full_validation.sh" not in workflow:
        fail("CI workflow does not run full validation")
    validation_script = read("scripts/run_full_validation.sh")
    for marker in [
        "verify_project_structure.py",
        "pytest services/api/tests",
        "npm run web:build",
        "npm run web:e2e",
        "verify_no_mock_runtime.sh",
        "secret_scan.sh",
        "verify_requirement_results.py",
        "verify_full_contract.py",
    ]:
        if marker not in validation_script:
            fail(f"full validation missing command marker: {marker}")


def main() -> None:
    check_source_manifest()
    check_requirement_results()
    check_project_shape()
    check_backend_contract()
    check_agents_skills_memory()
    check_external_truthfulness()
    check_frontend_contract()
    check_docs_reports_validation()
    if errors:
        print("Full contract verification failed:")
        for message in errors:
            print(f"- {message}")
        sys.exit(1)
    print("Full product contract verified")


if __name__ == "__main__":
    main()
