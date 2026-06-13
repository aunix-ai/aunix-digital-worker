# tests/test_worker_expiry.py
from datetime import datetime, timedelta, timezone

from aunix.models import Action, Agent, Finding, Run
from aunix.worker import sweep_expired_actions
from tests.test_worker import make_session_factory

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)


def test_sweep_expired_actions_marks_stale(session):
    a = Agent(owner="d", spec={}, status="active"); session.add(a); session.flush()
    r = Run(agent_id=a.id, trigger="manual"); session.add(r); session.flush()
    f = Finding(agent_id=a.id, run_id=r.id, dedupe_key="k", summary="s"); session.add(f); session.flush()
    stale = Action(agent_id=a.id, run_id=r.id, finding_id=f.id, type="resolve", params={},
                   dedupe_key="k:resolve", origin="L3", status="pending",
                   expires_at=NOW - timedelta(hours=1))
    session.add(stale); session.commit()
    n = sweep_expired_actions(make_session_factory(session), now=NOW)
    assert n == 1
    assert session.get(Action, stale.id).status == "expired"
