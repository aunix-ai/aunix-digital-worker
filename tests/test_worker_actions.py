# tests/test_worker_actions.py
from datetime import datetime, timezone

from sqlalchemy import select

from aunix.actions.planner import RuleBasedActionPlanner
from aunix.connectors.simship import SimShip
from aunix.models import Action, Agent
from aunix.spec import ActionPermission
from aunix.testing import FixedRuntime, make_spec
from aunix.worker import run_agent_once
from tests.test_worker import make_session_factory  # reuse existing helper

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)


def test_run_agent_once_proposes_actions_when_enabled(session, tmp_path):
    agent = Agent(owner="t", status="active",
                  spec=make_spec(autonomy_level=3, actions=[ActionPermission(type="resolve")]).model_dump(mode="json"))
    session.add(agent); session.commit()
    sim_path = tmp_path / "s.json"
    SimShip(sim_path, now=lambda: NOW).slip_delivery("PO-4567", days=2)
    runtime = FixedRuntime(sim_path, now=lambda: NOW)
    runtime.actions_enabled = True
    runtime.action_planner = RuleBasedActionPlanner()
    run = run_agent_once(make_session_factory(session), agent.id, runtime, trigger="manual", now=NOW)
    assert run.trace["actions"]["proposed"] == 1
    assert session.scalars(select(Action)).one().status == "pending"
