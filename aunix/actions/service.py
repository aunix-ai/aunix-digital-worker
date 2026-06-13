"""Action lifecycle service. propose_actions runs the planner, dedupes against the
actions table, and queues pending rows (the L3 gate). execute_action / expire_actions
(Task 9) handle approval and expiry. L4 policy auto-approval is layered on later."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from aunix.actions.executors import ActionExecutor
from aunix.actions.planner import ActionPlanner
from aunix.models import Action, Finding
from aunix.spec import AgentSpec


def propose_actions(session: Session, spec: AgentSpec, finding: Finding, run_id: int,
                    planner: ActionPlanner, *, now: datetime, ttl_hours: int) -> list[Action]:
    existing = set(session.scalars(
        select(Action.dedupe_key).where(Action.agent_id == finding.agent_id)
    ).all())
    created: list[Action] = []
    for proposed in planner.plan(spec, finding):
        if proposed.dedupe_key in existing:
            continue
        existing.add(proposed.dedupe_key)
        action = Action(
            agent_id=finding.agent_id, run_id=run_id, finding_id=finding.id,
            type=proposed.type, params=proposed.params, dedupe_key=proposed.dedupe_key,
            origin="L3", status="pending", expires_at=now + timedelta(hours=ttl_hours),
        )
        session.add(action)
        created.append(action)
    session.flush()
    return created


class ActionStateError(Exception):
    pass


def _spec_for(session: Session, action: Action) -> AgentSpec:
    from aunix.models import Agent
    return AgentSpec.model_validate(session.get(Agent, action.agent_id).spec)


def execute_action(session: Session, action: Action, executors: dict[str, ActionExecutor],
                   *, now: datetime, decided_by: str) -> Action:
    if action.status != "pending":
        raise ActionStateError(f"action {action.id} is {action.status}, not pending")
    expires_at = action.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)  # SQLite strips tz; treat as UTC
    if expires_at is not None and expires_at <= now:
        action.status = "expired"
        session.flush()
        raise ActionStateError(f"action {action.id} has expired")
    finding = session.get(Finding, action.finding_id)
    spec = _spec_for(session, action)
    action.status = "approved"
    action.decided_at = now
    action.decided_by = decided_by
    try:
        action.result = executors[action.type].execute(session, action, finding, spec)
        action.status = "executed"
        action.executed_at = now
    except Exception as exc:  # best-effort: record, never raise
        action.error = str(exc)
        action.status = "failed"
    session.flush()
    return action


def expire_actions(session: Session, *, now: datetime) -> int:
    stale = session.scalars(
        select(Action).where(Action.status == "pending", Action.expires_at <= now)
    ).all()
    for action in stale:
        action.status = "expired"
    session.flush()
    return len(stale)
