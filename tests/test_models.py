from aunix.models import Agent, Finding, Run


def test_agent_run_finding_round_trip(session):
    agent = Agent(owner="david", spec={"name": "po-watcher"}, status="active")
    session.add(agent)
    session.flush()

    run = Run(agent_id=agent.id, trigger="manual", trace={"rows_fetched": 3})
    session.add(run)
    session.flush()

    finding = Finding(
        agent_id=agent.id,
        run_id=run.id,
        dedupe_key="PO-4567:delivery_date",
        summary="PO-4567 delayed",
    )
    session.add(finding)
    session.commit()

    assert session.get(Finding, finding.id).state == "new"
    assert session.get(Run, run.id).trace == {"rows_fetched": 3}
