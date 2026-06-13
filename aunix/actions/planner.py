"""Action planner seam. RuleBasedActionPlanner is the deterministic offline
implementation; LlmActionPlanner (Task 4) implements the same protocol with the
LLM. A planner only ever proposes the action types the spec granted."""
from typing import Protocol

from pydantic import BaseModel

from aunix.models import Finding
from aunix.spec import ActionPermission, AgentSpec


class ProposedAction(BaseModel):
    type: str
    params: dict = {}
    dedupe_key: str


class ActionPlanner(Protocol):
    def plan(self, spec: AgentSpec, finding: Finding) -> list[ProposedAction]: ...


def _row(finding: Finding) -> dict:
    return (finding.details or {}).get("row", {}) if isinstance(finding.details, dict) else {}


def _email_recipient(perm: ActionPermission, finding: Finding) -> str | None:
    if perm.to:
        return perm.to
    if perm.to_field:
        return _row(finding).get(perm.to_field)
    return None


class RuleBasedActionPlanner:
    def plan(self, spec: AgentSpec, finding: Finding) -> list[ProposedAction]:
        out: list[ProposedAction] = []
        for perm in spec.actions:
            key = f"{finding.dedupe_key}:{perm.type}"
            if perm.type == "email":
                params: dict = {
                    "subject": f"[{finding.source_ref}] {finding.summary}",
                    "body": f"{finding.summary}\n\nRecommended: {finding.recommendation}",
                }
                rcpt = _email_recipient(perm, finding)
                if rcpt:
                    params["to"] = rcpt
            elif perm.type == "hubspot":
                op = perm.ops[0] if perm.ops else "add_note"
                params = {"op": op, "note": f"Aunix: {finding.summary}",
                          "deal_id": _row(finding).get("hubspot_id")}
            elif perm.type == "task":
                params = {"title": f"Follow up: {finding.summary}"}
            else:  # resolve
                params = {}
            out.append(ProposedAction(type=perm.type, params=params, dedupe_key=key))
        return out
