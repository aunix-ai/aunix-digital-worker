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


class ActionPolicy(BaseModel):
    """L4 declarative allowlist + caps. An action auto-executes only if its type's
    `*_auto` flag is on, its target is within the type's bounds, and neither cap is
    exceeded; otherwise it falls back to the L3 approval queue (never dropped)."""
    email_auto: bool = False
    email_to_domains: list[str] = []      # recipient must match one of these domains
    hubspot_auto: bool = False
    hubspot_ops: list[str] = []           # only these ops auto-execute
    task_auto: bool = False
    resolve_auto: bool = False
    per_run: int = Field(default=3, ge=0)   # max auto-executions per run
    per_day: int = Field(default=20, ge=0)  # max auto-executions per agent per rolling 24h


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
    policy: ActionPolicy | None = None  # L4 only: which actions auto-execute, within caps
    reasoning_instructions: str | None = None  # free-text guidance for the LLM reasoner (Plan 2)
    rank_by: str | None = None  # analysis: numeric field for deterministic ranking
    top_n: int = Field(default=5, ge=1)  # analysis: briefing size

    @model_validator(mode="after")
    def check_action_permissions(self):
        if self.autonomy_level >= 3 and not self.actions:
            raise ValueError("autonomy level 3+ requires at least one action permission")
        if self.autonomy_level <= 2 and self.actions:
            raise ValueError("autonomy levels 1-2 cannot declare actions")
        if self.autonomy_level == 4 and self.policy is None:
            raise ValueError("autonomy level 4 requires a policy")
        if self.autonomy_level != 4 and self.policy is not None:
            raise ValueError("policy is only valid at autonomy level 4")
        return self
