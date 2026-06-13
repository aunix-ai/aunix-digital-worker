"""Action lifecycle service. propose_actions runs the planner, dedupes against the
actions table, then gates each proposal: L3 (or no policy) queues every action as
`pending`; L4 auto-executes policy-whitelisted, in-bounds actions inline (within
caps) and queues the rest. execute_action / expire_actions handle approval/expiry."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aunix.actions.executors import ActionExecutor
from aunix.actions.gate import gate
from aunix.actions.planner import ActionPlanner
from aunix.models import Action, Finding
from aunix.spec import AgentSpec


def propose_actions(session: Session, spec: AgentSpec, finding: Finding, run_id: int,
                    planner: ActionPlanner, *, now: datetime, ttl_hours: int,
                    executors: dict[str, ActionExecutor] | None = None) -> list[Action]:
    existing = set(session.scalars(
        select(Action.dedupe_key).where(Action.agent_id == finding.agent_id)
    ).all())
    is_l4 = spec.autonomy_level == 4 and spec.policy is not None
    origin = "L4" if is_l4 else "L3"

    run_auto = 0  # auto-approvals consumed in this run, for the per_run cap
    day_auto = 0  # auto-approvals in the rolling 24h window, for the per_day cap
    if is_l4:
        day_auto = session.scalar(
            select(func.count()).select_from(Action).where(
                Action.agent_id == finding.agent_id,
                Action.policy_decision == "auto",
                Action.created_at >= now - timedelta(hours=24),
            )
        ) or 0

    created: list[Action] = []
    for proposed in planner.plan(spec, finding):
        if proposed.dedupe_key in existing:
            continue
        existing.add(proposed.dedupe_key)
        decision = gate(spec, proposed, run_auto_count=run_auto, day_auto_count=day_auto) if is_l4 else "queued"
        action = Action(
            agent_id=finding.agent_id, run_id=run_id, finding_id=finding.id,
            type=proposed.type, params=proposed.params, dedupe_key=proposed.dedupe_key,
            origin=origin, status="pending", policy_decision=(decision if is_l4 else None),
            created_at=now, expires_at=now + timedelta(hours=ttl_hours),
        )
        session.add(action)
        session.flush()
        if decision == "auto":
            run_auto += 1
            day_auto += 1
            if executors is not None:  # auto-execute inline; records executed/failed
                execute_action(session, action, executors, now=now, decided_by="policy")
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
    if action.type not in executors:
        action.status = "failed"
        action.error = f"no executor configured for action type {action.type!r}"
        session.flush()
        return action
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
