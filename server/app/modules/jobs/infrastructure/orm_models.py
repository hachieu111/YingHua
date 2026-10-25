"""Bảng của M15 (docs/database-design.md §4.9). Tạo ở migration 0005; mã nghiệp vụ làm ở lượt 3b."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class ScheduledJobModel(Base):
    __tablename__ = "scheduled_jobs"
    __table_args__ = (CheckConstraint("last_status IN ('ok', 'failed')", name="last_status"),)

    name: Mapped[str] = mapped_column(String(48), primary_key=True)
    interval_seconds: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    last_started_at: Mapped[datetime | None] = mapped_column(TS)
    last_finished_at: Mapped[datetime | None] = mapped_column(TS)
    last_status: Mapped[str | None] = mapped_column(String(12))
    locked_until: Mapped[datetime | None] = mapped_column(TS)
    locked_by: Mapped[str | None] = mapped_column(String(64))


class JobRunModel(Base):
    __tablename__ = "job_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'ok', 'failed')", name="status"),
        Index("ix_job_runs_job_name", "job_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    job_name: Mapped[str] = mapped_column(String(48), ForeignKey("scheduled_jobs.name", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(TS)
    finished_at: Mapped[datetime | None] = mapped_column(TS)
    status: Mapped[str] = mapped_column(String(12), server_default="running")
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
