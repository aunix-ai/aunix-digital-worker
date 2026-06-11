"""Finding state machine: diff current breaches against open findings so the
platform monitors (alert once, track, auto-resolve) instead of spamming."""
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from aunix.models import Finding


class CandidateFinding(BaseModel):
    dedupe_key: str
    severity: str = "info"
    summary: str
    recommendation: str = ""
    source_ref: str = ""
    details: dict = {}


@dataclass
class ReconcileResult:
    new: list[Finding] = field(default_factory=list)
    ongoing: list[Finding] = field(default_factory=list)
    resolved: list[Finding] = field(default_factory=list)


def reconcile(
    session: Session,
    agent_id: int,
    run_id: int,
    current: list[CandidateFinding],
    *,
    now: datetime,
) -> ReconcileResult:
    open_findings = session.scalars(
        select(Finding).where(
            Finding.agent_id == agent_id,
            Finding.state.in_(["new", "ongoing"]),
        )
    ).all()
    open_by_key = {f.dedupe_key: f for f in open_findings}

    result = ReconcileResult()
    seen_keys: set[str] = set()
    for cand in current:
        if cand.dedupe_key in seen_keys:
            continue  # same breach reported twice in one run — first occurrence wins
        seen_keys.add(cand.dedupe_key)
        existing = open_by_key.get(cand.dedupe_key)
        if existing:
            existing.state = "ongoing"
            existing.last_seen_at = now
            existing.summary = cand.summary
            result.ongoing.append(existing)
        else:
            f = Finding(
                agent_id=agent_id,
                run_id=run_id,
                dedupe_key=cand.dedupe_key,
                severity=cand.severity,
                summary=cand.summary,
                recommendation=cand.recommendation,
                source_ref=cand.source_ref,
                details=cand.details,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(f)
            result.new.append(f)

    for key, f in open_by_key.items():
        if key not in seen_keys:
            f.state = "resolved"
            result.resolved.append(f)

    session.flush()
    return result
