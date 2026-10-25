"""Giai đoạn 4: M07 sổ tay, M08 ôn tập FSRS, M11 bộ nhớ đệm TTS và nhật ký dịch vụ ngoài.

Tạo toàn bộ bảng GĐ4 một lần (docs/database-design.md §4.10–4.12, §6.2) gồm `vocab_entries.is_starred`;
`tts_cache` và `external_call_logs` để lượt 4b (M11) chỉ viết mã. `fsrs_parameters` tạo sẵn cho F08.08 (GĐ6).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('external_call_logs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('service', sa.String(length=8), nullable=False),
    sa.Column('provider', sa.String(length=32), nullable=False),
    sa.Column('operation', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('error_code', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("service IN ('llm', 'tts')", name=op.f('ck_external_call_logs_service')),
    sa.CheckConstraint("status IN ('ok', 'timeout', 'invalid', 'error')", name=op.f('ck_external_call_logs_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_external_call_logs'))
    )
    op.create_index('ix_external_call_logs_service_created_at', 'external_call_logs', ['service', 'created_at'], unique=False)
    op.create_table('fsrs_parameters',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('weights', sa.ARRAY(sa.Double()), nullable=False),
    sa.Column('desired_retention', sa.Numeric(precision=3, scale=2), server_default=sa.text('0.90'), nullable=False),
    sa.Column('review_count', sa.Integer(), nullable=False),
    sa.Column('optimized_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_fsrs_parameters_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_fsrs_parameters'))
    )
    op.create_table('vocab_entries',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('term', sa.String(length=32), nullable=False),
    sa.Column('entry_id', sa.BigInteger(), nullable=True),
    sa.Column('pinyin', sa.String(length=128), nullable=True),
    sa.Column('meaning_vi', sa.Text(), nullable=True),
    sa.Column('hsk_level', sa.SmallInteger(), nullable=True),
    sa.Column('hsk_source', sa.String(length=12), server_default='none', nullable=False),
    sa.Column('status', sa.String(length=12), server_default='learning', nullable=False),
    sa.Column('source', sa.String(length=12), nullable=False),
    sa.Column('note', sa.String(length=1000), nullable=True),
    sa.Column('is_starred', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("hsk_source IN ('list', 'derived', 'none')", name=op.f('ck_vocab_entries_hsk_source')),
    sa.CheckConstraint("source IN ('highlight', 'lookup', 'suggestion', 'manual', 'quiz')", name=op.f('ck_vocab_entries_source')),
    sa.CheckConstraint("status IN ('learning', 'known', 'ignored')", name=op.f('ck_vocab_entries_status')),
    sa.CheckConstraint('hsk_level BETWEEN 1 AND 9', name=op.f('ck_vocab_entries_hsk_level')),
    sa.ForeignKeyConstraint(['entry_id'], ['dict_entries.id'], name=op.f('fk_vocab_entries_entry_id_dict_entries'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_vocab_entries_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vocab_entries')),
    sa.UniqueConstraint('user_id', 'term', name=op.f('uq_vocab_entries_user_id_term'))
    )
    op.create_index('ix_vocab_entries_user_id_hsk_level', 'vocab_entries', ['user_id', 'hsk_level'], unique=False)
    op.create_index('ix_vocab_entries_user_id_status', 'vocab_entries', ['user_id', 'status'], unique=False)
    op.create_table('cards',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('vocab_entry_id', sa.BigInteger(), nullable=False),
    sa.Column('card_type', sa.String(length=12), nullable=False),
    sa.Column('state', sa.String(length=12), nullable=False),
    sa.Column('step', sa.SmallInteger(), nullable=True),
    sa.Column('stability', sa.Double(), nullable=True),
    sa.Column('difficulty', sa.Double(), nullable=True),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_review_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reps', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('lapses', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('is_suspended', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("card_type IN ('recognition', 'recall', 'listening')", name=op.f('ck_cards_card_type')),
    sa.CheckConstraint("state IN ('learning', 'review', 'relearning')", name=op.f('ck_cards_state')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_cards_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['vocab_entry_id'], ['vocab_entries.id'], name=op.f('fk_cards_vocab_entry_id_vocab_entries'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cards')),
    sa.UniqueConstraint('vocab_entry_id', 'card_type', name=op.f('uq_cards_vocab_entry_id_card_type'))
    )
    op.create_index('ix_cards_user_id_due_at', 'cards', ['user_id', 'due_at'], unique=False, postgresql_where=sa.text('NOT is_suspended'))
    op.create_table('tts_cache',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('text_sha256', sa.CHAR(length=64), nullable=False),
    sa.Column('voice', sa.String(length=64), nullable=False),
    sa.Column('rate', sa.Numeric(precision=3, scale=2), nullable=False),
    sa.Column('file_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['stored_files.id'], name=op.f('fk_tts_cache_file_id_stored_files'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tts_cache')),
    sa.UniqueConstraint('text_sha256', 'voice', 'rate', name=op.f('uq_tts_cache_text_sha256_voice_rate'))
    )
    op.create_table('review_logs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('card_id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('rating', sa.SmallInteger(), nullable=False),
    sa.Column('state_before', sa.String(length=12), nullable=False),
    sa.Column('stability_before', sa.Double(), nullable=True),
    sa.Column('stability_after', sa.Double(), nullable=True),
    sa.Column('difficulty_before', sa.Double(), nullable=True),
    sa.Column('difficulty_after', sa.Double(), nullable=True),
    sa.Column('due_after', sa.DateTime(timezone=True), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('presentation_id', sa.UUID(), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('rating BETWEEN 1 AND 4', name=op.f('ck_review_logs_rating')),
    sa.ForeignKeyConstraint(['card_id'], ['cards.id'], name=op.f('fk_review_logs_card_id_cards'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_review_logs_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_review_logs')),
    sa.UniqueConstraint('presentation_id', name=op.f('uq_review_logs_presentation_id'))
    )
    op.create_index('ix_review_logs_card_id', 'review_logs', ['card_id'], unique=False)
    op.create_index('ix_review_logs_user_id_reviewed_at', 'review_logs', ['user_id', 'reviewed_at'], unique=False)
    op.create_table('vocab_contexts',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('vocab_entry_id', sa.BigInteger(), nullable=False),
    sa.Column('bubble_id', sa.BigInteger(), nullable=True),
    sa.Column('page_id', sa.BigInteger(), nullable=True),
    sa.Column('sentence_zh', sa.Text(), nullable=False),
    sa.Column('sentence_vi', sa.Text(), nullable=True),
    sa.Column('snippet_file_id', sa.BigInteger(), nullable=True),
    sa.Column('source_label', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['bubble_id'], ['bubbles.id'], name=op.f('fk_vocab_contexts_bubble_id_bubbles'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['page_id'], ['pages.id'], name=op.f('fk_vocab_contexts_page_id_pages'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['snippet_file_id'], ['stored_files.id'], name=op.f('fk_vocab_contexts_snippet_file_id_stored_files'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['vocab_entry_id'], ['vocab_entries.id'], name=op.f('fk_vocab_contexts_vocab_entry_id_vocab_entries'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vocab_contexts')),
    sa.UniqueConstraint('vocab_entry_id', 'bubble_id', name=op.f('uq_vocab_contexts_vocab_entry_id_bubble_id'))
    )
    op.create_index('ix_vocab_contexts_page_id', 'vocab_contexts', ['page_id'], unique=False)
    op.create_index('ix_vocab_contexts_vocab_entry_id', 'vocab_contexts', ['vocab_entry_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_vocab_contexts_vocab_entry_id', table_name='vocab_contexts')
    op.drop_index('ix_vocab_contexts_page_id', table_name='vocab_contexts')
    op.drop_table('vocab_contexts')
    op.drop_index('ix_review_logs_user_id_reviewed_at', table_name='review_logs')
    op.drop_index('ix_review_logs_card_id', table_name='review_logs')
    op.drop_table('review_logs')
    op.drop_table('tts_cache')
    op.drop_index('ix_cards_user_id_due_at', table_name='cards', postgresql_where=sa.text('NOT is_suspended'))
    op.drop_table('cards')
    op.drop_index('ix_vocab_entries_user_id_status', table_name='vocab_entries')
    op.drop_index('ix_vocab_entries_user_id_hsk_level', table_name='vocab_entries')
    op.drop_table('vocab_entries')
    op.drop_table('fsrs_parameters')
    op.drop_index('ix_external_call_logs_service_created_at', table_name='external_call_logs')
    op.drop_table('external_call_logs')
