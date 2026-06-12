import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aunix.api import create_app
from aunix.compiler import CompiledIntent
from aunix.llm import FakeLlm
from aunix.models import Base
from aunix.testing import FixedRuntime, make_spec


@pytest.fixture
def client(tmp_path):
    # StaticPool: TestClient drives the app from a worker thread; without a
    # single shared connection every session would see a fresh empty :memory: DB
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    fake_llm = FakeLlm([CompiledIntent(spec=make_spec())])
    app = create_app(session_factory=factory, llm=fake_llm,
                     runtime=FixedRuntime(tmp_path / "s.json"),
                     upload_dir=tmp_path / "uploads")
    return TestClient(app)


def test_compile_returns_interpreted_spec(client):
    resp = client.post("/agents/compile", json={"text": "watch my POs"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["spec"]["task_type"] == "monitoring"
    assert body["questions"] == []


def test_full_agent_lifecycle(client):
    # create from a confirmed spec
    resp = client.post("/agents", json={"owner": "david",
                                        "spec": make_spec().model_dump(mode="json")})
    assert resp.status_code == 201
    agent_id = resp.json()["id"]
    assert resp.json()["status"] == "draft"

    # activate
    assert client.post(f"/agents/{agent_id}/activate").json()["status"] == "active"
    assert client.get("/agents").json()[0]["id"] == agent_id

    # run now (healthy seed: no breaches, run succeeds)
    run = client.post(f"/agents/{agent_id}/run").json()
    assert run["status"] == "succeeded"
    assert run["trace"]["rows_fetched"] == 3

    # trace is queryable ("why did I get this alert?")
    trace = client.get(f"/runs/{run['id']}").json()
    assert trace["trace"]["breaches"] == []

    # runs listed per agent; feed empty (no findings)
    assert len(client.get(f"/agents/{agent_id}/runs").json()) == 1
    assert client.get("/feed").json() == []

    # pause
    assert client.post(f"/agents/{agent_id}/pause").json()["status"] == "paused"


def test_invalid_spec_rejected(client):
    bad = make_spec().model_dump(mode="json")
    bad["schedule"] = {"mode": "interval"}  # missing interval_minutes
    resp = client.post("/agents", json={"owner": "x", "spec": bad})
    assert resp.status_code == 422


def test_csv_upload_registers_connection(client):
    resp = client.post("/uploads/csv",
                       files={"file": ("leads.csv", b"lead,deal_size\nA,100\n", "text/csv")})
    assert resp.status_code == 201
    assert resp.json()["rows"] == 1


def test_missing_agent_404s(client):
    assert client.post("/agents/999/run").status_code == 404
    assert client.get("/runs/999").status_code == 404


def test_run_now_on_paused_agent_runs_once_but_stays_paused(client):
    resp = client.post("/agents", json={"owner": "d", "spec": make_spec().model_dump(mode="json")})
    agent_id = resp.json()["id"]
    client.post(f"/agents/{agent_id}/activate")
    client.post(f"/agents/{agent_id}/pause")

    run = client.post(f"/agents/{agent_id}/run").json()
    assert run["status"] == "succeeded"
    assert client.get(f"/agents/{agent_id}").json()["status"] == "paused"


def test_compile_returns_502_when_llm_unavailable(tmp_path):
    from aunix.llm import LlmError
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    app = create_app(session_factory=sessionmaker(bind=engine),
                     llm=FakeLlm([LlmError("api down")]),
                     runtime=FixedRuntime(tmp_path / "s.json"),
                     upload_dir=tmp_path / "up")
    resp = TestClient(app).post("/agents/compile", json={"text": "watch"})
    assert resp.status_code == 502


def test_non_utf8_csv_rejected(client):
    resp = client.post("/uploads/csv",
                       files={"file": ("x.csv", b"\xff\xfe\x00bad", "text/csv")})
    assert resp.status_code == 400
