from datetime import datetime, timezone

from aunix.findings import CandidateFinding, reconcile
from aunix.models import Agent, Run

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def seed_agent_run(session):
    agent = Agent(owner="david", spec={}, status="active")
    session.add(agent)
    session.flush()
    run = Run(agent_id=agent.id, trigger="manual")
    session.add(run)
    session.flush()
    return agent, run


def new_run(session, agent):
    run = Run(agent_id=agent.id, trigger="manual")
    session.add(run)
    session.flush()
    return run


def cand(key="PO-4567:delivery_date"):
    return CandidateFinding(
        dedupe_key=key,
        severity="warning",
        summary="PO-4567 delayed 2 days",
        recommendation="Contact supplier",
        source_ref="simship://PO-4567",
    )


def test_first_breach_creates_new_finding(session):
    agent, run = seed_agent_run(session)
    result = reconcile(session, agent.id, run.id, [cand()], now=NOW)
    assert [f.state for f in result.new] == ["new"]
    assert result.ongoing == []
    assert result.resolved == []


def test_repeat_breach_is_ongoing_not_new(session):
    agent, run = seed_agent_run(session)
    reconcile(session, agent.id, run.id, [cand()], now=NOW)
    run2 = new_run(session, agent)
    result = reconcile(session, agent.id, run2.id, [cand()], now=NOW)
    assert result.new == []
    assert [f.state for f in result.ongoing] == ["ongoing"]


def test_cleared_breach_resolves(session):
    agent, run = seed_agent_run(session)
    reconcile(session, agent.id, run.id, [cand()], now=NOW)
    run2 = new_run(session, agent)
    result = reconcile(session, agent.id, run2.id, [], now=NOW)
    assert [f.state for f in result.resolved] == ["resolved"]


def test_resolved_breach_realerts_if_it_returns(session):
    agent, run = seed_agent_run(session)
    reconcile(session, agent.id, run.id, [cand()], now=NOW)
    run2 = new_run(session, agent)
    reconcile(session, agent.id, run2.id, [], now=NOW)  # resolves
    run3 = new_run(session, agent)
    result = reconcile(session, agent.id, run3.id, [cand()], now=NOW)
    assert len(result.new) == 1  # returning breach alerts again
