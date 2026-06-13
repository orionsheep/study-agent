from __future__ import annotations

import re
import shutil
from pathlib import Path


def resolve_hermes_command(configured: str) -> str | None:
    command = configured.strip()
    if not command:
        command = "hermes"
    resolved = command if "/" in command else shutil.which(command)
    if not resolved:
        return None
    path = Path(resolved)
    if not path.exists():
        return resolved if "/" not in command else None
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return str(path)
        match = re.search(r'exec\s+"([^"]*/venv/bin/hermes)"', text)
        if match:
            unwrapped = Path(match.group(1))
            if unwrapped.exists():
                return str(unwrapped)
    return str(path)
