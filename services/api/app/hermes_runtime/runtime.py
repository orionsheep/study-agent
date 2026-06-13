from __future__ import annotations

import logging

from app.core.config import get_settings
from app.hermes_runtime.cli_adapter import HermesCliAdapter
from app.hermes_runtime.config_writer import HermesConfigWriter
from app.hermes_runtime.python_agent_adapter import HermesPythonAgentAdapter
from app.hermes_runtime.skill_sync import HermesSkillSync
from app.hermes_runtime.status import HermesStatus


logger = logging.getLogger(__name__)


class HermesRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.python_adapter = HermesPythonAgentAdapter()
        self.cli_adapter = HermesCliAdapter()
        self.skill_sync = HermesSkillSync()
        self.config_writer = HermesConfigWriter()

    def prepare(self) -> None:
        self.skill_sync.sync()
        self.config_writer.write()

    def status(self) -> HermesStatus:
        self.prepare()
        profile_path = self.config_writer.write()
        home = self.settings.project_root / self.settings.hermes_home
        native_config_path = home / "config.yaml"
        configured_skills = [item.strip() for item in self.settings.hermes_default_skills.split(",") if item.strip()]
        enabled_toolsets = [item.strip() for item in self.settings.hermes_toolsets.split(",") if item.strip()]
        skills_diag = self.cli_adapter.diagnostic(["skills", "list"])
        tools_diag = self.cli_adapter.diagnostic(["tools", "--summary", "list"])
        mcp_diag = self.cli_adapter.diagnostic(["mcp", "list"])
        profile_status = {
            "profile_path": str(profile_path),
            "native_config_path": str(native_config_path),
            "profile_synced": True,
            "configured_skills": configured_skills,
            "enabled_toolsets": enabled_toolsets,
            "skills_status": skills_diag.status,
            "skills_detail": skills_diag.reason,
            "tools_status": tools_diag.status,
            "tools_detail": tools_diag.reason,
            "mcp_status": mcp_diag.status,
            "mcp_detail": mcp_diag.reason,
        }
        sdk_probe = self.python_adapter.probe()
        if sdk_probe.status == "ready":
            logger.info("Hermes runtime adapter=%s mode=sdk_embedded", self.python_adapter.name)
            return HermesStatus(
                status="ready",
                reason=sdk_probe.reason,
                adapter=self.python_adapter.name,
                home=str(self.settings.project_root / self.settings.hermes_home),
                skills_synced=self.skill_sync.complete(),
                integration_mode="sdk_embedded",
                sdk_module=sdk_probe.sdk_module,
                sdk_version=sdk_probe.sdk_version,
                sdk_path=sdk_probe.sdk_path,
                embedded_agent_class=sdk_probe.embedded_agent_class,
                execution_mode="sdk_embedded",
                skills_path=str(self.skill_sync.skills_root()),
                **profile_status,
            )
        cli_probe = self.cli_adapter.version_probe()
        if not self.settings.hermes_require_sdk and cli_probe.status == "ready":
            logger.info("Hermes runtime adapter=%s mode=cli_fallback", self.cli_adapter.name)
            return HermesStatus(
                status="ready",
                reason=cli_probe.reason,
                adapter=self.cli_adapter.name,
                home=str(self.settings.project_root / self.settings.hermes_home),
                skills_synced=self.skill_sync.complete(),
                command_path=cli_probe.command_path,
                probe_command=cli_probe.probe_command,
                integration_mode="cli_fallback",
                sdk_module=sdk_probe.sdk_module,
                sdk_version=sdk_probe.sdk_version,
                sdk_path=sdk_probe.sdk_path,
                embedded_agent_class=sdk_probe.embedded_agent_class,
                cli_status=cli_probe.status,
                execution_mode="cli_oneshot",
                skills_path=str(self.skill_sync.skills_root()),
                **profile_status,
            )
        if self.settings.hermes_require_sdk:
            reason = sdk_probe.reason
            if cli_probe.status == "ready":
                reason = f"{reason} CLI diagnostic is available but SDK embedding is required."
            logger.info("Hermes runtime adapter=%s mode=sdk_required status=%s", self.python_adapter.name, sdk_probe.status)
            return HermesStatus(
                status=sdk_probe.status,
                reason=reason,
                adapter=self.python_adapter.name,
                home=str(self.settings.project_root / self.settings.hermes_home),
                skills_synced=self.skill_sync.complete(),
                command_path=cli_probe.command_path,
                probe_command=cli_probe.probe_command,
                integration_mode="sdk_required",
                sdk_module=sdk_probe.sdk_module,
                sdk_version=sdk_probe.sdk_version,
                sdk_path=sdk_probe.sdk_path,
                embedded_agent_class=sdk_probe.embedded_agent_class,
                cli_status=cli_probe.status,
                execution_mode="sdk_required",
                skills_path=str(self.skill_sync.skills_root()),
                **profile_status,
            )
        if self.cli_adapter.available():
            if cli_probe.status != "ready":
                return HermesStatus(
                    status=cli_probe.status,
                    reason=cli_probe.reason,
                    adapter=self.cli_adapter.name,
                    home=str(self.settings.project_root / self.settings.hermes_home),
                    skills_synced=self.skill_sync.complete(),
                    command_path=cli_probe.command_path,
                    probe_command=cli_probe.probe_command,
                    integration_mode="cli_fallback",
                    cli_status=cli_probe.status,
                    execution_mode="cli_oneshot",
                    skills_path=str(self.skill_sync.skills_root()),
                    **profile_status,
                )
            return HermesStatus(
                status="ready",
                reason=cli_probe.reason,
                adapter=self.cli_adapter.name,
                home=str(self.settings.project_root / self.settings.hermes_home),
                skills_synced=self.skill_sync.complete(),
                command_path=cli_probe.command_path,
                probe_command=cli_probe.probe_command,
                integration_mode="cli_fallback",
                cli_status=cli_probe.status,
                execution_mode="cli_oneshot",
                skills_path=str(self.skill_sync.skills_root()),
                **profile_status,
            )
        return HermesStatus(
            status="blocked_missing_runtime",
            reason=sdk_probe.reason,
            adapter=None,
            home=str(self.settings.project_root / self.settings.hermes_home),
            skills_synced=self.skill_sync.complete(),
            integration_mode="sdk_required",
            sdk_module=sdk_probe.sdk_module,
            cli_status=cli_probe.status,
            execution_mode="blocked",
            skills_path=str(self.skill_sync.skills_root()),
            **profile_status,
        )
