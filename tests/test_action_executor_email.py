from urllib.parse import parse_qs

import httpx
import pytest

from aunix.actions.executors import EmailActionExecutor
from aunix.models import Action, Agent, Finding, Run
from aunix.testing import make_spec


def seed(session, params):
    a = Agent(owner="d", spec={}, status="active"); session.add(a); session.flush()
    r = Run(agent_id=a.id, trigger="manual"); session.add(r); session.flush()
    f = Finding(agent_id=a.id, run_id=r.id, dedupe_key="k", summary="s"); session.add(f); session.flush()
    act = Action(agent_id=a.id, run_id=r.id, finding_id=f.id, type="email",
                 params=params, dedupe_key="k:email", origin="L3"); session.add(act); session.flush()
    return act, f


def make_exec(handler):
    client = httpx.Client(base_url="https://api.mailgun.net", transport=httpx.MockTransport(handler))
    return EmailActionExecutor(api_key="key-x", domain="mail.aunix.ai",
                               default_from="Aunix <alerts@mail.aunix.ai>", client=client)


def test_email_executor_posts_to_mailgun(session):
    act, f = seed(session, {"to": "orders@acme.com", "subject": "Re PO-4567", "body": "Hi"})
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["form"] = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        return httpx.Response(200, json={"id": "<m@mail.aunix.ai>", "message": "Queued"})

    result = make_exec(handler).execute(session, act, f, make_spec())
    assert captured["path"] == "/v3/mail.aunix.ai/messages"
    assert captured["form"]["to"] == "orders@acme.com"
    assert captured["form"]["subject"] == "Re PO-4567"
    assert result["message_id"] == "<m@mail.aunix.ai>"


def test_email_executor_requires_a_recipient(session):
    act, f = seed(session, {"subject": "S", "body": "B"})  # no "to"
    with pytest.raises(ValueError):
        make_exec(lambda r: httpx.Response(200)).execute(session, act, f, make_spec())


def test_email_executor_raises_on_http_error(session):
    act, f = seed(session, {"to": "x@y.com", "subject": "S", "body": "B"})
    with pytest.raises(httpx.HTTPStatusError):
        make_exec(lambda r: httpx.Response(401, json={"message": "bad key"})).execute(session, act, f, make_spec())
