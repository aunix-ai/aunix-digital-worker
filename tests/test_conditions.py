from datetime import datetime, timedelta, timezone

from aunix.conditions import evaluate
from aunix.spec import Condition, ConditionGroup

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def group(mode, *conds):
    return ConditionGroup(mode=mode, conditions=list(conds))


def test_numeric_threshold_breach():
    g = group("any", Condition(field="amount", operator="gt", value=1_000_000))
    breach = evaluate(g, {"amount": 2_500_000}, now=NOW)
    assert breach is not None
    assert breach.matched[0].field == "amount"


def test_no_breach_returns_none():
    g = group("any", Condition(field="amount", operator="gt", value=1_000_000))
    assert evaluate(g, {"amount": 10}, now=NOW) is None


def test_field_to_field_comparison():
    g = group("any", Condition(field="delivery_date", operator="gt", value="expected_date"))
    row = {"delivery_date": "2026-06-20", "expected_date": "2026-06-15"}
    assert evaluate(g, row, now=NOW) is not None


def test_stale_hours():
    g = group("any", Condition(field="last_tracking_update", operator="stale_hours", value=48))
    fresh = {"last_tracking_update": NOW - timedelta(hours=2)}
    stale = {"last_tracking_update": NOW - timedelta(hours=50)}
    assert evaluate(g, fresh, now=NOW) is None
    assert evaluate(g, stale, now=NOW) is not None


def test_all_mode_requires_every_condition():
    g = group(
        "all",
        Condition(field="delay_hours", operator="gt", value=24),
        Condition(field="priority", operator="eq", value="high"),
    )
    assert evaluate(g, {"delay_hours": 30, "priority": "low"}, now=NOW) is None
    assert evaluate(g, {"delay_hours": 30, "priority": "high"}, now=NOW) is not None


def test_missing_field_does_not_match():
    g = group("any", Condition(field="absent", operator="gt", value=1))
    assert evaluate(g, {"amount": 5}, now=NOW) is None
