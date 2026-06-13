import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aunix.api import create_app
from aunix.compiler import CompiledIntent
from aunix.llm import FakeLlm
from aunix.models import Action, Agent, Base, Finding, Run
from aunix.testing import FixedRuntime, make_spec


@pytest.fixture
def client(tmp_path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    app = create_app(session_factory=factory, llm=FakeLlm([CompiledIntent(spec=make_spec())]),
                     runtime=FixedRuntime(tmp_path / "s.json"), upload_dir=tmp_path / "up")
    return TestClient(app), factory


def seed_pending(factory, atype="resolve", params=None):
    with factory() as s:
        a = Agent(owner="d", spec=make_spec().model_dump(mode="json"), status="active"); s.add(a); s.flush()
        r = Run(agent_id=a.id, trigger="manual"); s.add(r); s.flush()
        f = Finding(agent_id=a.id, run_id=r.id, dedupe_key="k", summary="PO-4567 delayed", state="new")
        s.add(f); s.flush()
        act = Action(agent_id=a.id, run_id=r.id, finding_id=f.id, type=atype, params=params or {},
                     dedupe_key=f"k:{atype}", origin="L3", status="pending"); s.add(act); s.commit()
        return act.id, f.id


def test_list_pending_actions_with_finding_context(client):
    tc, factory = client
    seed_pending(factory)
    body = tc.get("/actions?status=pending").json()
    assert len(body) == 1
    assert body[0]["type"] == "resolve"
    assert body[0]["finding"]["summary"] == "PO-4567 delayed"


def test_approve_executes_and_records(client):
    tc, factory = client
    aid, fid = seed_pending(factory, atype="resolve")
    resp = tc.post(f"/actions/{aid}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "executed"
    assert tc.get("/actions").json()[0]["status"] == "executed"


def test_approve_with_edited_params(client):
    tc, factory = client
    aid, fid = seed_pending(factory, atype="task", params={"title": "orig"})
    tc.post(f"/actions/{aid}/approve", json={"params": {"title": "edited title"}})
    from sqlalchemy import select
    with factory() as s:
        from aunix.models import Task
        assert s.scalars(select(Task)).one().title == "edited title"


def test_reject_marks_rejected(client):
    tc, factory = client
    aid, fid = seed_pending(factory)
    assert tc.post(f"/actions/{aid}/reject").json()["status"] == "rejected"


def test_approve_missing_action_404(client):
    tc, _ = client
    assert tc.post("/actions/999/approve").status_code == 404
