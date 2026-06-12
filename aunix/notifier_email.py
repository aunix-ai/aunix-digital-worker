"""Email notifier via the Resend HTTP API. A delivery failure records a
'failed' Notification row instead of raising - the run already produced the
finding and the in-app feed carries it; email is best-effort delivery."""
import logging
from html import escape

import httpx
from sqlalchemy.orm import Session

from aunix.models import Finding, Notification
from aunix.spec import AgentSpec

logger = logging.getLogger(__name__)


class EmailNotifier:
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
                    "subject": f"[Aunix] {finding.summary}",
                    "html": self._render(finding, spec),
                },
            )
            resp.raise_for_status()
            note.status = "sent"
        except httpx.HTTPError:
            logger.exception("email delivery failed for finding %s", finding.id)
            note.status = "failed"
        self.session.flush()

    def _render(self, finding: Finding, spec: AgentSpec) -> str:
        return (
            f"<h2>{escape(finding.summary)}</h2>"
            f"<p><strong>Recommended action:</strong> {escape(finding.recommendation)}</p>"
            f"<p><strong>Source:</strong> {escape(finding.source_ref)}</p>"
            f"<p>Agent: {escape(spec.name)} &mdash; severity {finding.severity}. "
            f"Run #{finding.run_id} has the full decision trace.</p>"
        )
