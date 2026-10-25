"""Bảng `user_settings` (docs/database-design.md §4.2)."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserSettingsModel(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint("hsk_level BETWEEN 1 AND 9", name="hsk_level"),
        CheckConstraint("default_mode IN ('read', 'learn')", name="default_mode"),
        CheckConstraint("tts_rate BETWEEN 0.50 AND 1.50", name="tts_rate"),
        CheckConstraint("learning_goal IN ('study', 'entertainment', 'both')", name="learning_goal"),
        CheckConstraint("weekly_page_goal BETWEEN 1 AND 1000", name="weekly_page_goal"),
        CheckConstraint("bubble_font_scale BETWEEN 80 AND 160", name="bubble_font_scale"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    hsk_level: Mapped[int | None] = mapped_column(SmallInteger)
    default_mode: Mapped[str] = mapped_column(String(8), server_default="read")
    tts_voice: Mapped[str | None] = mapped_column(String(64))
    tts_rate: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False), server_default=text("1.00"))
    show_xianxia: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    bubble_font_scale: Mapped[int] = mapped_column(SmallInteger, server_default=text("100"))
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reminder_time: Mapped[time | None] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(String(64), server_default="Asia/Ho_Chi_Minh")
    learning_goal: Mapped[str | None] = mapped_column(String(16))
    weekly_page_goal: Mapped[int | None] = mapped_column(SmallInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
