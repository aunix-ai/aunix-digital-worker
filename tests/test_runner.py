from datetime import datetime, timezone

from sqlalchemy import select

from aunix.connectors.simship import SimShip
from aunix.models import Agent, Finding, Notification
from aunix.notifier import FeedNotifier
from aunix.reasoning import RuleBasedReasoner
from aunix.runner import execute_run
from aunix.testing import make_spec

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def make_agent(session, **spec_overrides):
    agent = Agent(
        owner="test",
        status="active",
        spec=make_spec(**spec_overrides).model_dump(mode="json"),
    )
    session.add(agent)
    session.commit()
    return agent


def run_once(session, agent, connectors):
    return execute_run(
        session,
        agent,
        connectors,
        RuleBasedReasoner(),
        [FeedNotifier(session)],
        now=NOW,
    )


def notification_count(session):
    return len(session.scalars(select(Notification)).all())


def test_monitoring_run_alerts_on_breach(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW)
    sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session)

    run = run_once(session, agent, {"simship": sim})

    assert run.status == "succeeded"
    assert run.trace["rows_fetched"] == 3
    assert run.trace["breaches"] == ["PO-4567"]
    assert notification_count(session) == 1


def test_second_run_does_not_realert(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW)
    sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session)

    run_once(session, agent, {"simship": sim})
    run2 = run_once(session, agent, {"simship": sim})

    assert run2.status == "succeeded"
    assert run2.trace["findings"]["ongoing"] == 1
    assert notification_count(session) == 1  # still just the first alert


def test_failed_connector_records_failed_run(session):
    class Boom:
        source_id = "simship"

        def fetch(self):
            raise RuntimeError("api down")

    agent = make_agent(session)
    run = run_once(session, agent, {"simship": Boom()})

    assert run.status == "failed"
    assert "api down" in run.error
    assert notification_count(session) == 0


def test_analysis_run_briefs_every_run(session, tmp_path):
    csv = tmp_path / "leads.csv"
    csv.write_text("lead,deal_size\nA,100\nB,300\nC,200\n")
    from aunix.connectors.csv_source import CsvConnector

    agent = make_agent(
        session,
        task_type="analysis",
        conditions=None,
        data_sources=["csv"],
        record_key="lead",
        rank_by="deal_size",
        top_n=2,
    )
    connectors = {"csv": CsvConnector(csv)}

    run_once(session, agent, connectors)
    assert notification_count(session) == 2
    run_once(session, agent, connectors)
    assert notification_count(session) == 4  # briefing repeats every run by design


class BoomNotifier:
    channel = "feed"

    def send(self, finding, spec):
        raise RuntimeError("smtp down")


def test_notifier_failure_does_not_persist_phantom_findings(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW)
    sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session)

    run = execute_run(
        session, agent, {"simship": sim}, RuleBasedReasoner(), [BoomNotifier()], now=NOW
    )

    assert run.status == "failed"
    assert "smtp down" in run.error
    assert session.scalars(select(Finding)).all() == []  # no phantom finding

    # the breach must still alert once the notifier recovers
    run2 = run_once(session, agent, {"simship": sim})
    assert run2.status == "succeeded"
    assert notification_count(session) == 1


def test_notifiers_filtered_by_spec_channels(session, tmp_path):
    class WrongChannel:
        channel = "email"

        def send(self, finding, spec):
            raise AssertionError("must not be called: email not in spec channels")

    sim = SimShip(tmp_path / "s.json", now=lambda: NOW)
    sim.slip_delivery("PO-4567", days=2)
    agent = make_agent(session)  # spec channels = ["feed"]

    run = execute_run(
        session,
        agent,
        {"simship": sim},
        RuleBasedReasoner(),
        [FeedNotifier(session), WrongChannel()],
        now=NOW,
    )

    assert run.status == "succeeded"
    assert notification_count(session) == 1


def test_missing_connector_records_clear_error(session):
    agent = make_agent(session)
    run = run_once(session, agent, {})  # no connectors at all
    assert run.status == "failed"
    assert "no connector configured for data source 'simship'" in run.error


def test_misregistered_connector_fails_loudly(session, tmp_path):
    sim = SimShip(tmp_path / "s.json", now=lambda: NOW)  # source_id is "simship"
    agent = make_agent(session, data_sources=["wrong-name"])

    run = run_once(session, agent, {"wrong-name": sim})

    assert run.status == "failed"
    assert "source_id" in run.error
