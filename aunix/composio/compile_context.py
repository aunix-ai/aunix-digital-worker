"""Compile-time Composio context for the agent compiler."""
from __future__ import annotations

import json
from typing import Any

from aunix.composio.operations import list_toolkit_connections, search_tools


def build_compile_context(text: str, *, user_id: str | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {"connections": list_toolkit_connections(user_id)}
    try:
        context["tool_search"] = search_tools(text, user_id=user_id)
    except Exception as exc:  # pragma: no cover - best effort enrichment
        context["tool_search_error"] = str(exc)
    return context


def format_compile_context(context: dict[str, Any]) -> str:
    return json.dumps(context, indent=2, default=str)
