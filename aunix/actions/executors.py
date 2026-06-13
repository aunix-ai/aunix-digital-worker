"""Action executors. One per action type, registered by `type` and dispatched on
`action.type` (mirrors connectors/notifiers). Each performs a side effect and
returns a JSON-able result dict, or raises; the caller records executed/failed."""
from typing import Protocol

import httpx
from sqlalchemy.orm import Session

from aunix.models import Action, Finding, Task
from aunix.spec import AgentSpec


class ActionExecutor(Protocol):
    type: str
    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict: ...


class TaskActionExecutor:
    type = "task"

    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict:
        task = Task(agent_id=action.agent_id, finding_id=finding.id,
                    title=action.params.get("title", finding.summary))
        session.add(task)
        session.flush()
        return {"task_id": task.id}


class ResolveActionExecutor:
    type = "resolve"

    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict:
        finding.state = "resolved"
        session.flush()
        return {"resolved_finding_id": finding.id}
