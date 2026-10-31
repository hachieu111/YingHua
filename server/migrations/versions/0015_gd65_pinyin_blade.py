"""Giai đoạn 6.5 (M16): mini-game "Gõ pinyin chém chữ" thay "chữ Hán rơi" (F16.01).

- `minigame_rounds`: thêm chế độ chơi (`mode`), cấp HSK (`hsk_band`), bộ mục đã phát kèm đáp án (`items`);
  `radical` cho phép NULL; bỏ `chars` (đã nằm trong `items`). Dòng cũ nhận `mode = 'weak_radical'` và `items = []`
  (lượt cũ chỉ sống tối đa 7 ngày rồi bị dọn).
- `minigame_sessions`: mở `game_type` thêm `pinyin_blade`; `target_radical` cho NULL; thêm `hsk_band`,
  `max_combo`, `typos`; chỉ mục phục vụ kỷ lục theo cấp.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "minigame_rounds",
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="weak_radical"),
    )
    op.alter_column("minigame_rounds", "mode", server_default=None)
    op.add_column("minigame_rounds", sa.Column("hsk_band", sa.SmallInteger(), nullable=True))
    op.add_column(
        "minigame_rounds",
        sa.Column(
            "items", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    op.alter_column("minigame_rounds", "items", server_default=None)
    op.alter_column("minigame_rounds", "radical", existing_type=sa.String(length=8), nullable=True)
    op.drop_column("minigame_rounds", "chars")
    op.create_check_constraint(
        op.f("ck_minigame_rounds_mode"), "minigame_rounds", "mode IN ('hsk', 'weak_radical')"
    )
    op.create_check_constraint(
        op.f("ck_minigame_rounds_hsk_band"), "minigame_rounds", "hsk_band BETWEEN 1 AND 7"
    )

    op.drop_constraint(op.f("ck_minigame_sessions_game_type"), "minigame_sessions", type_="check")
    op.create_check_constraint(
        op.f("ck_minigame_sessions_game_type"),
        "minigame_sessions",
        "game_type IN ('falling_radical', 'pinyin_blade')",
    )
    op.alter_column("minigame_sessions", "target_radical", existing_type=sa.String(length=8), nullable=True)
    op.add_column("minigame_sessions", sa.Column("hsk_band", sa.SmallInteger(), nullable=True))
    op.add_column(
        "minigame_sessions",
        sa.Column("max_combo", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "minigame_sessions", sa.Column("typos", sa.SmallInteger(), nullable=False, server_default="0")
    )
    op.create_check_constraint(
        op.f("ck_minigame_sessions_hsk_band"), "minigame_sessions", "hsk_band BETWEEN 1 AND 7"
    )
    op.create_index(
        "ix_minigame_sessions_user_id_game_type_hsk_band",
        "minigame_sessions",
        ["user_id", "game_type", "hsk_band"],
    )


def downgrade() -> None:
    op.drop_index("ix_minigame_sessions_user_id_game_type_hsk_band", table_name="minigame_sessions")
    op.drop_constraint(op.f("ck_minigame_sessions_hsk_band"), "minigame_sessions", type_="check")
    op.drop_column("minigame_sessions", "typos")
    op.drop_column("minigame_sessions", "max_combo")
    op.drop_column("minigame_sessions", "hsk_band")
    op.execute("DELETE FROM minigame_sessions WHERE game_type = 'pinyin_blade'")
    op.execute("UPDATE minigame_sessions SET target_radical = '' WHERE target_radical IS NULL")
    op.alter_column("minigame_sessions", "target_radical", existing_type=sa.String(length=8), nullable=False)
    op.drop_constraint(op.f("ck_minigame_sessions_game_type"), "minigame_sessions", type_="check")
    op.create_check_constraint(
        op.f("ck_minigame_sessions_game_type"), "minigame_sessions", "game_type IN ('falling_radical')"
    )

    op.drop_constraint(op.f("ck_minigame_rounds_hsk_band"), "minigame_rounds", type_="check")
    op.drop_constraint(op.f("ck_minigame_rounds_mode"), "minigame_rounds", type_="check")
    op.add_column(
        "minigame_rounds",
        sa.Column(
            "chars",
            postgresql.ARRAY(sa.String(length=8)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.alter_column("minigame_rounds", "chars", server_default=None)
    op.execute("UPDATE minigame_rounds SET radical = '' WHERE radical IS NULL")
    op.alter_column("minigame_rounds", "radical", existing_type=sa.String(length=8), nullable=False)
    op.drop_column("minigame_rounds", "items")
    op.drop_column("minigame_rounds", "hsk_band")
    op.drop_column("minigame_rounds", "mode")
