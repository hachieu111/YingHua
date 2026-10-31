"""Giai đoạn 6.5 (M16 Gamification): XP, mùa thi đua, huy hiệu, mini-game.

- `xp_events` (F16.02): sổ cái XP chỉ thêm, khóa chống trùng `(user_id, source, source_ref)`.
- `seasons`, `season_results` (F16.09, F16.10): mùa thi đua theo tuần và kết quả đã chốt (top 50).
- `achievements`, `user_achievements` (F16.11, F16.12): danh mục huy hiệu (7 dòng khởi tạo) và huy hiệu đã đạt.
- `minigame_sessions` (F16.01): mỗi ván mini-game "chữ Hán rơi".
- `user_settings.show_on_leaderboard` (F16.08): ẩn danh trên bảng xếp hạng.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
NOW = sa.text("now()")

# (code, name, description, metric, thresholds, coin_rewards, style_key, sort_order)
ACHIEVEMENTS = [
    (
        "sakura_member",
        "Thành viên Hoa Anh Đào",
        "Thành viên thân thiết gắn bó với Yinghua",
        "study_days",
        [30, 100, 365],
        [50, 100, 200],
        "flower",
        1,
    ),
    (
        "top_scholar",
        "Đệ Nhất Học Giả",
        "Top 1 mùa giải điểm EXP cao nhất",
        "season_top3",
        [1],
        [0],
        "crown",
        2,
    ),
    (
        "manhua_elite",
        "Tinh Anh Manhua",
        "Độc giả đọc hơn 100 trang truyện",
        "pages_read",
        [100, 500, 2000],
        [50, 100, 200],
        "star",
        3,
    ),
    (
        "seed_sower",
        "Người Gieo Hạt",
        "Tích luỹ hơn 300 từ vựng tiếng Trung",
        "words_saved",
        [300, 1000, 3000],
        [50, 100, 200],
        "sprout",
        4,
    ),
    (
        "hsk3_master",
        "Vua Từ Vựng HSK 3",
        "Thành thạo trọn bộ 300 thẻ từ HSK 3",
        "hsk3_mastered",
        [300],
        [200],
        "trophy",
        5,
    ),
    (
        "night_owl",
        "Cú Đêm Cày Truyện",
        "Chăm chỉ học và đọc truyện sau 23:00",
        "night_pages",
        [50, 200, 500],
        [50, 100, 200],
        "moon",
        6,
    ),
    (
        "apprentice_translator",
        "Dịch Giả Tập Sự",
        "Tra cứu hơn 150 bong bóng thoại manhua",
        "bubble_lookups",
        [150, 500, 1500],
        [50, 100, 200],
        "scroll",
        7,
    ),
]


def upgrade() -> None:
    op.create_table(
        "xp_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_ref", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.SmallInteger(), nullable=False),
        sa.Column("capped", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "source IN ('page_read', 'review', 'word_saved', 'quiz', 'minigame', 'quest', 'weekly_goal',"
            " 'streak_milestone')",
            name=op.f("ck_xp_events_source"),
        ),
        sa.CheckConstraint("amount BETWEEN 0 AND 1000", name=op.f("ck_xp_events_amount")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_xp_events_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_xp_events")),
        sa.UniqueConstraint("user_id", "source", "source_ref", name=op.f("uq_xp_events_user_id_source_source_ref")),
    )
    op.create_index("ix_xp_events_created_at_user_id", "xp_events", ["created_at", "user_id"])
    op.create_index("ix_xp_events_user_id_activity_date", "xp_events", ["user_id", "activity_date"])

    op.create_table(
        "seasons",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("starts_at", TS, nullable=False),
        sa.Column("ends_at", TS, nullable=False),
        sa.Column("status", sa.String(length=12), server_default="active", nullable=False),
        sa.Column("finalized_at", TS, nullable=True),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint("number >= 1", name=op.f("ck_seasons_number")),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_seasons_period")),
        sa.CheckConstraint("status IN ('active', 'finalizing', 'finalized')", name=op.f("ck_seasons_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seasons")),
        sa.UniqueConstraint("number", name=op.f("uq_seasons_number")),
        sa.UniqueConstraint("starts_at", name=op.f("uq_seasons_starts_at")),
    )
    op.create_index("ix_seasons_status_ends_at", "seasons", ["status", "ends_at"])

    op.create_table(
        "season_results",
        sa.Column("season_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=8), nullable=False),
        sa.Column("reward_granted_at", TS, nullable=True),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint("rank BETWEEN 1 AND 50", name=op.f("ck_season_results_rank")),
        sa.CheckConstraint("xp >= 0", name=op.f("ck_season_results_xp")),
        sa.CheckConstraint("tier IN ('top3', 'top10', 'top50')", name=op.f("ck_season_results_tier")),
        sa.ForeignKeyConstraint(
            ["season_id"], ["seasons.id"], name=op.f("fk_season_results_season_id_seasons"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_season_results_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("season_id", "user_id", name=op.f("pk_season_results")),
        sa.UniqueConstraint("season_id", "rank", name=op.f("uq_season_results_season_id_rank")),
    )
    op.create_index("ix_season_results_user_id", "season_results", ["user_id"])

    achievements = op.create_table(
        "achievements",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("metric", sa.String(length=24), nullable=False),
        sa.Column("thresholds", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("coin_rewards", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("style_key", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "metric IN ('study_days', 'pages_read', 'words_saved', 'hsk3_mastered', 'night_pages',"
            " 'bubble_lookups', 'season_top3')",
            name=op.f("ck_achievements_metric"),
        ),
        sa.CheckConstraint(
            "cardinality(thresholds) BETWEEN 1 AND 3", name=op.f("ck_achievements_thresholds")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_achievements")),
        sa.UniqueConstraint("code", name=op.f("uq_achievements_code")),
    )
    op.bulk_insert(
        achievements,
        [
            {
                "code": code,
                "name": name,
                "description": description,
                "metric": metric,
                "thresholds": thresholds,
                "coin_rewards": coin_rewards,
                "style_key": style_key,
                "sort_order": sort_order,
            }
            for code, name, description, metric, thresholds, coin_rewards, style_key, sort_order in ACHIEVEMENTS
        ],
    )

    op.create_table(
        "user_achievements",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("achievement_id", sa.BigInteger(), nullable=False),
        sa.Column("tier", sa.SmallInteger(), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("is_equipped", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("unlocked_at", TS, nullable=False),
        sa.Column("tier_reached_at", TS, nullable=False),
        sa.CheckConstraint("tier BETWEEN 1 AND 3", name=op.f("ck_user_achievements_tier")),
        sa.CheckConstraint("source IN ('rule', 'season')", name=op.f("ck_user_achievements_source")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_achievements_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["achievement_id"],
            ["achievements.id"],
            name=op.f("fk_user_achievements_achievement_id_achievements"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("user_id", "achievement_id", name=op.f("pk_user_achievements")),
    )
    # Mỗi người tối đa một huy hiệu đang đeo.
    op.create_index(
        "uq_user_achievements_user_id_equipped",
        "user_achievements",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_equipped"),
    )

    op.create_table(
        "minigame_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_type", sa.String(length=24), nullable=False),
        sa.Column("target_radical", sa.String(length=8), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("correct", sa.SmallInteger(), nullable=False),
        sa.Column("wrong", sa.SmallInteger(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("played_at", TS, nullable=False),
        sa.CheckConstraint("game_type IN ('falling_radical')", name=op.f("ck_minigame_sessions_game_type")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_minigame_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_minigame_sessions")),
    )
    op.create_index("ix_minigame_sessions_user_id_played_at", "minigame_sessions", ["user_id", "played_at"])

    op.add_column(
        "user_settings",
        sa.Column("show_on_leaderboard", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "show_on_leaderboard")
    op.drop_index("ix_minigame_sessions_user_id_played_at", table_name="minigame_sessions")
    op.drop_table("minigame_sessions")
    op.drop_index("uq_user_achievements_user_id_equipped", table_name="user_achievements")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    op.drop_index("ix_season_results_user_id", table_name="season_results")
    op.drop_table("season_results")
    op.drop_index("ix_seasons_status_ends_at", table_name="seasons")
    op.drop_table("seasons")
    op.drop_index("ix_xp_events_user_id_activity_date", table_name="xp_events")
    op.drop_index("ix_xp_events_created_at_user_id", table_name="xp_events")
    op.drop_table("xp_events")
