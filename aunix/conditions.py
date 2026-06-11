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


def _matches(cond: Condition, row: dict, now: datetime) -> bool:
    if cond.field not in row:
        return False
    actual = row[cond.field]
    if cond.operator == "stale_hours":
        return now - actual > timedelta(hours=float(cond.value))
    expected = cond.value
    # a string value naming another column means field-to-field comparison
    if isinstance(expected, str) and expected in row:
        expected = row[expected]
    try:
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
