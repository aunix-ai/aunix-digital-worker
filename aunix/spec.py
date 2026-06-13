from typing import Literal

from pydantic import BaseModel, Field, model_validator

Operator = Literal["gt", "lt", "gte", "lte", "eq", "ne", "stale_hours"]


class Condition(BaseModel):
    field: str
    operator: Operator
    value: float | str

    @model_validator(mode="after")
    def check_stale_hours_numeric(self):
        if self.operator == "stale_hours" and isinstance(self.value, str):
            raise ValueError("stale_hours requires a numeric value")
        return self


class ConditionGroup(BaseModel):
    mode: Literal["all", "any"]
    conditions: list[Condition]


class Schedule(BaseModel):
    mode: Literal["interval", "daily", "on_demand"]
    interval_minutes: int | None = Field(default=None, ge=1)
    daily_time: str | None = None  # "HH:MM", 24h

    @model_validator(mode="after")
    def check_mode_fields(self):
        if self.mode == "interval" and self.interval_minutes is None:
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


class ActionPermission(BaseModel):
    type: Literal["email", "hubspot", "task", "resolve"]
    to_field: str | None = None  # email: row field holding the recipient
    to: str | None = None        # email: fixed recipient when there is no field
    ops: list[Literal["add_note", "set_property"]] = []  # hubspot


class AgentSpec(BaseModel):
    name: str
    objective: str
    task_type: Literal["monitoring", "analysis"]
    data_sources: list[str]
    record_key: str = "id"  # field identifying a record in fetched rows
    conditions: ConditionGroup | None = None
    schedule: Schedule
    notifications: NotificationRule
    autonomy_level: Literal[1, 2, 3, 4] = 1
    actions: list[ActionPermission] = []
    reasoning_instructions: str | None = None  # free-text guidance for the LLM reasoner (Plan 2)
    rank_by: str | None = None  # analysis: numeric field for deterministic ranking
    top_n: int = Field(default=5, ge=1)  # analysis: briefing size

    @model_validator(mode="after")
    def check_action_permissions(self):
        if self.autonomy_level >= 3 and not self.actions:
            raise ValueError("autonomy level 3+ requires at least one action permission")
        if self.autonomy_level <= 2 and self.actions:
            raise ValueError("autonomy levels 1-2 cannot declare actions")
        return self
