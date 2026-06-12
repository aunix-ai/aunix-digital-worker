from aunix.config import Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.database_url == "sqlite:///aunix.db"
    assert s.llm_model == "gpt-5.1"
    assert s.resend_api_key is None
    assert s.hubspot_access_token is None


def test_env_override(monkeypatch):
    monkeypatch.setenv("AUNIX_LLM_MODEL", "gpt-4.1")
    monkeypatch.setenv("AUNIX_DATABASE_URL", "postgresql://localhost/aunix")
    s = Settings(_env_file=None)
    assert s.llm_model == "gpt-4.1"
    assert s.database_url == "postgresql://localhost/aunix"


def test_llm_model_reads_bare_openai_model_var(monkeypatch):
    # OPENAI_MODEL (no AUNIX_ prefix) lines up with the OpenAI SDK's OPENAI_API_KEY
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1-mini")
    s = Settings(_env_file=None)
    assert s.llm_model == "gpt-5.1-mini"
