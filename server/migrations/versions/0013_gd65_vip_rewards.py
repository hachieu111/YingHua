"""Giai đoạn 6.5 (M17 VIP & Phần thưởng): ví, sổ phần thưởng, VIP, khung avatar, cửa hàng đổi thưởng.

- `avatar_frames` (F17.08): danh mục khung (5 dòng khởi tạo).
- `wallets` (F17.01-F17.03): xu, vé, hạn VIP, khung đang đeo; 1-1 với `users`.
- `wallet_ledger` (F17.01): sổ chỉ thêm, khóa chống trùng `(user_id, currency, idempotency_key)`.
- `vip_unlocks` (F17.06): truyện VIP đã mở khóa bằng vé.
- `user_frames` (F17.08): khung người dùng sở hữu (vĩnh viễn hoặc có hạn).
- `reward_items`, `reward_redemptions` (F17.07, F17.09): danh mục đổi thưởng (5 dòng khởi tạo) và lượt đổi.
- `series.is_vip` (F17.05): cờ truyện VIP, chỉ truyện công khai.
Không có bảng thanh toán hay thẻ: xu chỉ kiếm từ học tập (người dùng chốt 30/10/2026).

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
NOW = sa.text("now()")

# (code, name, description, style_key, acquire_kind)
FRAMES = [
    (
        "sakura_gold",
        "Hoa Anh Đào Vàng",
        "Thưởng mùa top 1-3 (vĩnh viễn) hoặc đạt mục tiêu tuần (7 ngày)",
        "sakura_gold",
        "season",
    ),
    ("spring_petal", "Cánh Hoa Mùa Xuân", "Thưởng mùa top 4-10", "spring_petal", "season"),
    ("vip_sakura", "Khung VIP Hoa Anh Đào", "Dùng được khi đang VIP", "vip_sakura", "vip"),
    ("bamboo_leaf", "Lá Trúc Xanh", "Đổi ở cửa hàng", "bamboo_leaf", "shop"),
    ("ink_cloud", "Mây Mực", "Đổi ở cửa hàng", "ink_cloud", "shop"),
]

# (code, name, description, kind, price, vip_days, ticket_count, frame_code, sort_order)
ITEMS = [
    ("vip_1d", "1 ngày VIP", "Cộng thêm 1 ngày VIP", "vip_days", 120, 1, None, None, 1),
    ("vip_7d", "7 ngày VIP", "Cộng thêm 7 ngày VIP", "vip_days", 700, 7, None, None, 2),
    ("vip_ticket", "1 vé đọc truyện VIP", "Mở khóa vĩnh viễn một truyện VIP", "vip_ticket", 300, None, 1, None, 3),
    ("frame_bamboo", 'Khung avatar "Lá Trúc Xanh"', "Khung avatar", "avatar_frame", 800, None, None, "bamboo_leaf", 4),
    ("frame_ink", 'Khung avatar "Mây Mực"', "Khung avatar", "avatar_frame", 800, None, None, "ink_cloud", 5),
]


def upgrade() -> None:
    frames = op.create_table(
        "avatar_frames",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("style_key", sa.String(length=32), nullable=False),
        sa.Column("acquire_kind", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "acquire_kind IN ('season', 'shop', 'vip')", name=op.f("ck_avatar_frames_acquire_kind")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_avatar_frames")),
        sa.UniqueConstraint("code", name=op.f("uq_avatar_frames_code")),
    )
    op.bulk_insert(
        frames,
        [
            {"code": c, "name": n, "description": d, "style_key": s, "acquire_kind": k}
            for c, n, d, s, k in FRAMES
        ],
    )

    op.create_table(
        "wallets",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("coin_balance", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ticket_balance", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("vip_until", TS, nullable=True),
        sa.Column("vip_reminded_for", TS, nullable=True),
        sa.Column("equipped_frame_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint("coin_balance >= 0", name=op.f("ck_wallets_coin_balance")),
        sa.CheckConstraint("ticket_balance BETWEEN 0 AND 99", name=op.f("ck_wallets_ticket_balance")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_wallets_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["equipped_frame_id"],
            ["avatar_frames.id"],
            name=op.f("fk_wallets_equipped_frame_id_avatar_frames"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_wallets")),
    )
    op.create_index(
        "ix_wallets_vip_until",
        "wallets",
        ["vip_until"],
        postgresql_where=sa.text("vip_until IS NOT NULL"),
    )

    op.create_table(
        "wallet_ledger",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=True),
        sa.Column("vip_until_after", TS, nullable=True),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint("currency IN ('coin', 'ticket', 'vip_days')", name=op.f("ck_wallet_ledger_currency")),
        sa.CheckConstraint("amount <> 0", name=op.f("ck_wallet_ledger_amount")),
        sa.CheckConstraint(
            "reason IN ('season_reward', 'quest_bonus', 'streak_milestone', 'achievement', 'welcome',"
            " 'redemption', 'vip_unlock', 'admin_adjust')",
            name=op.f("ck_wallet_ledger_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_wallet_ledger_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_wallet_ledger_actor_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallet_ledger")),
        sa.UniqueConstraint(
            "user_id", "currency", "idempotency_key", name=op.f("uq_wallet_ledger_user_id_currency_idempotency_key")
        ),
    )
    op.create_index("ix_wallet_ledger_user_id_created_at", "wallet_ledger", ["user_id", "created_at"])

    op.create_table(
        "vip_unlocks",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("series_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("unlocked_at", TS, nullable=False),
        sa.CheckConstraint("source IN ('ticket', 'admin')", name=op.f("ck_vip_unlocks_source")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_vip_unlocks_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["series_id"], ["series.id"], name=op.f("fk_vip_unlocks_series_id_series"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "series_id", name=op.f("pk_vip_unlocks")),
    )
    op.create_index("ix_vip_unlocks_series_id", "vip_unlocks", ["series_id"])

    op.create_table(
        "user_frames",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("frame_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=12), nullable=False),
        sa.Column("acquired_at", TS, nullable=False),
        sa.Column("expires_at", TS, nullable=True),
        sa.CheckConstraint(
            "source IN ('season', 'weekly_goal', 'redemption', 'admin')", name=op.f("ck_user_frames_source")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_frames_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["frame_id"],
            ["avatar_frames.id"],
            name=op.f("fk_user_frames_frame_id_avatar_frames"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("user_id", "frame_id", name=op.f("pk_user_frames")),
    )

    op.create_table(
        "reward_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("price_coins", sa.Integer(), nullable=False),
        sa.Column("vip_days", sa.SmallInteger(), nullable=True),
        sa.Column("ticket_count", sa.SmallInteger(), nullable=True),
        sa.Column("frame_id", sa.BigInteger(), nullable=True),
        sa.Column("per_user_limit", sa.SmallInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "kind IN ('vip_days', 'vip_ticket', 'avatar_frame')", name=op.f("ck_reward_items_kind")
        ),
        sa.CheckConstraint("price_coins BETWEEN 1 AND 100000", name=op.f("ck_reward_items_price_coins")),
        sa.CheckConstraint("vip_days BETWEEN 1 AND 365", name=op.f("ck_reward_items_vip_days")),
        sa.CheckConstraint("ticket_count BETWEEN 1 AND 10", name=op.f("ck_reward_items_ticket_count")),
        sa.CheckConstraint("per_user_limit >= 1", name=op.f("ck_reward_items_per_user_limit")),
        sa.CheckConstraint(
            "(kind = 'vip_days') = (vip_days IS NOT NULL)"
            " AND (kind = 'vip_ticket') = (ticket_count IS NOT NULL)"
            " AND (kind = 'avatar_frame') = (frame_id IS NOT NULL)",
            name=op.f("ck_reward_items_kind_fields"),
        ),
        sa.ForeignKeyConstraint(
            ["frame_id"],
            ["avatar_frames.id"],
            name=op.f("fk_reward_items_frame_id_avatar_frames"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_reward_items_updated_by_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reward_items")),
        sa.UniqueConstraint("code", name=op.f("uq_reward_items_code")),
    )
    for code, name, description, kind, price, vip_days, tickets, frame_code, sort_order in ITEMS:
        op.execute(
            sa.text(
                "INSERT INTO reward_items (code, name, description, kind, price_coins, vip_days, ticket_count,"
                " frame_id, sort_order) VALUES (:code, :name, :description, :kind, :price, :vip_days, :tickets,"
                " (SELECT id FROM avatar_frames WHERE code = :frame_code), :sort_order)"
            ).bindparams(
                code=code,
                name=name,
                description=description,
                kind=kind,
                price=price,
                vip_days=vip_days,
                tickets=tickets,
                frame_code=frame_code,
                sort_order=sort_order,
            )
        )

    op.create_table(
        "reward_redemptions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("price_coins", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.CheckConstraint("price_coins > 0", name=op.f("ck_reward_redemptions_price_coins")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_reward_redemptions_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["reward_items.id"],
            name=op.f("fk_reward_redemptions_item_id_reward_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reward_redemptions")),
        sa.UniqueConstraint("user_id", "request_id", name=op.f("uq_reward_redemptions_user_id_request_id")),
    )
    op.create_index("ix_reward_redemptions_user_id_item_id", "reward_redemptions", ["user_id", "item_id"])
    op.create_index("ix_reward_redemptions_user_id_created_at", "reward_redemptions", ["user_id", "created_at"])

    op.add_column("series", sa.Column("is_vip", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_check_constraint(
        op.f("ck_series_vip_public"), "series", "NOT is_vip OR visibility = 'public'"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_series_vip_public"), "series", type_="check")
    op.drop_column("series", "is_vip")
    op.drop_table("reward_redemptions")
    op.drop_table("reward_items")
    op.drop_table("user_frames")
    op.drop_table("vip_unlocks")
    op.drop_table("wallet_ledger")
    op.drop_table("wallets")
    op.drop_table("avatar_frames")
