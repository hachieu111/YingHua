"""Bảng của M01 (docs/database-design.md §4.1). Chỉ dùng trong tầng hạ tầng."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.stored_files import StoredFileModel  # noqa: F401  (đăng ký bảng cho khóa ngoại avatar_file_id)

TS = DateTime(timezone=True)


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="role"),
        CheckConstraint("status IN ('active', 'locked')", name="status"),
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
        Index("ix_users_role", "role"),
        Index("ix_users_status", "status"),
        Index(
            "ix_users_email_trgm", "email", postgresql_using="gin", postgresql_ops={"email": "gin_trgm_ops"}
        ),
        Index(
            "ix_users_display_name_trgm",
            "display_name",
            postgresql_using="gin",
            postgresql_ops={"display_name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(100))
    chinese_name: Mapped[str | None] = mapped_column(String(32))
    avatar_file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        # use_alter: users và stored_files tham chiếu vòng nhau (owner_id <-> avatar_file_id).
        ForeignKey(
            "stored_files.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_users_avatar_file_id_stored_files",
        ),
    )
    avatar_preset: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(16), server_default="user")
    status: Mapped[str] = mapped_column(String(16), server_default="active")
    locked_reason: Mapped[str | None] = mapped_column(String(500))
    locked_at: Mapped[datetime | None] = mapped_column(TS)
    show_email: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    show_join_date: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    password_changed_at: Mapped[datetime | None] = mapped_column(TS)
    last_login_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_family_id", "family_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    replaced_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(TS)
    revoked_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(TS)
    used_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
