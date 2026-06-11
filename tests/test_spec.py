import pytest
from pydantic import ValidationError

from aunix.spec import AgentSpec, Condition, NotificationRule, Schedule
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


def test_zero_interval_rejected():
    with pytest.raises(ValidationError):
        Schedule(mode="interval", interval_minutes=0)


def test_stale_hours_requires_numeric_value():
    with pytest.raises(ValidationError):
        Condition(field="last_tracking_update", operator="stale_hours", value="expected_date")


def test_top_n_must_be_positive():
    with pytest.raises(ValidationError):
        make_spec(top_n=0)
