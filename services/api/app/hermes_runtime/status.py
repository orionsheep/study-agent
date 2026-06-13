from __future__ import annotations

from pydantic import BaseModel


class HermesStatus(BaseModel):
    status: str
    reason: str
    adapter: str | None = None
    home: str
    skills_synced: bool = False
    command_path: str | None = None
    probe_command: list[str] | None = None
    integration_mode: str | None = None
    sdk_module: str | None = None
    sdk_version: str | None = None
    sdk_path: str | None = None
    embedded_agent_class: str | None = None
    cli_status: str | None = None
    execution_mode: str | None = None
    skills_path: str | None = None
    last_execution_status: str | None = None
    profile_path: str | None = None
    native_config_path: str | None = None
    profile_synced: bool = False
    configured_skills: list[str] = []
    enabled_toolsets: list[str] = []
    skills_status: str | None = None
    skills_detail: str | None = None
    tools_status: str | None = None
    tools_detail: str | None = None
    mcp_status: str | None = None
    mcp_detail: str | None = None
