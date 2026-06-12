from aunix.config import Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.database_url == "sqlite:///aunix.db"
    assert s.llm_model == "claude-opus-4-8"
    assert s.resend_api_key is None
    assert s.hubspot_access_token is None


def test_env_override(monkeypatch):
    monkeypatch.setenv("AUNIX_LLM_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("AUNIX_DATABASE_URL", "postgresql://localhost/aunix")
    s = Settings(_env_file=None)
    assert s.llm_model == "claude-sonnet-4-6"
    assert s.database_url == "postgresql://localhost/aunix"
