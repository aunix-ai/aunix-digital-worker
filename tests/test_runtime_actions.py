import sqlalchemy as sa

from aunix.config import Settings
from aunix.db import make_session_factory
from aunix.models import Base
from aunix.runtime import Runtime


def rt():
    return Runtime(Settings(_env_file=None))


def test_actions_disabled_by_default():
    assert rt().settings.actions_enabled is False


def test_action_planner_present():
    assert rt().action_planner is not None


def test_executors_include_internal_always(session):
    base = rt().executors(session)
    assert {"task", "resolve"} <= set(base)
    assert "email" not in base  # no mailgun creds configured


def test_email_executor_present_when_mailgun_configured(session, monkeypatch):
    # the credentials resolve through the same bare env vars the app uses
    monkeypatch.setenv("MAILGUN_API_KEY", "key-x")
    monkeypatch.setenv("MAILGUN_DOMAIN", "mail.aunix.ai")
    runtime = Runtime(Settings(_env_file=None))
    assert "email" in runtime.executors(session)
