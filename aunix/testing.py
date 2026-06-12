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


class FixedRuntime:
    """Offline runtime for tests: SimShip only, rule-based reasoner, feed
    notifier. Satisfies the same duck type as aunix.runtime.Runtime."""

    def __init__(self, sim_path, now=None):
        from aunix.reasoning import RuleBasedReasoner

        self.sim_path = sim_path
        self.now = now
        self.reasoner = RuleBasedReasoner()

    def connectors(self, session):
        from aunix.connectors.simship import SimShip

        kwargs = {"now": self.now} if self.now else {}
        return {"simship": SimShip(self.sim_path, **kwargs)}

    def notifiers(self, session):
        from aunix.notifier import FeedNotifier

        return [FeedNotifier(session)]
