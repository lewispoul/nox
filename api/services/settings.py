from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://127.0.0.1:6379/0"
    artifacts_root: Path = Path("./artifacts").resolve()
    xtb_bin: str = "xtb"
    sse_heartbeat_sec: int = 15
    jobs_force_local: bool = False
    iam_use_remote: bool = False
    iam_base_url: str = ""

    @field_validator("iam_base_url")
    @classmethod
    def validate_iam_base_url(cls, v: str, info) -> str:
        """Validate that iam_base_url is provided when iam_use_remote is enabled."""
        # Access iam_use_remote from the values being validated
        iam_use_remote = info.data.get("iam_use_remote", False)
        if iam_use_remote and not v:
            raise ValueError(
                "iam_base_url must be configured when iam_use_remote is True. "
                "Set IAM_BASE_URL environment variable or update .env file."
            )
        if iam_use_remote and v and not v.startswith(("http://", "https://")):
            raise ValueError(
                f"iam_base_url must be a valid HTTP(S) URL, got: {v}"
            )
        return v


settings = Settings()
settings.artifacts_root.mkdir(parents=True, exist_ok=True)
