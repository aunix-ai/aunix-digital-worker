"""Action lifecycle service. propose_actions runs the planner, dedupes against the
actions table, and queues pending rows (the L3 gate). execute_action / expire_actions
(Task 9) handle approval and expiry. L4 policy auto-approval is layered on later."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

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
