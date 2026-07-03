"""Deterministic condition evaluation over fetched data rows."""
from datetime import datetime, timedelta

from pydantic import BaseModel

from aunix.spec import Condition, ConditionGroup


class Breach(BaseModel):
    matched: list[Condition]


_OPS = {
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}


def _resolve_row_field(row: dict, field: str) -> str | None:
    """Match condition field to row keys (exact, case-insensitive, underscore-insensitive)."""
    if field in row:
        return field
    lower = field.lower()
    compact = lower.replace("_", "")
    for key in row:
        if key.lower() == lower:
            return key
        if key.lower().replace("_", "") == compact:
            return key
    return None


def _matches(cond: Condition, row: dict, now: datetime) -> bool:
    field = _resolve_row_field(row, cond.field)
    if field is None:
        return False
    actual = row[field]
    try:
        if cond.operator == "stale_hours":
            return now - actual > timedelta(hours=float(cond.value))
        expected = cond.value
        # a string value naming another column means field-to-field comparison,
        # only for ordering operators — eq/ne always compare against the literal
        if (
            isinstance(expected, str)
            and cond.operator in ("gt", "lt", "gte", "lte")
            and expected in row
        ):
            expected = row[expected]
        return _OPS[cond.operator](actual, expected)
    except TypeError:
        return False


def evaluate(group: ConditionGroup, row: dict, *, now: datetime) -> Breach | None:
    matched = [c for c in group.conditions if _matches(c, row, now)]
    if group.mode == "any" and matched:
        return Breach(matched=matched)
    if group.mode == "all" and len(matched) == len(group.conditions):
        return Breach(matched=matched)
    return None
