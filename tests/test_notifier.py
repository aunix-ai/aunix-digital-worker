from sqlalchemy import select

from aunix.models import Agent, Finding, Notification, Run
from aunix.notifier import FeedNotifier
from aunix.testing import make_spec


def test_feed_notifier_records_sent_notification(session):
    agent = Agent(owner="david", spec={}, status="active")
    session.add(agent)
    session.flush()
    run = Run(agent_id=agent.id, trigger="manual")
    session.add(run)
    session.flush()
    finding = Finding(agent_id=agent.id, run_id=run.id, dedupe_key="k", summary="s")
    session.add(finding)
    session.flush()

    FeedNotifier(session).send(finding, make_spec())

    note = session.scalars(select(Notification)).one()
    assert note.finding_id == finding.id
    assert note.channel == "feed"
    assert note.status == "sent"
