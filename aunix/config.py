"""Runtime configuration. All knobs come from AUNIX_* env vars or .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUNIX_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///aunix.db"
    llm_model: str = "claude-opus-4-8"
    # Anthropic credentials resolve via the SDK's own chain (ANTHROPIC_API_KEY etc.)
    resend_api_key: str | None = None
    email_from: str = "alerts@aunix.local"
    hubspot_access_token: str | None = None
    simship_state_path: str = "data/simship.json"
    upload_dir: str = "data/uploads"
    api_cors_origins: list[str] = ["http://localhost:3000"]
