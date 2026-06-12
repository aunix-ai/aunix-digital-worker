# aunix/worker.py
"""Scheduler worker: maps each active agent's schedule onto APScheduler and
executes runs with per-slot idempotency (a worker restart cannot double-run a
slot). Run with: uv run python -m aunix.worker"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from aunix.config import Settings
from aunix.db import make_engine, make_session_factory
from aunix.models import Agent, Base, Run
from aunix.runner import execute_run
from aunix.runtime import Runtime
from aunix.spec import AgentSpec

logger = logging.getLogger(__name__)


def slot_key_for(agent_id: int, spec: AgentSpec, now: datetime) -> str:
    if spec.schedule.mode == "interval":
        bucket = int(now.timestamp() // (spec.schedule.interval_minutes * 60))
        return f"{agent_id}:interval:{bucket}"
    return f"{agent_id}:daily:{now.date().isoformat()}"


def run_agent_once(session_factory, agent_id: int, runtime, *,
                   trigger: str, now: datetime | None = None) -> Run | None:
    now = now or datetime.now(timezone.utc)
    with session_factory() as session:
        agent = session.get(Agent, agent_id)
        if agent is None or agent.status != "active":
            return None
        spec = AgentSpec.model_validate(agent.spec)
        key = slot_key_for(agent_id, spec, now) if trigger != "manual" else None
        if key and session.scalars(select(Run).where(Run.slot_key == key)).first():
            return None  # slot already ran (idempotent across restarts)
        run = execute_run(
            session, agent, runtime.connectors(session), runtime.reasoner,
            runtime.notifiers(session), trigger=trigger, now=now,
            slot_key=key,
        )
        return run


def schedule_agents(scheduler, session_factory, runtime: Runtime) -> None:
    """(Re)register one job per active agent; called at startup and every minute
    so newly activated agents get picked up without a restart."""
    with session_factory() as session:
        agents = session.scalars(select(Agent).where(Agent.status == "active")).all()
        specs = [(a.id, AgentSpec.model_validate(a.spec)) for a in agents]
    for agent_id, spec in specs:
        if spec.schedule.mode == "interval":
            trig, trigger_name = IntervalTrigger(minutes=spec.schedule.interval_minutes), "interval"
        elif spec.schedule.mode == "daily":
            hour, minute = (int(p) for p in spec.schedule.daily_time.split(":"))
            trig, trigger_name = CronTrigger(hour=hour, minute=minute), "daily"
        else:
            continue  # on_demand agents run only via the API
        scheduler.add_job(
            run_agent_once, trig,
            args=[session_factory, agent_id, runtime], kwargs={"trigger": trigger_name},
            id=f"agent-{agent_id}", replace_existing=True,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    runtime = Runtime(settings)
    scheduler = BlockingScheduler()
    schedule_agents(scheduler, session_factory, runtime)
    scheduler.add_job(schedule_agents, IntervalTrigger(minutes=1),
                      args=[scheduler, session_factory, runtime], id="rescan")
    logger.info("worker started")
    scheduler.start()


if __name__ == "__main__":
    main()
