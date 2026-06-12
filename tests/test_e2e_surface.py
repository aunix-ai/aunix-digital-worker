"""Full product-surface smoke: conversational creation through to an alert in
the feed, all offline (FakeLlm + SimShip). Uses the real clock throughout so
the 48h staleness rule can never fire spuriously as the calendar advances."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aunix.api import create_app
from aunix.compiler import CompiledIntent
from aunix.connectors.simship import SimShip
from aunix.llm import FakeLlm
from aunix.models import Base
from aunix.testing import FixedRuntime, make_spec


@pytest.fixture
def harness(tmp_path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    sim_path = tmp_path / "s.json"
    app = create_app(session_factory=factory, llm=FakeLlm([CompiledIntent(spec=make_spec())]),
                     runtime=FixedRuntime(sim_path), upload_dir=tmp_path / "up")
    return TestClient(app), sim_path


def test_breach_reaches_feed_exactly_once(harness):
    client, sim_path = harness

    # conversational creation
    spec = client.post("/agents/compile", json={"text": "watch my POs"}).json()["spec"]
    agent_id = client.post("/agents", json={"owner": "david", "spec": spec}).json()["id"]
    client.post(f"/agents/{agent_id}/activate")

    # trigger a live delay in the simulated ERP (real clock: seed stays fresh)
    SimShip(sim_path).slip_delivery("PO-4567", days=2)

    run1 = client.post(f"/agents/{agent_id}/run").json()
    assert run1["status"] == "succeeded"
    feed = client.get("/feed").json()
    assert len(feed) == 1
    assert "PO-4567" in feed[0]["finding"]["summary"]

    # second run: ongoing breach stays quiet
    client.post(f"/agents/{agent_id}/run")
    assert len(client.get("/feed").json()) == 1

    # the alert links to an explainable trace
    trace = client.get(f"/runs/{run1['id']}").json()
    assert trace["trace"]["breaches"] == ["PO-4567"]
    assert trace["findings"][0]["dedupe_key"] == "PO-4567:delivery_date"
