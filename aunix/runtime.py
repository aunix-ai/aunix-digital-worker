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
from aunix.llm import AnthropicLlm
from aunix.models import Connection
from aunix.notifier import FeedNotifier, Notifier
from aunix.notifier_email import EmailNotifier
from aunix.reasoning import Reasoner
from aunix.reasoning_llm import LlmReasoner


class Runtime:
    def __init__(self, settings: Settings, reasoner: Reasoner | None = None):
        self.settings = settings
        self.reasoner = reasoner or LlmReasoner(AnthropicLlm(model=settings.llm_model))

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
        if self.settings.resend_api_key:
            out.append(EmailNotifier(session, self.settings.resend_api_key, self.settings.email_from))
        return out
