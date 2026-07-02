# tests/test_worker.py
from datetime import datetime, timezone

from sqlalchemy import select

from aunix.models import Agent, Run
from aunix.testing import FixedRuntime, make_spec
from aunix.worker import run_agent_once, slot_key_for

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def test_interval_slot_key_buckets_by_interval():
    spec = make_spec()  # interval_minutes=30
    k1 = slot_key_for(1, spec, NOW)
    k2 = slot_key_for(1, spec, NOW.replace(minute=10))  # same 30-min bucket
    k3 = slot_key_for(1, spec, NOW.replace(minute=40))  # next bucket
    assert k1 == k2
    assert k1 != k3


def test_daily_slot_key_is_per_day():
    from aunix.spec import Schedule
    spec = make_spec(schedule=Schedule(mode="daily", daily_time="08:00"))
    assert slot_key_for(2, spec, NOW) == "2:daily:2026-06-11"


def make_session_factory(session):
    class Factory:
        def __call__(self):
            return self

        def __enter__(self):
            return session

        def __exit__(self, *args):
            return False

    return Factory()


def seed_active_agent(session):
    agent = Agent(owner="t", status="active", spec=make_spec().model_dump(mode="json"))
    session.add(agent)
    session.commit()
    return agent


def test_scheduled_run_is_idempotent_per_slot(session, tmp_path):
    agent = seed_active_agent(session)
    factory = make_session_factory(session)
    runtime = FixedRuntime(tmp_path / "s.json", now=lambda: NOW)

    r1 = run_agent_once(factory, agent.id, runtime, trigger="interval", now=NOW)
    r2 = run_agent_once(factory, agent.id, runtime, trigger="interval", now=NOW)

    assert r1 is not None and r1.slot_key is not None
    assert r2 is None  # same slot, skipped
    assert len(session.scalars(select(Run)).all()) == 1


def test_manual_runs_have_no_slot_key_and_always_execute(session, tmp_path):
    agent = seed_active_agent(session)
    factory = make_session_factory(session)
    runtime = FixedRuntime(tmp_path / "s.json", now=lambda: NOW)

    r1 = run_agent_once(factory, agent.id, runtime, trigger="manual", now=NOW)
    r2 = run_agent_once(factory, agent.id, runtime, trigger="manual", now=NOW)

    assert r1 is not None and r1.slot_key is None
    assert r2 is not None


def test_paused_agent_does_not_run(session, tmp_path):
    agent = seed_active_agent(session)
    agent.status = "paused"
    session.commit()
    runtime = FixedRuntime(tmp_path / "s.json", now=lambda: NOW)
    assert run_agent_once(make_session_factory(session), agent.id, runtime, trigger="interval", now=NOW) is None


def test_slot_key_is_committed_atomically_with_the_run(session, tmp_path):
    agent = seed_active_agent(session)
    factory = make_session_factory(session)
    runtime = FixedRuntime(tmp_path / "s.json", now=lambda: NOW)

    run = run_agent_once(factory, agent.id, runtime, trigger="interval", now=NOW)
    session.expire_all()  # re-read committed state from the DB
    persisted = session.get(Run, run.id)
    assert persisted.slot_key == slot_key_for(agent.id, make_spec(), NOW)


def test_failed_run_still_claims_its_slot(session, tmp_path):
    class BoomRuntime(FixedRuntime):
        def connectors(self, inner_session, spec=None, *, owner=None):
            class Boom:
                source_id = "simship"

                def fetch(self):
                    raise RuntimeError("api down")

            return {"simship": Boom()}

    agent = seed_active_agent(session)
    factory = make_session_factory(session)
    runtime = BoomRuntime(tmp_path / "s.json")

    r1 = run_agent_once(factory, agent.id, runtime, trigger="interval", now=NOW)
    assert r1.status == "failed"
    session.expire_all()
    assert session.get(Run, r1.id).slot_key is not None  # failed run claims the slot

    r2 = run_agent_once(factory, agent.id, runtime, trigger="interval", now=NOW)
    assert r2 is None  # no hot-loop retry within the same slot
