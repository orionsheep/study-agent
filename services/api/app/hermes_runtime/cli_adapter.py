from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from app.core.config import get_settings
from app.hermes_runtime.command import resolve_hermes_command


@dataclass(frozen=True)
class HermesCliProbe:
    status: str
    reason: str
    command_path: str | None
    probe_command: list[str] | None


class HermesCliAdapter:
    name = "cli"

    def command_path(self) -> str | None:
        configured = get_settings().hermes_command.strip()
        path_candidate = shutil.which(Path(configured).name if configured else "hermes")
        if path_candidate:
            return path_candidate
        resolved = resolve_hermes_command(configured)
        if resolved:
            return resolved
        return None

    def available(self) -> bool:
        return self.command_path() is not None

    def version_probe(self) -> HermesCliProbe:
        path = self.command_path()
        if not path:
            return HermesCliProbe(
                status="blocked_missing_runtime",
                reason="hermes command is not installed.",
                command_path=None,
                probe_command=None,
            )
        errors: list[str] = []
        for command in ([path, "version"], [path, "--version"]):
            try:
                result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=8, env=self._env())
            except subprocess.TimeoutExpired:
                errors.append(f"{' '.join(command)} timed out.")
                continue
            except OSError as exc:
                errors.append(f"{' '.join(command)} failed: {exc}")
                continue
            detail = (result.stdout or result.stderr or "").strip()
            if result.returncode == 0 and detail:
                return HermesCliProbe(
                    status="ready",
                    reason=detail,
                    command_path=path,
                    probe_command=command,
                )
            errors.append(f"{' '.join(command)} exited {result.returncode}: {detail or 'no output'}")
        status = "blocked_runtime_unresponsive" if errors and all("timed out" in error for error in errors) else "blocked_runtime_error"
        return HermesCliProbe(
            status=status,
            reason="; ".join(errors) or "hermes command did not provide a usable version proof.",
            command_path=path,
            probe_command=[path, "version"],
        )

    def diagnostic(self, args: list[str], timeout: int = 10) -> HermesCliProbe:
        path = self.command_path()
        if not path:
            return HermesCliProbe(
                status="blocked_missing_runtime",
                reason="hermes command is not installed.",
                command_path=None,
                probe_command=None,
            )
        command = [path, *args]
        try:
            result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout, env=self._env())
        except subprocess.TimeoutExpired:
            return HermesCliProbe(
                status="blocked_runtime_unresponsive",
                reason=f"{' '.join(command)} timed out.",
                command_path=path,
                probe_command=command,
            )
        except OSError as exc:
            return HermesCliProbe(
                status="blocked_runtime_error",
                reason=f"{' '.join(command)} failed: {exc}",
                command_path=path,
                probe_command=command,
            )
        detail = (result.stdout or result.stderr or "").strip()
        status = "ready" if result.returncode == 0 else "blocked_runtime_error"
        return HermesCliProbe(
            status=status,
            reason=detail[:1200] or f"exited {result.returncode}",
            command_path=path,
            probe_command=command,
        )

    def _env(self) -> dict[str, str]:
        import os

        settings = get_settings()
        env = os.environ.copy()
        env["HERMES_HOME"] = str(settings.project_root / settings.hermes_home)
        env["HERMES_ACCEPT_HOOKS"] = "1"
        if settings.gemini_api_key:
            env["GEMINI_API_KEY"] = settings.gemini_api_key
        return env
