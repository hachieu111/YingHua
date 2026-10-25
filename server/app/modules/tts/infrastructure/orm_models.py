"""Bảng của M11 (docs/database-design.md §4.12): bộ nhớ đệm âm thanh và nhật ký gọi dịch vụ ngoài.

Tạo ở migration 0006 cùng bảng M07/M08; mã nghiệp vụ M11 (TTS) làm ở lượt 4b.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class TtsCacheModel(Base):
    __tablename__ = "tts_cache"
    __table_args__ = (UniqueConstraint("text_sha256", "voice", "rate"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    text_sha256: Mapped[str] = mapped_column(CHAR(64))
    voice: Mapped[str] = mapped_column(String(64))
    rate: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stored_files.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class ExternalCallLogModel(Base):
    """Nhật ký gọi LLM/TTS; không chứa dữ liệu cá nhân."""

    __tablename__ = "external_call_logs"
    __table_args__ = (
        CheckConstraint("service IN ('llm', 'tts')", name="service"),
        CheckConstraint("status IN ('ok', 'timeout', 'invalid', 'error')", name="status"),
        Index("ix_external_call_logs_service_created_at", "service", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    service: Mapped[str] = mapped_column(String(8))
    provider: Mapped[str] = mapped_column(String(32))
    operation: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(12))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
