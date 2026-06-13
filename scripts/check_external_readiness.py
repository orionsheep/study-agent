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


def blocker_line(name: str, component: dict[str, object]) -> str:
    status = str(component.get("status", "unknown"))
    reason = " ".join(str(component.get("reason") or "No reason reported.").split())
    if status == "ready":
        return f"- {name}: `ready` - {reason}"
    return f"- {name}: `{status}` - {reason}"


def next_commands(status: dict[str, object]) -> str:
    lines = ["test -f .env || cp .env.example .env"]
    if status["mimo"]["status"] == "ready":
        lines.append("# MiMo is currently ready; keep MIMO_API_KEY and MIMO_BASE_URL in local .env for future checks.")
    else:
        lines.append("# Add a real MIMO_API_KEY and MIMO_BASE_URL to local .env.")
    if status["image2"]["status"] != "ready":
        lines.append("# Add IMAGE2_API_KEY and IMAGE2_BASE_URL when image2 should be enabled.")
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


def write_blocked_report(status: dict[str, object]) -> None:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    mimo = status["mimo"]
    image2 = status["image2"]
    hermes = status["hermes"]
    content = f"""# Blocked Real Integration Report

Status: not complete for external readiness.

Generated: `{generated_at}`

The product implements real integration paths, but this machine does not currently prove all external providers ready.

Current `/api/system/status` proof:

- `overall`: `{status["overall"]}`
- `database`: `{status["database"]["status"]}`
- `edumem0`: `{status["edumem0"]["status"]}`
- `rag`: `{status["rag"]["status"]}`

External blockers:

{blocker_line("MiMo", mimo)}
{blocker_line("image2", image2)}
{blocker_line("Hermes", hermes)}

Next commands:

```bash
{next_commands(status)}
```

Do not mark the goal complete until `/api/system/status` reports MiMo, image2, and Hermes ready or the user provides a runtime environment where those checks can succeed.
"""
    BLOCKED_REPORT.write_text(content, encoding="utf-8")


def validate_status(status: dict[str, object], require_external_ready: bool) -> list[str]:
    errors: list[str] = []
    if status.get("database", {}).get("status") != "ready":
        errors.append("database is not ready")
    for name in ["mimo", "image2", "hermes"]:
        component = status.get(name, {})
        component_status = str(component.get("status", "unknown"))
        if component_status != "ready" and not component_status.startswith("blocked"):
            errors.append(f"{name} returned non-ready/non-blocked status: {component_status}")
        if require_external_ready and component_status != "ready":
            errors.append(f"{name} is not externally ready: {component_status}")
    if require_external_ready and status.get("overall") != "ready":
        errors.append(f"overall status is not ready: {status.get('overall')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Write LearnForge external readiness proof.")
    parser.add_argument("--require-external-ready", action="store_true", help="Fail if MiMo, image2, or Hermes are blocked.")
    args = parser.parse_args()

    status = asyncio.run(system_status())
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    if status.get("overall") != "ready":
        write_blocked_report(status)

    errors = validate_status(status, args.require_external_ready)
    if errors:
        print("External readiness check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    summary = {
        "overall": status["overall"],
        "mimo": status["mimo"]["status"],
        "image2": status["image2"]["status"],
        "hermes": status["hermes"]["status"],
        "hermes_adapter": status["hermes"].get("adapter"),
        "hermes_integration_mode": status["hermes"].get("integration_mode"),
    }
    print("External readiness proof written")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
