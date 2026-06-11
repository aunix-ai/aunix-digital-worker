"""The agent run loop: fetch -> evaluate conditions -> reason -> reconcile ->
notify. Every run persists a structured trace (explainability) and a failed
run records its error instead of dying silently."""
from datetime import datetime

from sqlalchemy.orm import Session

from aunix.conditions import Breach, evaluate
from aunix.connectors.base import Connector
from aunix.findings import CandidateFinding, reconcile
from aunix.models import Agent, Finding, Run
from aunix.notifier import Notifier
from aunix.reasoning import Reasoner
from aunix.spec import AgentSpec


def execute_run(
    session: Session,
    agent: Agent,
    connectors: dict[str, Connector],
    reasoner: Reasoner,
    notifiers: list[Notifier],
    *,
    trigger: str = "manual",
    now: datetime,
) -> Run:
    """Execute one agent run and return the persisted Run record.

    Commits the session on success or failure; the caller owns the session
    lifecycle but must not commit or rollback after this returns.
    """
    run = Run(agent_id=agent.id, trigger=trigger, started_at=now)
    session.add(run)
    session.flush()
    run_id = run.id

    spec = AgentSpec.model_validate(agent.spec)
    trace: dict = {}
    try:
        rows: list[dict] = []
        for source in spec.data_sources:
            if source not in connectors:
                raise RuntimeError(f"no connector configured for data source {source!r}")
            rows.extend(connectors[source].fetch())
        trace["rows_fetched"] = len(rows)

        breaches: list[tuple[dict, Breach]] = []
        if spec.conditions:
            for row in rows:
                breach = evaluate(spec.conditions, row, now=now)
                if breach:
                    breaches.append((row, breach))
        trace["breaches"] = [str(row.get(spec.record_key)) for row, _ in breaches]

        insight = reasoner.reason(spec, rows, breaches)

        if spec.task_type == "monitoring":
            result = reconcile(session, agent.id, run.id, insight.findings, now=now)
            to_notify = result.new
            trace["findings"] = {
                "new": len(result.new),
                "ongoing": len(result.ongoing),
                "resolved": len(result.resolved),
            }
        else:
            to_notify = _persist_analysis_findings(session, agent.id, run.id, insight.findings, now)
            trace["findings"] = {"new": len(to_notify), "ongoing": 0, "resolved": 0}

        active = [n for n in notifiers if n.channel in spec.notifications.channels]
        for finding in to_notify:
            for notifier in active:
                notifier.send(finding, spec)

        run.status = "succeeded"
        run.trace = trace
        run.finished_at = now
        session.commit()
    except Exception as exc:
        # discard any half-applied findings/notifications, then record the
        # failed run on a clean session
        session.rollback()
        run = session.get(Run, run_id)
        if run is None:  # the Run insert itself was rolled back
            run = Run(id=run_id, agent_id=agent.id, trigger=trigger, started_at=now)
            session.add(run)
        run.status = "failed"
        run.error = str(exc)
        run.trace = trace
        run.finished_at = now
        session.commit()
    return run


def _persist_analysis_findings(
    session: Session,
    agent_id: int,
    run_id: int,
    candidates: list[CandidateFinding],
    now: datetime,
) -> list[Finding]:
    """Analysis briefings repeat every run, so findings are run-scoped rather
    than reconciled against prior runs."""
    findings = []
    for cand in candidates:
        f = Finding(
            agent_id=agent_id,
            run_id=run_id,
            dedupe_key=f"run-{run_id}:{cand.dedupe_key}",
            severity=cand.severity,
            summary=cand.summary,
            recommendation=cand.recommendation,
            source_ref=cand.source_ref,
            details=cand.details,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(f)
        findings.append(f)
    session.flush()
    return findings
