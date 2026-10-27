"""Bảng của M12 (docs/database-design.md §4.15). Tạo ở migration 0009."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DailyActivityModel(Base):
    __tablename__ = "daily_activities"
    __table_args__ = (
        CheckConstraint(
            "reviews_count >= 0 AND pages_read >= 0 AND words_saved >= 0 AND quizzes_done >= 0"
            " AND study_seconds >= 0",
            name="counters",
        ),
        Index("ix_daily_activities_activity_date", "activity_date"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
    reviews_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    pages_read: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    words_saved: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    quizzes_done: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    study_seconds: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
