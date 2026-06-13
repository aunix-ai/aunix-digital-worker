"""Action executors. One per action type, registered by `type` and dispatched on
`action.type` (mirrors connectors/notifiers). Each performs a side effect and
returns a JSON-able result dict, or raises; the caller records executed/failed."""
from typing import Protocol

import httpx
from sqlalchemy.orm import Session

from aunix.models import Action, Finding, Task
from aunix.spec import AgentSpec


class ActionExecutor(Protocol):
    type: str
    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict: ...


class TaskActionExecutor:
    type = "task"

    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict:
        task = Task(agent_id=action.agent_id, finding_id=finding.id,
                    title=action.params.get("title", finding.summary))
        session.add(task)
        session.flush()
        return {"task_id": task.id}


class ResolveActionExecutor:
    type = "resolve"

    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict:
        finding.state = "resolved"
        session.flush()
        return {"resolved_finding_id": finding.id}


class EmailActionExecutor:
    """Sends the drafted email to a third-party recipient via Mailgun. Distinct from
    the alert-to-self notifier: the recipient comes from the action params."""

    type = "email"

    def __init__(self, api_key: str, domain: str, default_from: str,
                 base_url: str = "https://api.mailgun.net", client: httpx.Client | None = None):
        self.domain = domain
        self.default_from = default_from
        self._auth = ("api", api_key)
        self.client = client or httpx.Client(base_url=base_url, timeout=30)

    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict:
        to = action.params.get("to")
        if not to:
            raise ValueError("email action has no recipient")
        resp = self.client.post(
            f"/v3/{self.domain}/messages", auth=self._auth,
            data={"from": action.params.get("from", self.default_from), "to": to,
                  "subject": action.params.get("subject", f"[Aunix] {finding.summary}"),
                  "text": action.params.get("body", finding.summary)},
        )
        resp.raise_for_status()
        return {"message_id": resp.json().get("id")}
