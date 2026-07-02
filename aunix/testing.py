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
        from aunix.actions.planner import RuleBasedActionPlanner
        from aunix.reasoning import RuleBasedReasoner

        self.sim_path = sim_path
        self.now = now
        self.reasoner = RuleBasedReasoner()
        self.action_planner = RuleBasedActionPlanner()
        self.actions_enabled = False  # tests flip this to True when exercising the act phase

    def connectors(self, session, spec=None, *, owner=None):
        from aunix.connectors.simship import SimShip

        kwargs = {"now": self.now} if self.now else {}
        return {"simship": SimShip(self.sim_path, **kwargs)}

    def notifiers(self, session):
        from aunix.notifier import FeedNotifier

        return [FeedNotifier(session)]

    def executors(self, session, *, owner=None):
        from aunix.actions.executors import ResolveActionExecutor, TaskActionExecutor

        return {"task": TaskActionExecutor(), "resolve": ResolveActionExecutor()}
