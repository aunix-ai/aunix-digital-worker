"""Notifier protocol. FeedNotifier writes in-app feed records; the email
notifier (Plan 2) implements the same protocol."""
from typing import Protocol

from sqlalchemy.orm import Session

from aunix.models import Finding, Notification
from aunix.spec import AgentSpec


class Notifier(Protocol):
    channel: str

    def send(self, finding: Finding, spec: AgentSpec) -> None: ...


class FeedNotifier:
    channel = "feed"

    def __init__(self, session: Session):
        self.session = session

    def send(self, finding: Finding, spec: AgentSpec) -> None:
        self.session.add(
            Notification(finding_id=finding.id, channel=self.channel, status="sent")
        )
        self.session.flush()
