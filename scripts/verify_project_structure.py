#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
required = [
    "apps/web",
    "services/api",
    "packages/app-protocol",
    "packages/learning-apps",
    "docs",
    "scripts",
    "validation",
]
missing = [path for path in required if not (ROOT / path).exists()]
if missing:
    raise SystemExit(f"missing project paths: {missing}")
print("Project structure verified")
