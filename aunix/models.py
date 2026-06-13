from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|active|paused
    spec: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    trigger: Mapped[str] = mapped_column(String(20))  # interval|daily|manual
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|succeeded|failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trace: Mapped[dict] = mapped_column(JSON, default=dict)  # explainability backbone
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # idempotency key for scheduled runs: one run per (agent, schedule slot)
    slot_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_agent_state", "agent_id", "state"),
        Index("ix_findings_agent_dedupe", "agent_id", "dedupe_key"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    dedupe_key: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(20), default="new")  # new|ongoing|resolved
    severity: Mapped[str] = mapped_column(String(20), default="info")
    summary: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(String(500), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    channel: Mapped[str] = mapped_column(String(20))  # feed|email
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|sent|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Connection(Base):
    __tablename__ = "connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))  # hubspot|simship|csv
    credentials: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Action(Base):
    __tablename__ = "actions"
    __table_args__ = (Index("ix_actions_agent_dedupe", "agent_id", "dedupe_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    type: Mapped[str] = mapped_column(String(20))  # email|hubspot|task|resolve
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending|approved|executed|rejected|expired|failed
    origin: Mapped[str] = mapped_column(String(4))  # L3|L4
    policy_decision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(300))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    title: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
