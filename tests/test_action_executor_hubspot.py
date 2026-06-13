import httpx
import pytest

from aunix.actions.executors import HubSpotActionExecutor
from aunix.models import Action, Agent, Finding, Run
from aunix.testing import make_spec


def seed(session, params):
    a = Agent(owner="d", spec={}, status="active"); session.add(a); session.flush()
    r = Run(agent_id=a.id, trigger="manual"); session.add(r); session.flush()
    f = Finding(agent_id=a.id, run_id=r.id, dedupe_key="k", summary="s"); session.add(f); session.flush()
    act = Action(agent_id=a.id, run_id=r.id, finding_id=f.id, type="hubspot",
                 params=params, dedupe_key="k:hubspot", origin="L3"); session.add(act); session.flush()
    return act, f


def make_exec(handler):
    client = httpx.Client(base_url="https://api.hubapi.com", transport=httpx.MockTransport(handler))
    return HubSpotActionExecutor(access_token="pat-na2-x", client=client)


def test_add_note_creates_note_associated_to_deal(session):
    act, f = seed(session, {"op": "add_note", "deal_id": "123", "note": "Aunix flagged this"})
    captured = {}

    def handler(request):
        import json
        captured["path"] = request.url.path
        captured["auth"] = request.headers.get("authorization", "")
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": "note-9"})

    result = make_exec(handler).execute(session, act, f, make_spec())
    assert captured["path"] == "/crm/v3/objects/notes"
    assert captured["auth"] == "Bearer pat-na2-x"
    assert captured["body"]["properties"]["hs_note_body"] == "Aunix flagged this"
    assert any(a["to"]["id"] == "123" for a in captured["body"]["associations"])
    assert result["note_id"] == "note-9"


def test_unsupported_op_raises(session):
    act, f = seed(session, {"op": "delete_deal", "deal_id": "123"})
    with pytest.raises(ValueError):
        make_exec(lambda r: httpx.Response(200)).execute(session, act, f, make_spec())
