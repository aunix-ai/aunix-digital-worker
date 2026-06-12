# aunix/runtime.py
"""Assembles connectors/reasoner/notifiers from settings + DB state. Shared by
the API process (run-now) and the worker process (scheduled runs)."""
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from aunix.config import Settings
from aunix.connectors.base import Connector
from aunix.connectors.csv_source import CsvConnector
from aunix.connectors.hubspot import HubSpotConnector
from aunix.connectors.simship import SimShip
from aunix.llm import OpenAiLlm
from aunix.models import Connection
from aunix.notifier import FeedNotifier, Notifier
from aunix.notifier_email import EmailNotifier, MailgunNotifier
from aunix.reasoning import Reasoner
from aunix.reasoning_llm import LlmReasoner


class Runtime:
    def __init__(self, settings: Settings, reasoner: Reasoner | None = None):
        self.settings = settings
        self.reasoner = reasoner or LlmReasoner(OpenAiLlm(model=settings.llm_model))

    def connectors(self, session: Session) -> dict[str, Connector]:
        Path(self.settings.simship_state_path).parent.mkdir(parents=True, exist_ok=True)
        out: dict[str, Connector] = {"simship": SimShip(Path(self.settings.simship_state_path))}
        csv_conn = session.scalars(
            select(Connection).where(Connection.provider == "csv").order_by(Connection.id.desc())
        ).first()
        if csv_conn:
            out["csv"] = CsvConnector(Path(csv_conn.credentials["path"]))
        if self.settings.hubspot_access_token:
            out["hubspot"] = HubSpotConnector(self.settings.hubspot_access_token)
        return out

    def notifiers(self, session: Session) -> list[Notifier]:
        out: list[Notifier] = [FeedNotifier(session)]
        s = self.settings
        if s.mailgun_api_key and s.mailgun_domain:
            # Mailgun requires the sender to be on the verified domain; fall back
            # to alerts@<domain> when no real AUNIX_EMAIL_FROM is configured.
            sender = s.email_from if s.email_from != "alerts@aunix.local" else f"Aunix Alerts <alerts@{s.mailgun_domain}>"
            out.append(MailgunNotifier(session, s.mailgun_api_key, s.mailgun_domain,
                                       sender, base_url=s.mailgun_base_url))
        elif s.resend_api_key:
            out.append(EmailNotifier(session, s.resend_api_key, s.email_from))
        return out
