#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path.cwd()
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

sys.path.insert(0, str(ROOT / "services" / "api"))

from app.hermes_runtime.runtime import HermesRuntime  # noqa: E402


OUT_JSON = ROOT / "validation" / "hermes_sdk_status.json"


def validate(status: dict[str, object], require_ready: bool) -> list[str]:
    errors: list[str] = []
    current = str(status.get("status", "unknown"))
    if current == "ready":
        if status.get("adapter") != "python_aiagent_sdk":
            errors.append(f"Hermes ready status is not using the Python SDK adapter: {status.get('adapter')}")
        if status.get("integration_mode") != "sdk_embedded":
            errors.append(f"Hermes ready status is not sdk_embedded: {status.get('integration_mode')}")
        if status.get("embedded_agent_class") != "run_agent.AIAgent":
            errors.append(f"Hermes embedded agent class is not run_agent.AIAgent: {status.get('embedded_agent_class')}")
    elif not current.startswith("blocked"):
        errors.append(f"Hermes returned non-ready/non-blocked status: {current}")
    if require_ready and current != "ready":
        errors.append(f"Hermes SDK embedding is not ready: {current}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Write LearnForge Hermes SDK embedding proof.")
    parser.add_argument("--require-ready", action="store_true", help="Fail if embedded Hermes SDK is blocked.")
    args = parser.parse_args()

    status = HermesRuntime().status().model_dump()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "status": status.get("status"),
        "adapter": status.get("adapter"),
        "integration_mode": status.get("integration_mode"),
        "sdk_module": status.get("sdk_module"),
        "sdk_version": status.get("sdk_version"),
        "embedded_agent_class": status.get("embedded_agent_class"),
        "sdk_path": status.get("sdk_path"),
    }
    print("Hermes SDK embedding proof written")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    errors = validate(status, args.require_ready)
    if errors:
        print("Hermes SDK embedding check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
