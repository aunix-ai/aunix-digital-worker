from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from aunix.actions.service import ActionStateError, execute_action, expire_actions
from aunix.models import Action, Agent, Finding, Run
from aunix.testing import make_spec

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)


class OkExecutor:
    type = "resolve"
    def execute(self, session, action, finding, spec):
        finding.state = "resolved"
        return {"resolved_finding_id": finding.id}


class BoomExecutor:
    type = "resolve"
    def execute(self, session, action, finding, spec):
        raise RuntimeError("executor blew up")


def seed(session, status="pending", expires_at=NOW + timedelta(hours=1)):
    a = Agent(owner="d", spec=make_spec().model_dump(mode="json"), status="active"); session.add(a); session.flush()
    r = Run(agent_id=a.id, trigger="manual"); session.add(r); session.flush()
    f = Finding(agent_id=a.id, run_id=r.id, dedupe_key="k", summary="s", state="new"); session.add(f); session.flush()
    act = Action(agent_id=a.id, run_id=r.id, finding_id=f.id, type="resolve", params={},
                 dedupe_key="k:resolve", origin="L3", status=status, expires_at=expires_at)
    session.add(act); session.flush()
    return act, f


def test_execute_runs_executor_and_records_executed(session):
    act, f = seed(session)
    execute_action(session, act, {"resolve": OkExecutor()}, now=NOW, decided_by="alice")
    assert act.status == "executed"
    assert act.result == {"resolved_finding_id": f.id}
    assert act.decided_by == "alice" and act.executed_at == NOW
    assert f.state == "resolved"


def test_executor_failure_records_failed_not_raised(session):
    act, f = seed(session)
    execute_action(session, act, {"resolve": BoomExecutor()}, now=NOW, decided_by="alice")
    assert act.status == "failed"
    assert "blew up" in act.error


def test_cannot_execute_non_pending(session):
    act, f = seed(session, status="rejected")
    with pytest.raises(ActionStateError):
        execute_action(session, act, {"resolve": OkExecutor()}, now=NOW, decided_by="x")


def test_cannot_execute_expired(session):
    act, f = seed(session, expires_at=NOW - timedelta(hours=1))
    with pytest.raises(ActionStateError):
        execute_action(session, act, {"resolve": OkExecutor()}, now=NOW, decided_by="x")


def test_expire_sweep_marks_stale_pending_expired(session):
    stale, _ = seed(session, expires_at=NOW - timedelta(hours=1))
    fresh, _ = seed(session, expires_at=NOW + timedelta(hours=1))
    n = expire_actions(session, now=NOW)
    assert n == 1
    assert session.get(Action, stale.id).status == "expired"
    assert session.get(Action, fresh.id).status == "pending"
