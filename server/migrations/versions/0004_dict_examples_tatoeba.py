"""Ví dụ từ Tatoeba: thêm nguồn 'tatoeba' và cột source_ref.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dict_examples", sa.Column("source_ref", sa.String(length=32), nullable=True))
    op.drop_constraint(op.f("ck_dict_examples_source"), "dict_examples", type_="check")
    op.create_check_constraint(
        op.f("ck_dict_examples_source"), "dict_examples", "source IN ('curated', 'gloss', 'tatoeba', 'llm')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM dict_examples WHERE source = 'tatoeba'")
    op.drop_constraint(op.f("ck_dict_examples_source"), "dict_examples", type_="check")
    op.create_check_constraint(op.f("ck_dict_examples_source"), "dict_examples", "source IN ('curated', 'gloss', 'llm')")
    op.drop_column("dict_examples", "source_ref")
