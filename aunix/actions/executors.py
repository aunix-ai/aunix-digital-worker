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


class HubSpotActionExecutor:
    """Writes back to HubSpot. `add_note` creates a note associated to the deal;
    `set_property` patches a deal property. Needs the crm.objects.deals.write scope."""

    type = "hubspot"

    def __init__(self, access_token: str, client: httpx.Client | None = None):
        self.client = client or httpx.Client(
            base_url="https://api.hubapi.com",
            headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
        self._auth_header = f"Bearer {access_token}"

    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict:
        op = action.params.get("op", "add_note")
        deal_id = str(action.params.get("deal_id") or "")
        if op == "add_note":
            resp = self.client.post(
                "/crm/v3/objects/notes",
                headers={"Authorization": self._auth_header},
                json={
                    "properties": {"hs_note_body": action.params.get("note", finding.summary)},
                    "associations": [{
                        "to": {"id": deal_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}],
                    }] if deal_id else [],
                },
            )
            resp.raise_for_status()
            return {"note_id": resp.json().get("id")}
        if op == "set_property":
            resp = self.client.patch(
                f"/crm/v3/objects/deals/{deal_id}",
                headers={"Authorization": self._auth_header},
                json={"properties": action.params.get("properties", {})},
            )
            resp.raise_for_status()
            return {"deal_id": deal_id, "updated": True}
        raise ValueError(f"unsupported hubspot op: {op!r}")
