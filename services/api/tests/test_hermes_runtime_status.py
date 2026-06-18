from pathlib import Path
from types import SimpleNamespace

from app.hermes_runtime.cli_adapter import HermesCliAdapter
from app.hermes_runtime.python_agent_adapter import HermesPythonAgentAdapter
from app.hermes_runtime.runtime import HermesRuntime


def test_hermes_runtime_status_and_config():
    runtime = HermesRuntime()
    status = runtime.status()
    assert status.status == "ready" or status.status.startswith("blocked")
    assert status.skills_synced is True
    assert status.home
    if status.status == "ready":
        assert status.integration_mode in {"sdk_embedded", "cli_fallback"}
        if status.integration_mode == "sdk_embedded":
            assert status.adapter == "python_aiagent_sdk"
            assert status.embedded_agent_class == "run_agent.AIAgent"


def test_hermes_python_adapter_embeds_aiagent_sdk(monkeypatch):
    captured = {}

    class FakeAgent:
        __module__ = "run_agent"

        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.provider = kwargs["provider"]
            self.api_mode = "chat_completions"
            self.model = kwargs["model"]

    settings = SimpleNamespace(
        project_root=Path("/tmp/learnforge"),
        hermes_home=".runtime/hermes",
        hermes_provider="gemini",
        gemini_api_key="local-key",
        gemini_text_model="gemini-3.1-pro-preview",
        hermes_sdk_path="",
        hermes_sdk_site_packages="",
    )
    adapter = HermesPythonAgentAdapter()
    adapter.settings = settings
    monkeypatch.setattr(adapter, "_load_sdk", lambda: (FakeAgent, "0.test", "/tmp/run_agent.py"))

    probe = adapter.probe()

    assert probe.status == "ready"
    assert probe.sdk_module == "run_agent"
    assert probe.sdk_version == "0.test"
    assert probe.embedded_agent_class == "run_agent.FakeAgent"
    assert captured["base_url"] == "https://generativelanguage.googleapis.com/v1beta"
    assert captured["provider"] == "gemini"
    assert captured["model"] == "gemini-3.1-pro-preview"
    assert captured["enabled_toolsets"] == []
    # 记忆系统已启用:EduMem0Provider 通过 skip_memory=False + memory.provider=edumem0 接入。
    assert captured["skip_memory"] is False
    assert captured["skip_context_files"] is True


def test_hermes_python_adapter_blocks_without_gemini_key():
    settings = SimpleNamespace(
        project_root=Path("/tmp/learnforge"),
        hermes_home=".runtime/hermes",
        hermes_provider="gemini",
        gemini_api_key="",
        gemini_text_model="gemini-3.1-pro-preview",
        hermes_sdk_path="",
        hermes_sdk_site_packages="",
    )
    adapter = HermesPythonAgentAdapter()
    adapter.settings = settings

    probe = adapter.probe()

    assert probe.status == "blocked_missing_credentials"
    assert "GEMINI_API_KEY" in probe.reason


def test_hermes_cli_probe_prefers_version_command(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = "Hermes Agent v0.14.0"
        stderr = ""

    def fake_run(command, **_kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr("app.hermes_runtime.cli_adapter.shutil.which", lambda _name: "/tmp/hermes")
    monkeypatch.setattr("app.hermes_runtime.cli_adapter.subprocess.run", fake_run)

    probe = HermesCliAdapter().version_probe()

    assert probe.status == "ready"
    assert probe.probe_command == ["/tmp/hermes", "version"]
    assert calls == [["/tmp/hermes", "version"]]
