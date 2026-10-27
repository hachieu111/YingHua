"""Bảng của M14 (docs/database-design.md §4.17). Tạo ở migration 0009."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class ErrorReportModel(Base):
    __tablename__ = "error_reports"
    __table_args__ = (
        CheckConstraint("report_type IN ('ocr', 'translation', 'other')", name="report_type"),
        CheckConstraint("status IN ('new', 'resolved', 'rejected')", name="status"),
        Index("ix_error_reports_reporter_id_created_at", "reporter_id", "created_at"),
        Index("ix_error_reports_status_created_at", "status", "created_at"),
        # Chỉ mục duy nhất từng phần `uq_error_reports_open` (COALESCE) tạo bằng SQL ở migration 0009.
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    page_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("pages.id", ondelete="SET NULL"))
    bubble_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("bubbles.id", ondelete="SET NULL"))
    report_type: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(12), server_default="new")
    resolution_note: Mapped[str | None] = mapped_column(String(1000))
    handled_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    handled_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("channel IN ('in_app', 'email')", name="channel"),
        CheckConstraint("status IN ('pending', 'sent', 'failed')", name="status"),
        Index("ix_notifications_user_id_read_at", "user_id", "read_at"),
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(8))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    read_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(TS)


class ReminderLogModel(Base):
    __tablename__ = "reminder_logs"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    reminder_date: Mapped[date] = mapped_column(Date, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(TS)
