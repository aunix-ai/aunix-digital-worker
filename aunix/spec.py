from typing import Literal

from pydantic import BaseModel, model_validator

Operator = Literal["gt", "lt", "gte", "lte", "eq", "ne", "stale_hours"]


class Condition(BaseModel):
    field: str
    operator: Operator
    value: float | str


class ConditionGroup(BaseModel):
    mode: Literal["all", "any"]
    conditions: list[Condition]


class Schedule(BaseModel):
    mode: Literal["interval", "daily", "on_demand"]
    interval_minutes: int | None = None
    daily_time: str | None = None  # "HH:MM", 24h

    @model_validator(mode="after")
    def check_mode_fields(self):
        if self.mode == "interval" and not self.interval_minutes:
            raise ValueError("interval schedule requires interval_minutes")
        if self.mode == "daily" and not self.daily_time:
            raise ValueError("daily schedule requires daily_time")
        return self


class NotificationRule(BaseModel):
    channels: list[Literal["feed", "email"]]
    email_to: str | None = None

    @model_validator(mode="after")
    def check_email(self):
        if "email" in self.channels and not self.email_to:
            raise ValueError("email channel requires email_to")
        return self


class AgentSpec(BaseModel):
    name: str
    objective: str
    task_type: Literal["monitoring", "analysis"]
    data_sources: list[str]
    record_key: str = "id"  # field identifying a record in fetched rows
    conditions: ConditionGroup | None = None
    schedule: Schedule
    notifications: NotificationRule
    autonomy_level: Literal[1, 2] = 1
    reasoning_instructions: str | None = None  # free-text guidance for the LLM reasoner (Plan 2)
    rank_by: str | None = None  # analysis: numeric field for deterministic ranking
    top_n: int = 5  # analysis: briefing size
