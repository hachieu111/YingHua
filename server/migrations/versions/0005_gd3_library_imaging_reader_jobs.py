"""Giai đoạn 3: stored_files, M03 thư viện, M04 translations/bubbles, M05, M15 và users.avatar_file_id.

Tạo toàn bộ bảng GĐ3 một lần (docs/database-design.md §4.5–4.9, §6.2) để lượt 3b chỉ viết mã.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('guest_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('lookup_count', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_guest_sessions'))
    )
    op.create_index('ix_guest_sessions_expires_at', 'guest_sessions', ['expires_at'], unique=False)
    op.create_table('scheduled_jobs',
    sa.Column('name', sa.String(length=48), nullable=False),
    sa.Column('interval_seconds', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('last_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_status', sa.String(length=12), nullable=True),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locked_by', sa.String(length=64), nullable=True),
    sa.CheckConstraint("last_status IN ('ok', 'failed')", name=op.f('ck_scheduled_jobs_last_status')),
    sa.PrimaryKeyConstraint('name', name=op.f('pk_scheduled_jobs'))
    )
    op.create_table('stored_files',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('storage_key', sa.Text(), nullable=False),
    sa.Column('sha256', sa.CHAR(length=64), nullable=False),
    sa.Column('mime_type', sa.String(length=64), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('width', sa.Integer(), nullable=True),
    sa.Column('height', sa.Integer(), nullable=True),
    sa.Column('owner_id', sa.BigInteger(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('original', 'inpainted', 'rendered', 'snippet', 'cover', 'audio', 'avatar')", name=op.f('ck_stored_files_kind')),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_stored_files_owner_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stored_files')),
    sa.UniqueConstraint('storage_key', name=op.f('uq_stored_files_storage_key'))
    )
    op.create_index('ix_stored_files_expires_at', 'stored_files', ['expires_at'], unique=False, postgresql_where='expires_at IS NOT NULL')
    op.create_index('ix_stored_files_owner_id', 'stored_files', ['owner_id'], unique=False)
    op.create_index('ix_stored_files_sha256', 'stored_files', ['sha256'], unique=False)
    op.create_table('job_runs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('job_name', sa.String(length=48), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=12), server_default='running', nullable=False),
    sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('running', 'ok', 'failed')", name=op.f('ck_job_runs_status')),
    sa.ForeignKeyConstraint(['job_name'], ['scheduled_jobs.name'], name=op.f('fk_job_runs_job_name_scheduled_jobs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_runs'))
    )
    op.create_index('ix_job_runs_job_name', 'job_runs', ['job_name'], unique=False)
    op.create_table('series',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('owner_id', sa.BigInteger(), nullable=True),
    sa.Column('visibility', sa.String(length=8), nullable=False),
    sa.Column('title_vi', sa.String(length=255), nullable=False),
    sa.Column('title_zh', sa.String(length=255), nullable=True),
    sa.Column('author', sa.String(length=255), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('cover_file_id', sa.BigInteger(), nullable=True),
    sa.Column('status', sa.String(length=12), server_default='ongoing', nullable=False),
    sa.Column('est_hsk_level', sa.SmallInteger(), nullable=True),
    sa.Column('created_by', sa.BigInteger(), nullable=True),
    sa.Column('genres', postgresql.ARRAY(sa.String(length=32)), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(visibility = 'public' AND owner_id IS NULL) OR (visibility = 'private' AND owner_id IS NOT NULL)", name=op.f('ck_series_visibility_owner')),
    sa.CheckConstraint("status IN ('ongoing', 'completed')", name=op.f('ck_series_status')),
    sa.CheckConstraint("visibility IN ('public', 'private')", name=op.f('ck_series_visibility')),
    sa.CheckConstraint('est_hsk_level BETWEEN 1 AND 9', name=op.f('ck_series_est_hsk_level')),
    sa.ForeignKeyConstraint(['cover_file_id'], ['stored_files.id'], name=op.f('fk_series_cover_file_id_stored_files'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_series_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_series_owner_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_series'))
    )
    op.create_index('ix_series_owner_id', 'series', ['owner_id'], unique=False)
    op.create_index('ix_series_title_vi_trgm', 'series', ['title_vi'], unique=False, postgresql_using='gin', postgresql_ops={'title_vi': 'gin_trgm_ops'})
    op.create_index('ix_series_title_zh_trgm', 'series', ['title_zh'], unique=False, postgresql_using='gin', postgresql_ops={'title_zh': 'gin_trgm_ops'})
    op.create_index('ix_series_visibility', 'series', ['visibility'], unique=False)
    op.create_table('translations',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('source_file_id', sa.BigInteger(), nullable=True),
    sa.Column('sha256', sa.CHAR(length=64), nullable=False),
    sa.Column('phash', sa.BigInteger(), nullable=True),
    sa.Column('status', sa.String(length=12), server_default='queued', nullable=False),
    sa.Column('pipeline_version', sa.String(length=32), nullable=False),
    sa.Column('attempts', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('worker_id', sa.String(length=64), nullable=True),
    sa.Column('error_step', sa.String(length=32), nullable=True),
    sa.Column('error_message', sa.String(length=1000), nullable=True),
    sa.Column('inpainted_file_id', sa.BigInteger(), nullable=True),
    sa.Column('rendered_file_id', sa.BigInteger(), nullable=True),
    sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('processing_ms', sa.Integer(), nullable=True),
    sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('queued', 'running', 'done', 'failed')", name=op.f('ck_translations_status')),
    sa.ForeignKeyConstraint(['inpainted_file_id'], ['stored_files.id'], name=op.f('fk_translations_inpainted_file_id_stored_files'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['rendered_file_id'], ['stored_files.id'], name=op.f('fk_translations_rendered_file_id_stored_files'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_file_id'], ['stored_files.id'], name=op.f('fk_translations_source_file_id_stored_files'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_translations'))
    )
    op.create_index('ix_translations_phash', 'translations', ['phash'], unique=False)
    op.create_index('ix_translations_sha256', 'translations', ['sha256'], unique=False)
    op.create_index('ix_translations_status_queued_at', 'translations', ['status', 'queued_at'], unique=False)
    op.create_table('bubbles',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('translation_id', sa.BigInteger(), nullable=False),
    sa.Column('idx', sa.SmallInteger(), nullable=False),
    sa.Column('class_name', sa.String(length=16), nullable=False),
    sa.Column('x', sa.Integer(), nullable=False),
    sa.Column('y', sa.Integer(), nullable=False),
    sa.Column('w', sa.Integer(), nullable=False),
    sa.Column('h', sa.Integer(), nullable=False),
    sa.Column('polygon', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('text_zh', sa.Text(), nullable=False),
    sa.Column('pinyin', sa.Text(), nullable=True),
    sa.Column('text_vi', sa.Text(), nullable=True),
    sa.Column('translate_method', sa.String(length=32), nullable=True),
    sa.Column('lines', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('tokens', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('style', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("class_name IN ('speech_bubble', 'sound_effect', 'calligraphy', 'floating_text')", name=op.f('ck_bubbles_class_name')),
    sa.ForeignKeyConstraint(['translation_id'], ['translations.id'], name=op.f('fk_bubbles_translation_id_translations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bubbles')),
    sa.UniqueConstraint('translation_id', 'idx', name=op.f('uq_bubbles_translation_id_idx'))
    )
    op.create_table('chapters',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('series_id', sa.BigInteger(), nullable=False),
    sa.Column('number', sa.Numeric(precision=6, scale=1), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('is_trial', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('number >= 0', name=op.f('ck_chapters_number')),
    sa.ForeignKeyConstraint(['series_id'], ['series.id'], name=op.f('fk_chapters_series_id_series'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chapters')),
    sa.UniqueConstraint('series_id', 'number', name=op.f('uq_chapters_series_id_number'))
    )
    op.create_table('library_items',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('series_id', sa.BigInteger(), nullable=False),
    sa.Column('is_favorite', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['series_id'], ['series.id'], name=op.f('fk_library_items_series_id_series'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_library_items_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'series_id', name=op.f('pk_library_items'))
    )
    op.create_table('series_ratings',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('series_id', sa.BigInteger(), nullable=False),
    sa.Column('stars', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('stars BETWEEN 1 AND 5', name=op.f('ck_series_ratings_stars')),
    sa.ForeignKeyConstraint(['series_id'], ['series.id'], name=op.f('fk_series_ratings_series_id_series'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_series_ratings_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'series_id', name=op.f('pk_series_ratings'))
    )
    op.create_index('ix_series_ratings_series_id', 'series_ratings', ['series_id'], unique=False)
    op.create_table('bubble_edits',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('bubble_id', sa.BigInteger(), nullable=False),
    sa.Column('text_vi', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['bubble_id'], ['bubbles.id'], name=op.f('fk_bubble_edits_bubble_id_bubbles'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bubble_edits_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'bubble_id', name=op.f('pk_bubble_edits'))
    )
    op.create_table('pages',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('chapter_id', sa.BigInteger(), nullable=True),
    sa.Column('owner_id', sa.BigInteger(), nullable=True),
    sa.Column('page_no', sa.SmallInteger(), nullable=False),
    sa.Column('original_file_id', sa.BigInteger(), nullable=True),
    sa.Column('translation_id', sa.BigInteger(), nullable=True),
    sa.Column('width', sa.Integer(), nullable=True),
    sa.Column('height', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('chapter_id IS NOT NULL OR owner_id IS NOT NULL', name=op.f('ck_pages_chapter_or_owner')),
    sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], name=op.f('fk_pages_chapter_id_chapters'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['original_file_id'], ['stored_files.id'], name=op.f('fk_pages_original_file_id_stored_files'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_pages_owner_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['translation_id'], ['translations.id'], name=op.f('fk_pages_translation_id_translations'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pages')),
    sa.UniqueConstraint('chapter_id', 'page_no', name=op.f('uq_pages_chapter_id_page_no'))
    )
    op.create_index('ix_pages_original_file_id', 'pages', ['original_file_id'], unique=False)
    op.create_index('ix_pages_owner_id', 'pages', ['owner_id'], unique=False)
    op.create_index('ix_pages_translation_id', 'pages', ['translation_id'], unique=False)
    op.create_table('reading_progress',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('chapter_id', sa.BigInteger(), nullable=False),
    sa.Column('last_page_no', sa.SmallInteger(), nullable=False),
    sa.Column('mode', sa.String(length=8), server_default='read', nullable=False),
    sa.Column('completed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("mode IN ('read', 'learn')", name=op.f('ck_reading_progress_mode')),
    sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], name=op.f('fk_reading_progress_chapter_id_chapters'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reading_progress_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'chapter_id', name=op.f('pk_reading_progress'))
    )
    op.create_index('ix_reading_progress_user_id_updated_at', 'reading_progress', ['user_id', 'updated_at'], unique=False)
    op.create_table('page_annotations',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('page_id', sa.BigInteger(), nullable=False),
    sa.Column('is_bookmarked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('highlights', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('strokes', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['page_id'], ['pages.id'], name=op.f('fk_page_annotations_page_id_pages'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_page_annotations_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'page_id', name=op.f('pk_page_annotations'))
    )
    op.create_index('ix_page_annotations_user_id_updated_at', 'page_annotations', ['user_id', 'updated_at'], unique=False)
    op.create_table('page_reads',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('page_id', sa.BigInteger(), nullable=False),
    sa.Column('first_read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['page_id'], ['pages.id'], name=op.f('fk_page_reads_page_id_pages'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_page_reads_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'page_id', name=op.f('pk_page_reads'))
    )
    op.add_column('users', sa.Column('avatar_file_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(op.f('fk_users_avatar_file_id_stored_files'), 'users', 'stored_files', ['avatar_file_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint(op.f('fk_users_avatar_file_id_stored_files'), 'users', type_='foreignkey')
    op.drop_column('users', 'avatar_file_id')
    op.drop_table('page_reads')
    op.drop_index('ix_page_annotations_user_id_updated_at', table_name='page_annotations')
    op.drop_table('page_annotations')
    op.drop_index('ix_reading_progress_user_id_updated_at', table_name='reading_progress')
    op.drop_table('reading_progress')
    op.drop_index('ix_pages_translation_id', table_name='pages')
    op.drop_index('ix_pages_owner_id', table_name='pages')
    op.drop_index('ix_pages_original_file_id', table_name='pages')
    op.drop_table('pages')
    op.drop_table('bubble_edits')
    op.drop_index('ix_series_ratings_series_id', table_name='series_ratings')
    op.drop_table('series_ratings')
    op.drop_table('library_items')
    op.drop_table('chapters')
    op.drop_table('bubbles')
    op.drop_index('ix_translations_status_queued_at', table_name='translations')
    op.drop_index('ix_translations_sha256', table_name='translations')
    op.drop_index('ix_translations_phash', table_name='translations')
    op.drop_table('translations')
    op.drop_index('ix_series_visibility', table_name='series')
    op.drop_index('ix_series_title_zh_trgm', table_name='series', postgresql_using='gin', postgresql_ops={'title_zh': 'gin_trgm_ops'})
    op.drop_index('ix_series_title_vi_trgm', table_name='series', postgresql_using='gin', postgresql_ops={'title_vi': 'gin_trgm_ops'})
    op.drop_index('ix_series_owner_id', table_name='series')
    op.drop_table('series')
    op.drop_index('ix_job_runs_job_name', table_name='job_runs')
    op.drop_table('job_runs')
    op.drop_index('ix_stored_files_sha256', table_name='stored_files')
    op.drop_index('ix_stored_files_owner_id', table_name='stored_files')
    op.drop_index('ix_stored_files_expires_at', table_name='stored_files', postgresql_where='expires_at IS NOT NULL')
    op.drop_table('stored_files')
    op.drop_table('scheduled_jobs')
    op.drop_index('ix_guest_sessions_expires_at', table_name='guest_sessions')
    op.drop_table('guest_sessions')
