from datetime import datetime, timezone

from sqlalchemy import select

from aunix.actions.planner import RuleBasedActionPlanner
from aunix.connectors.simship import SimShip
from aunix.models import Action, Agent
from aunix.notifier import FeedNotifier
from aunix.reasoning import RuleBasedReasoner
from aunix.runner import execute_run
from aunix.actions.executors import ResolveActionExecutor, TaskActionExecutor
from aunix.spec import ActionPermission, ActionPolicy
from aunix.testing import make_spec

INTERNAL_EXECUTORS = {"resolve": ResolveActionExecutor(), "task": TaskActionExecutor()}

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)


def make_agent(session, **overrides):
    agent = Agent(owner="t", status="active", spec=make_spec(**overrides).model_dump(mode="json"))
    session.add(agent); session.commit()
    return agent


def run(session, agent, sim, *, planner=None, enabled=True, executors=None):
    return execute_run(session, agent, {"simship": sim}, RuleBasedReasoner(), [FeedNotifier(session)],
                       now=NOW, action_planner=planner or RuleBasedActionPlanner(), actions_enabled=enabled,
                       executors=executors)


def test_l3_run_proposes_pending_actions(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW); sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session, autonomy_level=3, actions=[ActionPermission(type="resolve")])
    r = run(session, agent, sim)
    assert r.trace["actions"] == {"proposed": 1, "auto_executed": 0, "queued": 1, "failed": 0}
    act = session.scalars(select(Action)).one()
    assert act.type == "resolve" and act.status == "pending" and act.origin == "L3"


def test_no_act_phase_below_l3(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW); sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session)  # autonomy 1, no actions
    r = run(session, agent, sim)
    assert "actions" not in r.trace
    assert session.scalars(select(Action)).all() == []


def test_kill_switch_blocks_proposals(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW); sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session, autonomy_level=3, actions=[ActionPermission(type="resolve")])
    r = run(session, agent, sim, enabled=False)
    assert session.scalars(select(Action)).all() == []


def test_rerun_does_not_duplicate_actions(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW); sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session, autonomy_level=3, actions=[ActionPermission(type="resolve")])
    run(session, agent, sim)
    run(session, agent, sim)
    assert len(session.scalars(select(Action)).all()) == 1


def test_l4_auto_executes_whitelisted_action(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW); sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session, autonomy_level=4, actions=[ActionPermission(type="resolve")],
                       policy=ActionPolicy(resolve_auto=True))
    r = run(session, agent, sim, executors=INTERNAL_EXECUTORS)
    assert r.trace["actions"] == {"proposed": 1, "auto_executed": 1, "queued": 0, "failed": 0}
    act = session.scalars(select(Action)).one()
    assert act.origin == "L4" and act.policy_decision == "auto"
    assert act.status == "executed" and act.decided_by == "policy"


def test_l4_out_of_policy_falls_back_to_queue(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW); sim.slip_delivery("PO-4567", days=2)
    # resolve permitted but NOT whitelisted for auto -> queues for approval (L4 ⊆ L3)
    agent = make_agent(session, autonomy_level=4, actions=[ActionPermission(type="resolve")],
                       policy=ActionPolicy(resolve_auto=False))
    r = run(session, agent, sim, executors=INTERNAL_EXECUTORS)
    assert r.trace["actions"] == {"proposed": 1, "auto_executed": 0, "queued": 1, "failed": 0}
    act = session.scalars(select(Action)).one()
    assert act.origin == "L4" and act.policy_decision == "queued" and act.status == "pending"
