"""Bảng của M10 (docs/database-design.md §4.14). Tạo ở migration 0007."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DismissedSuggestionModel(Base):
    __tablename__ = "dismissed_suggestions"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    term: Mapped[str] = mapped_column(String(32), primary_key=True)
    dismissed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
