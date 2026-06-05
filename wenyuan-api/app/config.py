import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_local_env() -> None:
    api_root = Path(__file__).resolve().parents[1]
    for env_file in (api_root / ".env.local", api_root / ".env"):
        if not env_file.exists():
            continue
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_local_env()


def _load_local_model_configs() -> dict[str, dict[str, str]]:
    api_root = Path(__file__).resolve().parents[1]
    config_file = os.getenv("LLM_MODEL_CONFIG_FILE", ".llm.models.local.json")
    config_path = Path(config_file)
    if not config_path.is_absolute():
        config_path = api_root / config_path
    if not config_path.exists():
        return {}
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    configs: dict[str, dict[str, str]] = {}
    for name, item in raw.items():
        if not isinstance(item, dict):
            continue
        normalized_name = str(name).strip().lower()
        if not normalized_name:
            continue
        configs[normalized_name] = {str(key): str(value) for key, value in item.items() if value is not None}
    return configs


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "文渊问史 API")
    app_env: str = os.getenv("APP_ENV", "development")
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-change-me")
    access_token_expire_minutes: int = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 1440)
    database_url: str = os.getenv("DATABASE_URL") or "sqlite:///./wenyuan.db"
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    llm_provider: str = os.getenv("LLM_PROVIDER", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_model_configs: dict[str, dict[str, str]] = field(default_factory=_load_local_model_configs)

    @property
    def using_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def llm_enabled(self) -> bool:
        has_global_config = bool(self.llm_api_key and self.llm_base_url and self.llm_model)
        has_model_config = any(
            item.get("api_key") and item.get("base_url") and (item.get("model") or item.get("model_id"))
            for item in self.llm_model_configs.values()
        )
        return has_global_config or has_model_config


settings = Settings()
