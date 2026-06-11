"""Factories for tests and demos."""
from aunix.spec import AgentSpec, Condition, ConditionGroup, NotificationRule, Schedule


def make_spec(**overrides) -> AgentSpec:
    base = dict(
        name="po-watcher",
        objective="Watch my active POs and alert me on delays",
        task_type="monitoring",
        data_sources=["simship"],
        record_key="po_number",
        conditions=ConditionGroup(
            mode="any",
            conditions=[
                Condition(field="delivery_date", operator="gt", value="expected_date"),
                Condition(field="last_tracking_update", operator="stale_hours", value=48),
            ],
        ),
        schedule=Schedule(mode="interval", interval_minutes=30),
        notifications=NotificationRule(channels=["feed"]),
        autonomy_level=1,
    )
    base.update(overrides)
    return AgentSpec(**base)
