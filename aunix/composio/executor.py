"""Execute Composio write tools for L3/L4 actions."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from aunix.composio.operations import execute_tool
from aunix.models import Action, Finding
from aunix.spec import AgentSpec


_PLACEHOLDER = re.compile(r"\{\{finding\.([a-zA-Z0-9_]+)\}\}")


def _interpolate_value(value: Any, finding: Finding) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            if key == "summary":
                return finding.summary or ""
            if key == "recommendation":
                return finding.recommendation or ""
            if key == "source_ref":
                return finding.source_ref or ""
            details = finding.details if isinstance(finding.details, dict) else {}
            row = details.get("row") if isinstance(details.get("row"), dict) else {}
            if key in row:
                return str(row.get(key) or "")
            return ""
        return _PLACEHOLDER.sub(repl, value)
    if isinstance(value, dict):
        return {k: _interpolate_value(v, finding) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_value(v, finding) for v in value]
    return value


class ComposioActionExecutor:
    type = "composio"

    def __init__(self, *, user_id: str | None = None):
        self.user_id = user_id

    def execute(self, session: Session, action: Action, finding: Finding, spec: AgentSpec) -> dict:
        tool_slug = str(action.params.get("tool_slug") or "")
        if not tool_slug:
            raise ValueError("composio action missing tool_slug")
        template = action.params.get("arguments")
        if not isinstance(template, dict):
            template = {k: v for k, v in action.params.items() if k not in {"tool_slug", "arguments"}}
        arguments = _interpolate_value(template, finding)
        result = execute_tool(tool_slug, arguments, user_id=self.user_id)
        return {"tool_slug": tool_slug, "result": result}
