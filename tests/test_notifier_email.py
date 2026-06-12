from urllib.parse import parse_qs

import httpx
from sqlalchemy import select

from aunix.models import Agent, Finding, Notification, Run
from aunix.notifier_email import EmailNotifier, MailgunNotifier
from aunix.testing import make_spec
from aunix.spec import NotificationRule


def seed_finding(session):
    agent = Agent(owner="david", spec={}, status="active")
    session.add(agent)
    session.flush()
    run = Run(agent_id=agent.id, trigger="manual")
    session.add(run)
    session.flush()
    finding = Finding(agent_id=agent.id, run_id=run.id, dedupe_key="k",
                      summary="PO-4567 delayed 2 days", recommendation="Contact supplier")
    session.add(finding)
    session.flush()
    return finding


def email_spec():
    return make_spec(notifications=NotificationRule(channels=["email"], email_to="david@example.com"))


def make_notifier(session, handler):
    client = httpx.Client(base_url="https://api.resend.com", transport=httpx.MockTransport(handler))
    return EmailNotifier(session, api_key="re_test", from_address="alerts@aunix.dev", client=client)


def test_sends_email_and_records_sent(session):
    finding = seed_finding(session)
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"id": "email-1"})

    make_notifier(session, handler).send(finding, email_spec())

    note = session.scalars(select(Notification)).one()
    assert note.status == "sent"
    assert note.channel == "email"
    assert captured["to"] == ["david@example.com"]
    assert "PO-4567" in captured["subject"]
    assert "Contact supplier" in captured["html"]


def test_delivery_failure_records_failed_and_does_not_raise(session):
    finding = seed_finding(session)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "smtp down"})

    make_notifier(session, handler).send(finding, email_spec())  # must not raise

    note = session.scalars(select(Notification)).one()
    assert note.status == "failed"


def test_html_in_finding_fields_is_escaped(session):
    finding = seed_finding(session)
    finding.summary = 'PO <a href="https://evil.example">click</a>'
    session.flush()
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"id": "email-1"})

    make_notifier(session, handler).send(finding, email_spec())
    assert "<a href" not in captured["html"].replace("&lt;", "<", 0)  # raw tag must not appear
    assert "&lt;a href" in captured["html"]


# ── Mailgun (Basic auth, form-encoded) ──────────────────────────────────────

def make_mailgun(session, handler):
    client = httpx.Client(base_url="https://api.mailgun.net", transport=httpx.MockTransport(handler))
    return MailgunNotifier(session, api_key="key-test", domain="mail.aunix.dev",
                           from_address="Aunix <alerts@mail.aunix.dev>", client=client)


def test_mailgun_posts_form_to_domain_and_records_sent(session):
    finding = seed_finding(session)
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["auth"] = request.headers.get("authorization", "")
        captured["form"] = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        return httpx.Response(200, json={"id": "<msg@mail.aunix.dev>", "message": "Queued"})

    make_mailgun(session, handler).send(finding, email_spec())

    note = session.scalars(select(Notification)).one()
    assert note.status == "sent"
    assert captured["path"] == "/v3/mail.aunix.dev/messages"
    assert captured["auth"].startswith("Basic ")  # api:<key>
    assert captured["form"]["to"] == "david@example.com"
    assert "PO-4567" in captured["form"]["subject"]
    assert "Contact supplier" in captured["form"]["html"]


def test_mailgun_failure_records_failed_and_does_not_raise(session):
    finding = seed_finding(session)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid private key"})

    make_mailgun(session, handler).send(finding, email_spec())  # must not raise

    note = session.scalars(select(Notification)).one()
    assert note.status == "failed"
