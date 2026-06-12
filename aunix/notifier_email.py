"""Email notifiers. MailgunNotifier (Basic auth, form-encoded) and EmailNotifier
(Resend, Bearer + JSON) both implement the Notifier protocol. A delivery failure
records a 'failed' Notification row instead of raising - the run already produced
the finding and the in-app feed carries it; email is best-effort delivery."""
import logging
from html import escape

import httpx
from sqlalchemy.orm import Session

from aunix.models import Finding, Notification
from aunix.spec import AgentSpec

logger = logging.getLogger(__name__)


def render_html(finding: Finding, spec: AgentSpec) -> str:
    return (
        f"<h2>{escape(finding.summary)}</h2>"
        f"<p><strong>Recommended action:</strong> {escape(finding.recommendation)}</p>"
        f"<p><strong>Source:</strong> {escape(finding.source_ref)}</p>"
        f"<p>Agent: {escape(spec.name)} &mdash; severity {finding.severity}. "
        f"Run #{finding.run_id} has the full decision trace.</p>"
    )


def subject_for(finding: Finding) -> str:
    return f"[Aunix] {finding.summary}"


class MailgunNotifier:
    """Email via the Mailgun HTTP API (Basic auth `api:<key>`, form-encoded)."""

    channel = "email"

    def __init__(self, session: Session, api_key: str, domain: str, from_address: str,
                 base_url: str = "https://api.mailgun.net", client: httpx.Client | None = None):
        self.session = session
        self.domain = domain
        self.from_address = from_address
        self._auth = ("api", api_key)  # applied per request so an injected client still authenticates
        self.client = client or httpx.Client(base_url=base_url, timeout=30)

    def send(self, finding: Finding, spec: AgentSpec) -> None:
        note = Notification(finding_id=finding.id, channel=self.channel, status="pending")
        self.session.add(note)
        self.session.flush()
        try:
            resp = self.client.post(
                f"/v3/{self.domain}/messages",
                auth=self._auth,
                data={
                    "from": self.from_address,
                    "to": spec.notifications.email_to,
                    "subject": subject_for(finding),
                    "html": render_html(finding, spec),
                },
            )
            resp.raise_for_status()
            note.status = "sent"
        except httpx.HTTPError:
            logger.exception("mailgun delivery failed for finding %s", finding.id)
            note.status = "failed"
        self.session.flush()


class EmailNotifier:
    """Email via the Resend HTTP API (Bearer auth, JSON body)."""

    channel = "email"

    def __init__(self, session: Session, api_key: str, from_address: str,
                 client: httpx.Client | None = None):
        self.session = session
        self.from_address = from_address
        self.client = client or httpx.Client(
            base_url="https://api.resend.com",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )

    def send(self, finding: Finding, spec: AgentSpec) -> None:
        note = Notification(finding_id=finding.id, channel=self.channel, status="pending")
        self.session.add(note)
        self.session.flush()
        try:
            resp = self.client.post(
                "/emails",
                json={
                    "from": self.from_address,
                    "to": [spec.notifications.email_to],
                    "subject": subject_for(finding),
                    "html": render_html(finding, spec),
                },
            )
            resp.raise_for_status()
            note.status = "sent"
        except httpx.HTTPError:
            logger.exception("email delivery failed for finding %s", finding.id)
            note.status = "failed"
        self.session.flush()
