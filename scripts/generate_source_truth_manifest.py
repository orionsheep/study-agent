#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path.cwd()
PACK = ROOT.parent / "learnforge_v4_all_requirements_test_gated_goal_pack"
OUT_JSON = ROOT / "validation" / "source_truth_manifest.json"
OUT_MD = ROOT / "docs" / "source_truth_manifest.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_for(rel_path: str) -> list[str]:
    if rel_path == "requirements/requirements.json":
        return ["requirements/requirements.json", "validation/requirement_results.json", "scripts/verify_requirement_results.py"]
    if rel_path.startswith("templates/"):
        return [".env.example", ".gitignore", "packages/app-protocol/src/types.ts", "services/api/app/edumem0/schemas.py"]
    if rel_path.startswith("scripts/"):
        return ["scripts/run_full_validation.sh", "scripts/verify_full_contract.py", "scripts/verify_no_mock_runtime.sh"]
    if rel_path.startswith("sources/"):
        return ["docs/open_source_licenses.md", "docs/provider_declaration.md", "docs/competition_traceability.md"]
    if rel_path.startswith("prompts/") or rel_path == "FULL_GOAL_COMMAND.md":
        return ["RUN_REPORT.md", "BLOCKED_REAL_INTEGRATION_REPORT.md", "docs/runbook.md"]
    if rel_path.startswith(".omx/"):
        return ["RUN_REPORT.md"]

    root_map = {
        "AGENT_TOPOLOGY_REQUIRED.md": ["services/api/app/agents", "docs/agent_design.md", "docs/agents"],
        "APP_CANVAS_REQUIRED.md": ["apps/web/src/features/app-canvas", "docs/app_canvas_design.md"],
        "APP_PROTOCOL_REQUIRED.md": ["packages/app-protocol/src/types.ts", "services/api/app/schemas/app_protocol.py"],
        "AUDIT_V3_GAPS.md": ["validation/requirement_results.json", "BLOCKED_REAL_INTEGRATION_REPORT.md"],
        "BACKEND_RUNTIME_REQUIRED.md": ["services/api/app/main.py", "services/api/tests/test_health_routes.py"],
        "COMPETITION_TRACEABILITY_REQUIRED.md": ["docs/competition_traceability.md", "docs/demo_script.md"],
        "CUSTOM_GENERATIVE_UI_REQUIRED.md": ["apps/web/src/features/custom-html-app", "services/api/app/skills/custom_html_app_skill.py"],
        "DASHBOARD_LEARNING_LOOP_REQUIRED.md": ["apps/web/src/features/learning-apps/NativeAppRenderer.tsx", "services/api/app/skills/dashboard_skill.py"],
        "DATABASE_SCHEMA_DRAFT.sql": ["services/api/app/database/postgres_schema.sql", "services/api/app/database/schema.py"],
        "DELIVERABLES_REQUIRED.md": ["RUN_REPORT.md", "docs/test_report.md", "validation/requirement_results.json"],
        "FRONTEND_PRODUCT_REQUIRED.md": ["apps/web/src/app/LearnForgeApp.tsx", "apps/web/src/app/styles.css"],
        "HERMES_MIMO_IMAGE2_REQUIRED.md": [
            "services/api/app/hermes_runtime",
            "services/api/app/model_gateway/gemini_client.py",
            "services/api/app/image_gateway/gemini_image_client.py",
        ],
        "IMPLEMENT_FULL_PRODUCT.md": ["RUN_REPORT.md", "scripts/run_full_validation.sh"],
        "MEMORY_SYSTEM_REQUIRED.md": ["services/api/app/edumem0", "docs/memory_design.md"],
        "NATIVE_LEARNING_APPS_REQUIRED.md": ["apps/web/src/features/learning-apps/NativeAppRenderer.tsx", "packages/learning-apps/src/index.ts"],
        "NO_MOCK_POLICY.md": ["scripts/verify_no_mock_runtime.sh", "BLOCKED_REAL_INTEGRATION_REPORT.md"],
        "OPEN_SOURCE_RESEARCH_AND_CHOICES.md": ["docs/open_source_licenses.md", "docs/provider_declaration.md"],
        "RAG_SAFETY_VERIFIER_REQUIRED.md": ["services/api/app/rag", "services/api/app/safety", "docs/rag_safety_design.md"],
        "README.md": ["RUN_REPORT.md", "docs/architecture.md"],
        "RESOURCE_SKILLS_REQUIRED.md": ["services/api/app/skills", "services/api/hermes_profile/skills"],
        "SECRETS_POLICY.md": ["scripts/secret_scan.sh", ".gitignore", ".env.example"],
        "TARGET_PROJECT_STRUCTURE.md": ["scripts/verify_project_structure.py", "docs/architecture.md"],
        "TEST_STANDARDS_REQUIRED.md": ["scripts/run_full_validation.sh", "docs/test_report.md"],
        "USER_REQUIREMENT_TRACE.md": ["validation/requirement_results.json", "docs/competition_traceability.md"],
    }
    return root_map.get(rel_path, ["RUN_REPORT.md"])


def role_for(rel_path: str) -> str:
    if rel_path.startswith(".omx/"):
        return "pack operational metadata"
    if rel_path.startswith("requirements/"):
        return "machine-readable acceptance contract"
    if rel_path.startswith("templates/"):
        return "implementation template"
    if rel_path.startswith("scripts/"):
        return "validation template"
    if rel_path.startswith("sources/"):
        return "research/source inventory"
    if rel_path.startswith("prompts/"):
        return "goal prompt"
    if rel_path.endswith(".md"):
        return "requirements source document"
    if rel_path.endswith(".sql"):
        return "database schema source"
    return "source pack file"


def main() -> None:
    if not PACK.exists():
        raise SystemExit(f"source pack not found: {PACK}")

    entries = []
    for path in sorted(PACK.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        rel = path.relative_to(PACK).as_posix()
        entries.append(
            {
                "path": rel,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
                "role": role_for(rel),
                "product_evidence": evidence_for(rel),
            }
        )

    payload = {
        "pack_root": str(PACK),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "excluded": [".DS_Store"],
        "entries": entries,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        "# Source Truth Manifest",
        "",
        f"Pack root: `{PACK}`",
        "",
        "Every non-OS file in the requirement pack is inventoried here with a hash and product evidence path. `.DS_Store` is excluded as OS metadata.",
        "",
        "| Pack file | SHA-256 | Role | Product evidence |",
        "| --- | --- | --- | --- |",
    ]
    for entry in entries:
        evidence = ", ".join(f"`{item}`" for item in entry["product_evidence"])
        rows.append(f"| `{entry['path']}` | `{entry['sha256'][:16]}` | {entry['role']} | {evidence} |")
    OUT_MD.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} source-truth manifest entries")


if __name__ == "__main__":
    main()
