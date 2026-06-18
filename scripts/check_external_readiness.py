#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path.cwd()
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

sys.path.insert(0, str(ROOT / "services" / "api"))

from app.main import system_status  # noqa: E402


OUT_JSON = ROOT / "validation" / "external_readiness.json"
BLOCKED_REPORT = ROOT / "BLOCKED_REAL_INTEGRATION_REPORT.md"
REQUIRED_COMPONENTS = ["gemini", "gemini_image", "hermes", "object_storage"]
OPTIONAL_COMPONENTS = ["image2"]


def blocker_line(name: str, component: dict[str, object]) -> str:
    status = str(component.get("status", "unknown"))
    reason = " ".join(str(component.get("reason") or "No reason reported.").split())
    if status == "ready":
        return f"- {name}: `ready` - {reason}"
    return f"- {name}: `{status}` - {reason}"


def next_commands(status: dict[str, object]) -> str:
    lines = ["test -f .env || cp .env.example .env"]
    if status["gemini"]["status"] == "ready":
        lines.append("# Gemini text is currently ready; keep GEMINI_API_KEY and GEMINI_TEXT_MODEL in local .env.")
    else:
        lines.append("# Add a real GEMINI_API_KEY and GEMINI_TEXT_MODEL to local .env.")
    if status["gemini_image"]["status"] == "ready":
        lines.append("# Gemini image is currently ready; keep GEMINI_IMAGE_MODEL in local .env.")
    else:
        lines.append("# Configure GEMINI_IMAGE_MODEL/GEMINI_IMAGE_FALLBACK_MODEL for image generation.")
    hermes_mode = status["hermes"].get("integration_mode")
    if status["hermes"]["status"] == "ready" and hermes_mode == "sdk_embedded":
        lines.append("# Hermes SDK is currently ready; keep hermes-agent installed in the API venv or set HERMES_SDK_PATH.")
    elif status["hermes"]["status"] == "ready":
        lines.append("# Hermes is currently ready through a fallback path; install hermes-agent in the API venv for SDK embedding.")
    else:
        lines.append("# Install hermes-agent in the API venv, or set HERMES_SDK_PATH to a real Hermes checkout.")
    lines.extend(
        [
            "docker compose up -d postgres redis",
            ". .venv/bin/activate",
            "export HERMES_REQUIRE_SDK=true",
            "DATABASE_URL=postgresql+asyncpg://learnforge:learnforge@localhost:5432/learnforge uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000",
            "curl http://127.0.0.1:8000/api/system/status",
            "python scripts/check_hermes_sdk_embedding.py",
            "hermes version  # optional CLI diagnostic; SDK embedding is the product integration path",
        ]
    )
    return "\n".join(lines)


def write_ready_report(status: dict[str, object]) -> None:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    content = f"""# Real Integration Report

Status: external readiness complete.

Generated: `{generated_at}`

The product currently proves the required Gemini-first external integrations ready.

Current `/api/system/status` proof:

- `overall`: `{status["overall"]}`
- `database`: `{status["database"]["status"]}`
- `edumem0`: `{status["edumem0"]["status"]}`
- `rag`: `{status["rag"]["status"]}`

Required external components:

{blocker_line("Gemini text", status["gemini"])}
{blocker_line("Gemini image", status["gemini_image"])}
{blocker_line("Hermes", status["hermes"])}
{blocker_line("Object storage", status["object_storage"])}

Optional compatibility components:

{blocker_line("image2", status.get("image2", {"status": "blocked_not_configured", "reason": "Optional image2 provider is not part of Gemini-first readiness."}))}
"""
    BLOCKED_REPORT.write_text(content, encoding="utf-8")


def write_blocked_report(status: dict[str, object]) -> None:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    gemini = status["gemini"]
    gemini_image = status["gemini_image"]
    hermes = status["hermes"]
    object_storage = status["object_storage"]
    content = f"""# Blocked Real Integration Report

Status: not complete for external readiness.

Generated: `{generated_at}`

The product implements real Gemini-first integration paths, but this machine does not currently prove all required external components ready.

Current `/api/system/status` proof:

- `overall`: `{status["overall"]}`
- `database`: `{status["database"]["status"]}`
- `edumem0`: `{status["edumem0"]["status"]}`
- `rag`: `{status["rag"]["status"]}`

External blockers:

{blocker_line("Gemini text", gemini)}
{blocker_line("Gemini image", gemini_image)}
{blocker_line("Hermes", hermes)}
{blocker_line("Object storage", object_storage)}

Optional compatibility components:

{blocker_line("image2", status.get("image2", {"status": "blocked_not_configured", "reason": "Optional image2 provider is not part of Gemini-first readiness."}))}

Next commands:

```bash
{next_commands(status)}
```

Do not mark the goal complete until `/api/system/status` reports Gemini text, Gemini image, Hermes, and object storage ready or the user provides a runtime environment where those checks can succeed.
"""
    BLOCKED_REPORT.write_text(content, encoding="utf-8")


def validate_status(status: dict[str, object], require_external_ready: bool) -> list[str]:
    errors: list[str] = []
    if status.get("database", {}).get("status") != "ready":
        errors.append("database is not ready")
    for name in [*REQUIRED_COMPONENTS, *OPTIONAL_COMPONENTS]:
        component = status.get(name, {})
        component_status = str(component.get("status", "unknown"))
        if component_status != "ready" and not component_status.startswith("blocked"):
            errors.append(f"{name} returned non-ready/non-blocked status: {component_status}")
        if name in OPTIONAL_COMPONENTS:
            continue
        if require_external_ready and component_status != "ready":
            errors.append(f"{name} is not externally ready: {component_status}")
    if require_external_ready and status.get("overall") != "ready":
        errors.append(f"overall status is not ready: {status.get('overall')}")
    return errors


def normalize_external_blockers(status: dict[str, object]) -> dict[str, object]:
    normalized = dict(status)
    has_required_external_blocker = False
    for name in [*REQUIRED_COMPONENTS, *OPTIONAL_COMPONENTS]:
        component = normalized.get(name)
        if not isinstance(component, dict):
            normalized[name] = {"status": "blocked_unknown", "reason": "Component did not report readiness details."}
            if name in REQUIRED_COMPONENTS:
                has_required_external_blocker = True
            continue
        component_status = str(component.get("status", "unknown"))
        if component_status != "ready" and not component_status.startswith("blocked"):
            normalized[name] = {
                **component,
                "status": f"blocked_{component_status or 'unknown'}",
                "reason": component.get("reason") or f"Component returned non-ready status {component_status}.",
            }
            if name in REQUIRED_COMPONENTS:
                has_required_external_blocker = True
        elif component_status.startswith("blocked") and name in REQUIRED_COMPONENTS:
            has_required_external_blocker = True
    if has_required_external_blocker:
        normalized["overall"] = "blocked_external"
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Write LearnForge external readiness proof.")
    parser.add_argument("--require-external-ready", action="store_true", help="Fail if Gemini text, Gemini image, Hermes, or object storage are blocked.")
    args = parser.parse_args()

    status = normalize_external_blockers(asyncio.run(system_status()))
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    if status.get("overall") != "ready":
        write_blocked_report(status)
    else:
        write_ready_report(status)

    errors = validate_status(status, args.require_external_ready)
    if errors:
        print("External readiness check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    summary = {
        "overall": status["overall"],
        "gemini": status["gemini"]["status"],
        "gemini_image": status["gemini_image"]["status"],
        "hermes": status["hermes"]["status"],
        "object_storage": status["object_storage"]["status"],
        "image2_optional": status.get("image2", {}).get("status"),
        "hermes_adapter": status["hermes"].get("adapter"),
        "hermes_integration_mode": status["hermes"].get("integration_mode"),
    }
    print("External readiness proof written")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
