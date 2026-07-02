"""Composio-backed data source connector."""
from __future__ import annotations

from typing import Any

from aunix.composio.interpolate import interpolate_runtime_arguments
from aunix.composio.normalize import normalize_rows
from aunix.composio.operations import execute_tool
from aunix.spec import ComposioSource


class ComposioConnector:
    def __init__(self, source: ComposioSource, *, user_id: str | None = None, now=None):
        self.source = source
        self.user_id = user_id
        self.now = now
        self.source_id = source.source_id()

    def fetch(self) -> list[dict]:
        arguments = interpolate_runtime_arguments(dict(self.source.arguments), now=self.now)
        result = execute_tool(
            self.source.tool_slug,
            arguments,
            user_id=self.user_id,
        )
        return normalize_rows(result, self.source.row_mapping or None)
