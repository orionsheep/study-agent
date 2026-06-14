from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def load_dotenv_file(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if not name or name in os.environ:
            continue
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
            cleaned = cleaned[1:-1]
        os.environ[name] = cleaned


load_dotenv_file()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def missing_secret(value: str | None) -> bool:
    if value is None:
        return True
    cleaned = value.strip()
    return cleaned == "" or cleaned.startswith("replace_with")


@dataclass(frozen=True)
class Settings:
    app_env: str = _env("APP_ENV", "development")
    api_host: str = _env("API_HOST", "127.0.0.1")
    api_port: int = int(_env("API_PORT", "8000"))
    database_url: str = _env("DATABASE_URL", "sqlite:///.data/learnforge_dev.sqlite")
    redis_url: str = _env("REDIS_URL", "redis://localhost:6379/0")
    mimo_api_key: str = _env("MIMO_API_KEY", "")
    mimo_base_url: str = _env("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    mimo_text_model: str = _env("MIMO_TEXT_MODEL", "mimo-v2.5-pro")
    mimo_fast_model: str = _env("MIMO_FAST_MODEL", "mimo-v2.5")
    mimo_use_thinking: bool = _env("MIMO_USE_THINKING", "false").lower() == "true"
    mimo_timeout_seconds: int = int(_env("MIMO_TIMEOUT_SECONDS", "180"))
    mimo_max_tokens: int = int(_env("MIMO_MAX_TOKENS", "16384"))
    model_provider: str = _env("MODEL_PROVIDER", "gemini")
    gemini_api_key: str = _env("GEMINI_API_KEY", "")
    gemini_text_model: str = _env("GEMINI_TEXT_MODEL", "gemini-3.1-pro-preview")
    gemini_text_fallback_model: str = _env("GEMINI_TEXT_FALLBACK_MODEL", "gemini-3.5-flash")
    gemini_image_model: str = _env("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
    gemini_image_fallback_model: str = _env("GEMINI_IMAGE_FALLBACK_MODEL", "gemini-3-pro-image-preview")
    gemini_embedding_model: str = _env("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
    gemini_timeout_seconds: int = int(_env("GEMINI_TIMEOUT_SECONDS", _env("MIMO_TIMEOUT_SECONDS", "180")))
    gemini_connect_timeout_seconds: int = int(_env("GEMINI_CONNECT_TIMEOUT_SECONDS", "10"))
    gemini_max_tokens: int = int(_env("GEMINI_MAX_TOKENS", "32768"))
    image2_api_key: str = _env("IMAGE2_API_KEY", "")
    image2_base_url: str = _env("IMAGE2_BASE_URL", "")
    image2_model: str = _env("IMAGE2_MODEL", "")
    hermes_home: str = _env("HERMES_HOME", ".runtime/hermes")
    hermes_provider: str = _env("HERMES_PROVIDER", "gemini")
    hermes_require_sdk: bool = _env("HERMES_REQUIRE_SDK", "false").lower() == "true"
    hermes_command: str = _env("HERMES_COMMAND", "/Users/mychanging/.local/bin/hermes")
    hermes_task_timeout_seconds: int = int(_env("HERMES_TASK_TIMEOUT_SECONDS", "600"))
    hermes_sdk_path: str = _env("HERMES_SDK_PATH", "")
    hermes_sdk_site_packages: str = _env("HERMES_SDK_SITE_PACKAGES", "")
    hermes_toolsets: str = _env("HERMES_TOOLSETS", "web,file,vision")
    hermes_default_skills: str = _env(
        "HERMES_DEFAULT_SKILLS",
        "resource-bundle-skill,document-skill,mindmap-skill,quiz-skill,code-practice-skill,ppt-skill,guizang-ppt-skill,image-generation-skill,video-script-skill,reading-material-skill,custom-html-app-skill,notes-skill,dashboard-skill,verifier-skill,app-generation-skill,memory-update-skill,course-ingestion-skill,detailed-analysis-skill",
    )
    unified_orchestrator_enabled: bool = _env("UNIFIED_ORCHESTRATOR", "false").lower() == "true"
    vector_store: str = _env("VECTOR_STORE", "pgvector")

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def api_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def data_dir(self) -> Path:
        path = self.project_root / ".data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def sqlite_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url.replace("sqlite:///", "", 1)
            path = Path(raw)
            if not path.is_absolute():
                path = self.project_root / path
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        return self.data_dir / "learnforge_dev.sqlite"


@lru_cache
def get_settings() -> Settings:
    return Settings()
