"""L3 end-to-end through the API: a breach proposes an action, it lands pending,
approval executes it and audits the result — all offline (FakeLlm + SimShip +
internal resolve executor, no external API)."""
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
from aunix.spec import ActionPermission
from aunix.testing import FixedRuntime, make_spec


@pytest.fixture
def harness(tmp_path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    sim_path = tmp_path / "s.json"
    runtime = FixedRuntime(sim_path)
    runtime.actions_enabled = True
    app = create_app(session_factory=factory, llm=FakeLlm([CompiledIntent(spec=make_spec())]),
                     runtime=runtime, upload_dir=tmp_path / "up")
    return TestClient(app), sim_path


def test_l3_breach_to_approved_action(harness):
    client, sim_path = harness
    spec = make_spec(autonomy_level=3, actions=[ActionPermission(type="resolve")]).model_dump(mode="json")
    agent_id = client.post("/agents", json={"owner": "david", "spec": spec}).json()["id"]
    client.post(f"/agents/{agent_id}/activate")

    SimShip(sim_path).slip_delivery("PO-4567", days=2)
    run = client.post(f"/agents/{agent_id}/run").json()
    assert run["status"] == "succeeded"
    assert run["trace"]["actions"]["proposed"] == 1

    pending = client.get("/actions?status=pending").json()
    assert len(pending) == 1
    assert pending[0]["type"] == "resolve"
    assert "PO-4567" in pending[0]["finding"]["summary"]

    approved = client.post(f"/actions/{pending[0]['id']}/approve").json()
    assert approved["status"] == "executed"
    assert client.get("/actions?status=pending").json() == []  # cleared
