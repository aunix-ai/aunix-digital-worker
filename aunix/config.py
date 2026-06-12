"""Runtime configuration. Most knobs come from AUNIX_* env vars or .env; the LLM
model also accepts the bare OPENAI_MODEL var so it lines up with the OpenAI SDK's
own OPENAI_API_KEY."""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUNIX_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///aunix.db"
    # OpenAI credentials resolve via the SDK's own chain (OPENAI_API_KEY).
    llm_model: str = Field(
        default="gpt-5.1",
        validation_alias=AliasChoices("AUNIX_LLM_MODEL", "OPENAI_MODEL"),
    )
    email_from: str = "alerts@aunix.local"
    # Email gateway. Mailgun (Basic auth, form-encoded) is preferred when set;
    # Resend is the fallback. Bare MAILGUN_*/RESEND_* vars are accepted too.
    mailgun_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUNIX_MAILGUN_API_KEY", "MAILGUN_API_KEY"),
    )
    mailgun_domain: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUNIX_MAILGUN_DOMAIN", "MAILGUN_DOMAIN"),
    )
    # US: https://api.mailgun.net   EU: https://api.eu.mailgun.net
    mailgun_base_url: str = Field(
        default="https://api.mailgun.net",
        validation_alias=AliasChoices("AUNIX_MAILGUN_BASE_URL", "MAILGUN_BASE_URL"),
    )
    resend_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUNIX_RESEND_API_KEY", "RESEND_API_KEY"),
    )
    # HubSpot private-app access token (Bearer). Accepts the bare HUBSPOT_* vars too.
    hubspot_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AUNIX_HUBSPOT_ACCESS_TOKEN", "HUBSPOT_ACCESS_TOKEN", "HUBSPOT_ID"
        ),
    )
    simship_state_path: str = "data/simship.json"
    upload_dir: str = "data/uploads"
    api_cors_origins: list[str] = ["http://localhost:3000"]
