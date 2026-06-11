import pytest
from pydantic import ValidationError

from aunix.spec import AgentSpec, NotificationRule, Schedule
from aunix.testing import make_spec


def test_round_trip():
    spec = make_spec()
    assert AgentSpec.model_validate_json(spec.model_dump_json()) == spec


def test_interval_schedule_requires_minutes():
    with pytest.raises(ValidationError):
        Schedule(mode="interval")


def test_daily_schedule_requires_time():
    with pytest.raises(ValidationError):
        Schedule(mode="daily")


def test_email_channel_requires_address():
    with pytest.raises(ValidationError):
        NotificationRule(channels=["email"])


def test_autonomy_capped_at_l2():
    with pytest.raises(ValidationError):
        make_spec(autonomy_level=3)
