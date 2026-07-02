# aunix/runtime.py
"""Assembles connectors/reasoner/notifiers from settings + DB state. Shared by
the API process (run-now) and the worker process (scheduled runs)."""
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from aunix.actions.executors import (
    EmailActionExecutor,
    HubSpotActionExecutor,
    ResolveActionExecutor,
    TaskActionExecutor,
)
from aunix.actions.planner import LlmActionPlanner
from aunix.composio.client import get_composio_user_id
from aunix.composio.connector import ComposioConnector
from aunix.composio.executor import ComposioActionExecutor
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
from aunix.spec import AgentSpec, iter_composio_sources


class Runtime:
    def __init__(self, settings: Settings, reasoner: Reasoner | None = None):
        self.settings = settings
        self.reasoner = reasoner or LlmReasoner(OpenAiLlm(model=settings.llm_model))
        self.action_planner = LlmActionPlanner(OpenAiLlm(model=settings.llm_model))

    def executors(self, session: Session, *, owner: str | None = None) -> dict:
        from aunix.actions.executors import ActionExecutor
        out: dict[str, ActionExecutor] = {
            "task": TaskActionExecutor(),
            "resolve": ResolveActionExecutor(),
        }
        s = self.settings
        if s.mailgun_api_key and s.mailgun_domain:
            sender = s.email_from if s.email_from != "alerts@aunix.local" else f"Aunix Alerts <alerts@{s.mailgun_domain}>"
            out["email"] = EmailActionExecutor(s.mailgun_api_key, s.mailgun_domain, sender,
                                               base_url=s.mailgun_base_url)
        if s.hubspot_access_token:
            out["hubspot"] = HubSpotActionExecutor(s.hubspot_access_token)
        if s.composio_api_key:
            out["composio"] = ComposioActionExecutor(user_id=get_composio_user_id(owner))
        return out

    def connectors(self, session: Session, spec: AgentSpec | None = None, *, owner: str | None = None) -> dict[str, Connector]:
        Path(self.settings.simship_state_path).parent.mkdir(parents=True, exist_ok=True)
        out: dict[str, Connector] = {"simship": SimShip(Path(self.settings.simship_state_path))}
        csv_conn = session.scalars(
            select(Connection).where(Connection.provider == "csv").order_by(Connection.id.desc())
        ).first()
        if csv_conn:
            out["csv"] = CsvConnector(Path(csv_conn.credentials["path"]))
        if self.settings.hubspot_access_token:
            out["hubspot"] = HubSpotConnector(self.settings.hubspot_access_token)
        if self.settings.composio_api_key and spec is not None:
            uid = get_composio_user_id(owner)
            for source in iter_composio_sources(spec):
                out[source.source_id()] = ComposioConnector(source, user_id=uid)
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
