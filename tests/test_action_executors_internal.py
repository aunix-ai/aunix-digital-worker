from sqlalchemy import select

from aunix.actions.executors import ResolveActionExecutor, TaskActionExecutor
from aunix.models import Action, Agent, Finding, Run, Task
from aunix.testing import make_spec


def seed(session, finding_state="new"):
    a = Agent(owner="d", spec={}, status="active"); session.add(a); session.flush()
    r = Run(agent_id=a.id, trigger="manual"); session.add(r); session.flush()
    f = Finding(agent_id=a.id, run_id=r.id, dedupe_key="k", summary="s", state=finding_state)
    session.add(f); session.flush()
    return a, r, f


def test_task_executor_creates_task_row(session):
    a, r, f = seed(session)
    act = Action(agent_id=a.id, run_id=r.id, finding_id=f.id, type="task",
                 params={"title": "Chase Globex"}, dedupe_key="k:task", origin="L3")
    session.add(act); session.flush()
    result = TaskActionExecutor().execute(session, act, f, make_spec())
    task = session.scalars(select(Task)).one()
    assert task.title == "Chase Globex"
    assert result["task_id"] == task.id


def test_resolve_executor_marks_finding_resolved(session):
    a, r, f = seed(session, finding_state="new")
    act = Action(agent_id=a.id, run_id=r.id, finding_id=f.id, type="resolve",
                 params={}, dedupe_key="k:resolve", origin="L3")
    session.add(act); session.flush()
    ResolveActionExecutor().execute(session, act, f, make_spec())
    assert f.state == "resolved"
