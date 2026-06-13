from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from aunix.actions.planner import RuleBasedActionPlanner
from aunix.actions.service import propose_actions
from aunix.models import Action, Agent, Finding, Run
from aunix.spec import ActionPermission
from aunix.testing import make_spec

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)


def seed(session):
    a = Agent(owner="d", spec={}, status="active"); session.add(a); session.flush()
    r = Run(agent_id=a.id, trigger="manual"); session.add(r); session.flush()
    f = Finding(agent_id=a.id, run_id=r.id, dedupe_key="PO-4567:delivery_date", summary="s",
                source_ref="simship://PO-4567",
                details={"row": {"supplier_email": "orders@acme.com"}})
    session.add(f); session.flush()
    return a, r, f


def spec():
    return make_spec(autonomy_level=3, actions=[
        ActionPermission(type="email", to_field="supplier_email"),
        ActionPermission(type="resolve"),
    ])


def test_proposes_pending_actions_with_expiry(session):
    a, r, f = seed(session)
    created = propose_actions(session, spec(), f, r.id, RuleBasedActionPlanner(), now=NOW, ttl_hours=24)
    assert {x.type for x in created} == {"email", "resolve"}
    assert all(x.status == "pending" and x.origin == "L3" for x in created)
    email = next(x for x in created if x.type == "email")
    assert email.expires_at == NOW + timedelta(hours=24)


def test_dedupe_skips_already_proposed(session):
    a, r, f = seed(session)
    propose_actions(session, spec(), f, r.id, RuleBasedActionPlanner(), now=NOW, ttl_hours=24)
    again = propose_actions(session, spec(), f, r.id, RuleBasedActionPlanner(), now=NOW, ttl_hours=24)
    assert again == []  # nothing new
    assert len(session.scalars(select(Action)).all()) == 2  # still just the first two
