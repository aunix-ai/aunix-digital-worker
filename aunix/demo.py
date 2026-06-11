"""Seeded end-to-end demo: David's PO monitor and Mark's lead ranker.
Run with: uv run python -m aunix.demo"""
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from aunix.connectors.csv_source import CsvConnector
from aunix.connectors.simship import SimShip
from aunix.models import Agent, Base, Finding, Notification
from aunix.notifier import FeedNotifier
from aunix.reasoning import RuleBasedReasoner
from aunix.runner import execute_run
from aunix.spec import AgentSpec, Condition, ConditionGroup, NotificationRule, Schedule

SALES_CSV = Path(__file__).resolve().parent.parent / "data" / "sample_sales_report.csv"


def run_demo(workdir: Path) -> None:
    now = datetime.now(timezone.utc)
    engine = create_engine(f"sqlite:///{workdir}/demo.db")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    sim = SimShip(workdir / "simship.json")
    sim.slip_delivery("PO-4567", days=2)
    sim.freeze_tracking("PO-4568", hours=50)

    david = Agent(
        owner="david",
        status="active",
        spec=AgentSpec(
            name="po-watcher",
            objective="Watch active POs; alert on delivery slips or 48h tracking silence",
            task_type="monitoring",
            data_sources=["simship"],
            record_key="po_number",
            conditions=ConditionGroup(
                mode="any",
                conditions=[
                    Condition(field="delivery_date", operator="gt", value="expected_date"),
                    Condition(field="last_tracking_update", operator="stale_hours", value=48),
                ],
            ),
            schedule=Schedule(mode="interval", interval_minutes=30),
            notifications=NotificationRule(channels=["feed"]),
        ).model_dump(mode="json"),
    )
    mark = Agent(
        owner="mark",
        status="active",
        spec=AgentSpec(
            name="lead-ranker",
            objective="Rank top 5 leads from the daily sales report",
            task_type="analysis",
            data_sources=["csv"],
            record_key="lead",
            rank_by="deal_size",
            top_n=5,
            schedule=Schedule(mode="daily", daily_time="08:00"),
            notifications=NotificationRule(channels=["feed"]),
        ).model_dump(mode="json"),
    )
    session.add_all([david, mark])
    session.commit()

    connectors = {"simship": sim, "csv": CsvConnector(SALES_CSV)}
    reasoner = RuleBasedReasoner()
    notifiers = [FeedNotifier(session)]

    run1 = execute_run(session, david, connectors, reasoner, notifiers, now=now)
    print(
        f"[po-watcher] run {run1.id}: {run1.status} "
        f"rows={run1.trace['rows_fetched']} new={run1.trace['findings']['new']}"
    )
    run2 = execute_run(session, david, connectors, reasoner, notifiers, now=now)
    print(f"[po-watcher] run {run2.id}: {run2.status} (re-run; ongoing issues stay quiet)")
    run3 = execute_run(session, mark, connectors, reasoner, notifiers, now=now)
    print(
        f"[lead-ranker] run {run3.id}: {run3.status} "
        f"rows={run3.trace['rows_fetched']} new={run3.trace['findings']['new']}"
    )

    print("\n=== Activity feed ===")
    for note in session.scalars(select(Notification)).all():
        finding = session.get(Finding, note.finding_id)
        print(f"- [{note.channel}] {finding.summary} -> {finding.recommendation}")


def main() -> None:
    run_demo(workdir=Path(tempfile.mkdtemp(prefix="aunix-demo-")))


if __name__ == "__main__":
    main()
