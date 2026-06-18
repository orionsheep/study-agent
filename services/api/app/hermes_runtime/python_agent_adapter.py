from __future__ import annotations

import contextlib
import importlib
import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings, missing_secret


@dataclass(frozen=True)
class HermesSdkProbe:
    status: str
    reason: str
    sdk_module: str | None = None
    sdk_version: str | None = None
    sdk_path: str | None = None
    embedded_agent_class: str | None = None


class HermesPythonAgentAdapter:
    name = "python_aiagent_sdk"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _configured_paths(self) -> list[Path]:
        paths: list[Path] = []
        for raw in [self.settings.hermes_sdk_path, self.settings.hermes_sdk_site_packages]:
            if not raw:
                continue
            for part in raw.split(os.pathsep):
                candidate = Path(part).expanduser()
                if candidate.exists():
                    paths.append(candidate)
        return paths

    def _install_configured_paths(self) -> None:
        for path in reversed(self._configured_paths()):
            value = str(path)
            if value not in sys.path:
                sys.path.insert(0, value)

    def _load_sdk(self) -> tuple[type[Any], str, str | None]:
        self._install_configured_paths()
        module = importlib.import_module("run_agent")
        agent_class = getattr(module, "AIAgent")
        try:
            version_module = importlib.import_module("hermes_cli")
            version = str(getattr(version_module, "__version__", "unknown"))
        except Exception:
            version = "unknown"
        sdk_path = str(Path(getattr(module, "__file__", "")).resolve()) if getattr(module, "__file__", None) else None
        return agent_class, version, sdk_path

    def _ensure_environment(self) -> None:
        home = self.settings.project_root / self.settings.hermes_home
        os.environ["HERMES_HOME"] = str(home)
        os.environ["HERMES_PROVIDER"] = "gemini"
        os.environ["HERMES_INFERENCE_PROVIDER"] = "gemini"
        os.environ["HERMES_INFERENCE_MODEL"] = self.settings.gemini_text_model
        if not missing_secret(self.settings.gemini_api_key):
            os.environ.setdefault("GEMINI_API_KEY", self.settings.gemini_api_key)
        os.environ.setdefault("GEMINI_TEXT_MODEL", self.settings.gemini_text_model)

    def build_health_agent(
        self,
        *,
        session_id: str = "learnforge-hermes-sdk-health",
        max_iterations: int = 4,
        quiet_mode: bool = True,
        provider_override: str | None = None,
        model_override: str | None = None,
        user_id: str | None = None,
        hermes_callbacks: dict[str, Any] | None = None,
    ) -> Any:
        if missing_secret(self.settings.gemini_api_key):
            raise RuntimeError("GEMINI_API_KEY is required before embedding Hermes AIAgent with the Gemini provider.")
        provider = provider_override or getattr(self.settings, "hermes_provider", "gemini")
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        api_key = self.settings.gemini_api_key
        model = model_override or self.settings.gemini_text_model
        self._ensure_environment()
        agent_class, _version, _sdk_path = self._load_sdk()
        toolsets = getattr(self.settings, "hermes_toolsets", "")
        stdout = io.StringIO()
        stderr = io.StringIO()
        cb = hermes_callbacks or {}
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            return agent_class(
                base_url=base_url,
                api_key=api_key,
                provider=provider,
                model=model,
                enabled_toolsets=[item.strip() for item in toolsets.split(",") if item.strip()],
                quiet_mode=quiet_mode,
                skip_memory=False,
                skip_context_files=True,
                max_iterations=max_iterations,
                session_id=session_id,
                user_id=user_id,
                thinking_callback=cb.get("thinking_callback"),
                reasoning_callback=cb.get("reasoning_callback"),
                step_callback=cb.get("step_callback"),
                status_callback=cb.get("status_callback"),
            )

    def available(self) -> bool:
        return self.probe().status == "ready"

    def probe(self) -> HermesSdkProbe:
        try:
            agent = self.build_health_agent()
            _agent_class, version, sdk_path = self._load_sdk()
            provider = str(getattr(agent, "provider", "gemini") or "gemini")
            api_mode = str(getattr(agent, "api_mode", "unknown") or "unknown")
            default_model = getattr(self.settings, "gemini_text_model", "unknown")
            model = str(getattr(agent, "model", default_model) or default_model)
            return HermesSdkProbe(
                status="ready",
                reason=f"Hermes SDK embedded via run_agent.AIAgent; provider={provider}; api_mode={api_mode}; model={model}.",
                sdk_module="run_agent",
                sdk_version=version,
                sdk_path=sdk_path,
                embedded_agent_class=f"{agent.__class__.__module__}.{agent.__class__.__name__}",
            )
        except ModuleNotFoundError as exc:
            return HermesSdkProbe(
                status="blocked_missing_runtime",
                reason=f"Hermes SDK module is not importable in the API process: {exc.name}. Install hermes-agent in this venv or set HERMES_SDK_PATH.",
                sdk_module="run_agent",
            )
        except RuntimeError as exc:
            status = "blocked_missing_credentials" if "GEMINI_API_KEY" in str(exc) else "blocked_runtime_error"
            return HermesSdkProbe(status=status, reason=str(exc), sdk_module="run_agent")
        except Exception as exc:
            return HermesSdkProbe(
                status="blocked_runtime_error",
                reason=f"Hermes SDK embedding failed during AIAgent construction: {type(exc).__name__}: {exc}",
                sdk_module="run_agent",
            )
