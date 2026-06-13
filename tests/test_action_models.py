from aunix.models import Action, Agent, Finding, Run, Task


def test_action_round_trip(session):
    agent = Agent(owner="d", spec={}, status="active"); session.add(agent); session.flush()
    run = Run(agent_id=agent.id, trigger="manual"); session.add(run); session.flush()
    f = Finding(agent_id=agent.id, run_id=run.id, dedupe_key="PO-1:delivery_date", summary="s")
    session.add(f); session.flush()
    a = Action(agent_id=agent.id, run_id=run.id, finding_id=f.id, type="email",
               params={"to": "x@y.com"}, dedupe_key="PO-1:delivery_date:email", origin="L3")
    session.add(a); session.commit()
    got = session.get(Action, a.id)
    assert got.status == "pending"            # default
    assert got.params == {"to": "x@y.com"}
    assert got.origin == "L3"


def test_task_round_trip(session):
    agent = Agent(owner="d", spec={}, status="active"); session.add(agent); session.flush()
    f = Finding(agent_id=agent.id, run_id=1, dedupe_key="k", summary="s"); session.add(f); session.flush()
    t = Task(agent_id=agent.id, finding_id=f.id, title="Chase Globex")
    session.add(t); session.commit()
    assert session.get(Task, t.id).done is False
