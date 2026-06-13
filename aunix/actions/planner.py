"""Action planner seam. RuleBasedActionPlanner is the deterministic offline
implementation; LlmActionPlanner (Task 4) implements the same protocol with the
LLM. A planner only ever proposes the action types the spec granted."""
import json
import logging
from typing import Protocol

from pydantic import BaseModel

from aunix.llm import LlmClient
from aunix.models import Finding
from aunix.spec import ActionPermission, AgentSpec

logger = logging.getLogger(__name__)


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


SYSTEM = """You draft concrete actions an operations agent will take in response to a \
finding. You are given the finding and the list of permitted action types. For each \
permitted type, draft one action with realistic, specific content:
- email: a professional `subject` and `body` to the relevant party (and `to` if you can \
infer the address from the finding data).
- hubspot: a concise `note` (<= 300 chars) plus the `op` and `deal_id`.
- task: a one-line `title`.
- resolve: no params.
Only draft the permitted types. Keep content grounded in the finding's data."""


class DraftedActions(BaseModel):
    actions: list[ProposedAction]


class LlmActionPlanner:
    def __init__(self, llm: LlmClient, fallback: ActionPlanner | None = None):
        self.llm = llm
        self.fallback = fallback or RuleBasedActionPlanner()

    def plan(self, spec: AgentSpec, finding: Finding) -> list[ProposedAction]:
        base = self.fallback.plan(spec, finding)  # deterministic skeleton (types, keys, fallbacks)
        try:
            drafted = self.llm.parse(system=SYSTEM, prompt=self._prompt(spec, finding),
                                     schema=DraftedActions)
        except Exception:
            logger.exception("LLM action planning failed; using rule-based drafts")
            return base
        by_type = {d.type: d for d in drafted.actions}
        # keep the deterministic type set + keys; overlay LLM content where provided
        for action in base:
            d = by_type.get(action.type)
            if d:
                merged = {**action.params, **d.params}
                action.params = merged
        return base

    def _prompt(self, spec: AgentSpec, finding: Finding) -> str:
        permitted = [p.type for p in spec.actions]
        return json.dumps({
            "objective": spec.objective,
            "permitted_action_types": permitted,
            "finding": {"summary": finding.summary, "recommendation": finding.recommendation,
                        "source_ref": finding.source_ref, "severity": finding.severity,
                        "data": _row(finding)},
        }, indent=2)
