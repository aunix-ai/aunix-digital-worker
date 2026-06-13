from datetime import datetime, timezone

from sqlalchemy import select

from aunix.actions.planner import RuleBasedActionPlanner
from aunix.connectors.simship import SimShip
from aunix.models import Action, Agent
from aunix.notifier import FeedNotifier
from aunix.reasoning import RuleBasedReasoner
from aunix.runner import execute_run
from aunix.spec import ActionPermission
from aunix.testing import make_spec

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)


def make_agent(session, **overrides):
    agent = Agent(owner="t", status="active", spec=make_spec(**overrides).model_dump(mode="json"))
    session.add(agent); session.commit()
    return agent


def run(session, agent, sim, *, planner=None, enabled=True):
    return execute_run(session, agent, {"simship": sim}, RuleBasedReasoner(), [FeedNotifier(session)],
                       now=NOW, action_planner=planner or RuleBasedActionPlanner(), actions_enabled=enabled)


def test_l3_run_proposes_pending_actions(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW); sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session, autonomy_level=3, actions=[ActionPermission(type="resolve")])
    r = run(session, agent, sim)
    assert r.trace["actions"] == {"proposed": 1, "queued": 1}
    act = session.scalars(select(Action)).one()
    assert act.type == "resolve" and act.status == "pending"


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
