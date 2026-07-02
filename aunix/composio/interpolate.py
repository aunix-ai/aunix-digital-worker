"""Resolve {{now_iso}} and {{now_minus_N_days_iso}} placeholders in Composio tool arguments."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

_NOW_ISO = re.compile(r"\{\{now_iso\}\}")
_NOW_MINUS_DAYS = re.compile(r"\{\{now_minus_(\d+)_days_iso\}\}")


def interpolate_runtime_arguments(
    arguments: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Replace time placeholders in Composio fetch arguments before execute."""
    now = now or datetime.now(timezone.utc)

    def fmt(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def resolve(value: Any) -> Any:
        if isinstance(value, str):
            def repl_days(match: re.Match[str]) -> str:
                days = int(match.group(1))
                return fmt(now - timedelta(days=days))

            text = _NOW_MINUS_DAYS.sub(repl_days, value)
            text = _NOW_ISO.sub(fmt(now), text)
            return text
        if isinstance(value, dict):
            return {k: resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve(v) for v in value]
        return value

    return resolve(dict(arguments))
