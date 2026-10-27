"""Giai đoạn 6 (đợt A1): thống kê, báo lỗi, thông báo và nhắc ôn.

- `daily_activities` (F12.01, F12.02): bộ đếm hoạt động theo ngày của múi giờ người học.
- `error_reports` (F14.01, F14.02): báo lỗi nhận diện/dịch; chỉ một báo lỗi "new" cho mỗi (người, trang,
  bong bóng, loại).
- `notifications` (F14.05, F14.04): thông báo trong ứng dụng và email; thêm cột `data` (JSONB) để giao diện
  điều hướng tới đúng trang/báo lỗi.
- `reminder_logs` (F14.04): mỗi người tối đa một lần thử nhắc mỗi ngày.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
ZERO = sa.text("0")


def _counter(name: str) -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(name, sa.Integer(), server_default=ZERO, nullable=False)


def upgrade() -> None:
    op.create_table(
        "daily_activities",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        _counter("reviews_count"),
        _counter("pages_read"),
        _counter("words_saved"),
        _counter("quizzes_done"),
        _counter("study_seconds"),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "reviews_count >= 0 AND pages_read >= 0 AND words_saved >= 0 AND quizzes_done >= 0"
            " AND study_seconds >= 0",
            name=op.f("ck_daily_activities_counters"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_daily_activities_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "activity_date", name=op.f("pk_daily_activities")),
    )
    op.create_index("ix_daily_activities_activity_date", "daily_activities", ["activity_date"])

    op.create_table(
        "error_reports",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("reporter_id", sa.BigInteger(), nullable=False),
        sa.Column("page_id", sa.BigInteger(), nullable=True),
        sa.Column("bubble_id", sa.BigInteger(), nullable=True),
        sa.Column("report_type", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="new", nullable=False),
        sa.Column("resolution_note", sa.String(length=1000), nullable=True),
        sa.Column("handled_by", sa.BigInteger(), nullable=True),
        sa.Column("handled_at", TS, nullable=True),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "report_type IN ('ocr', 'translation', 'other')", name=op.f("ck_error_reports_report_type")
        ),
        sa.CheckConstraint("status IN ('new', 'resolved', 'rejected')", name=op.f("ck_error_reports_status")),
        sa.ForeignKeyConstraint(
            ["reporter_id"], ["users.id"], name=op.f("fk_error_reports_reporter_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name=op.f("fk_error_reports_page_id_pages"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["bubble_id"], ["bubbles.id"], name=op.f("fk_error_reports_bubble_id_bubbles"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["handled_by"], ["users.id"], name=op.f("fk_error_reports_handled_by_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_error_reports")),
    )
    op.create_index("ix_error_reports_reporter_id_created_at", "error_reports", ["reporter_id", "created_at"])
    op.create_index("ix_error_reports_status_created_at", "error_reports", ["status", "created_at"])
    # Chống báo lỗi trùng khi báo lỗi cũ còn "new" (F14.01); bong bóng trống tính chung một nhóm.
    op.execute(
        "CREATE UNIQUE INDEX uq_error_reports_open ON error_reports "
        "(reporter_id, COALESCE(page_id, 0), COALESCE(bubble_id, 0), report_type) WHERE status = 'new'"
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"),
                  nullable=False),
        sa.Column("read_at", TS, nullable=True),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", TS, nullable=True),
        sa.CheckConstraint("channel IN ('in_app', 'email')", name=op.f("ck_notifications_channel")),
        sa.CheckConstraint("status IN ('pending', 'sent', 'failed')", name=op.f("ck_notifications_status")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_notifications_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index("ix_notifications_user_id_read_at", "notifications", ["user_id", "read_at"])
    op.create_index("ix_notifications_user_id_created_at", "notifications", ["user_id", "created_at"])

    op.create_table(
        "reminder_logs",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("reminder_date", sa.Date(), nullable=False),
        sa.Column("sent_at", TS, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_reminder_logs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "reminder_date", name=op.f("pk_reminder_logs")),
    )


def downgrade() -> None:
    op.drop_table("reminder_logs")
    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id_read_at", table_name="notifications")
    op.drop_table("notifications")
    op.execute("DROP INDEX IF EXISTS uq_error_reports_open")
    op.drop_index("ix_error_reports_status_created_at", table_name="error_reports")
    op.drop_index("ix_error_reports_reporter_id_created_at", table_name="error_reports")
    op.drop_table("error_reports")
    op.drop_index("ix_daily_activities_activity_date", table_name="daily_activities")
    op.drop_table("daily_activities")
