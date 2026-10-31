from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.core.clock import Clock
from app.core.errors import DomainError
from app.core.learning_events import LearningEvent, LearningSource
from app.core.storage import FileStorage, StagedFiles
from app.core.stored_files import FileKind, store_image
from app.modules.auth.application.public import Identity
from app.modules.imaging.application.public import Bubble
from app.modules.library.application.public import PageAccess, PageAccessPort
from app.modules.review.application.public import Card, CreateCardsForEntryUseCase
from app.modules.stats.application.public import ActivityDelta
from app.modules.vocab.application.dto import SaveWordCommand, SaveWordResult
from app.modules.vocab.application.ports import SnippetCropper, TermDictionary, VocabUnitOfWork
from app.modules.vocab.application.views import build_detail
from app.modules.vocab.domain.entities import NewVocabContext, NewVocabEntry, VocabContext, VocabEntry
from app.modules.vocab.domain.errors import (
    BubbleNotFoundError,
    TermNotInBubbleError,
    VocabContextAlreadySavedError,
)
from app.modules.vocab.domain.rules import (
    clean_meaning,
    contains_term,
    normalize_term,
    parse_origin,
    snippet_box,
    source_label,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _BubbleSource:
    bubble: Bubble
    page: PageAccess | None


@dataclass(frozen=True, slots=True)
class _Saved:
    entry: VocabEntry
    created: bool
    context: VocabContext | None
    snippet_missing: bool
    cards: list[Card]


class SaveWordUseCase:
    """F07.01, F07.02, F06.08, F08.09 — Lưu từ vào sổ tay, chống trùng, thêm ngữ cảnh (US-NH-31, US-NH-32).

    Từ mới: tạo mục từ + ngữ cảnh (nếu có bong bóng) + ba thẻ FSRS trong MỘT giao dịch; ảnh ngữ cảnh được cắt
    từ ảnh gốc của trang thành bản sao độc lập, không hết hạn. Từ đã có: chỉ thêm ngữ cảnh khi bong bóng chưa
    có (không tạo thẻ, không đổi lịch ôn); đã có đúng ngữ cảnh đó → `VocabContextAlreadySavedError`. Hai yêu
    cầu đồng thời chỉ tạo một mục nhờ ràng buộc duy nhất (INSERT ... ON CONFLICT DO NOTHING).
    Không cắt được ảnh: vẫn lưu từ kèm câu văn và báo `snippet_missing`.
    Từ mới được tạo thì cộng `words_saved` của ngày, rồi ghi XP (F16.02, khóa là từ), cùng giao dịch (F12.01).
    Từ điển không có nghĩa (kể cả khi từ nằm trong bong bóng): KHÔNG đoán nghĩa từ câu dịch của bong bóng,
    vì câu dịch là nghĩa cả câu chứ không phải nghĩa của từ; `meaning_vi` để null, người học sửa qua PATCH
    (F07.04) và thẻ recall dùng gợi ý dự phòng (F08.03).
    """

    def __init__(
        self,
        uow_factory: Callable[[], VocabUnitOfWork],
        pages: PageAccessPort,
        dictionary: TermDictionary,
        cropper: SnippetCropper,
        create_cards: CreateCardsForEntryUseCase,
        storage: FileStorage,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._dictionary = dictionary
        self._cropper = cropper
        self._create_cards = create_cards
        self._storage = storage
        self._clock = clock

    async def execute(self, identity: Identity, command: SaveWordCommand) -> SaveWordResult:
        term = normalize_term(command.term)
        parse_origin(command.source)
        now = self._clock.now()
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                source = await self._load_source(uow, identity, command, term)
                saved = await self._save(uow, staged, identity.user_id, term, command, source, now)
                if saved.created:
                    await uow.activity.record(identity.user_id, now, ActivityDelta(words_saved=1))
                    word_event = LearningEvent(identity.user_id, LearningSource.WORD_SAVED, term, now)
                    await uow.learning.record(word_event)
                await uow.commit()
                await uow.learning.after_commit()
                detail = await build_detail(uow, self._pages, self._dictionary, identity, saved.entry, now)
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
        return SaveWordResult(detail, saved.created, saved.context, saved.snippet_missing, saved.cards)

    async def _load_source(
        self, uow: VocabUnitOfWork, identity: Identity, command: SaveWordCommand, term: str
    ) -> _BubbleSource | None:
        if command.bubble_id is None:
            return None
        bubble = await uow.bubbles.get(command.bubble_id)
        if bubble is None or not await self._pages.can_read_translation(identity, bubble.translation_id):
            raise BubbleNotFoundError()
        if not contains_term(bubble.text_zh, term):
            raise TermNotInBubbleError()
        if command.page_id is None:
            page = await self._pages.readable_page_for_translation(identity, bubble.translation_id)
            return _BubbleSource(bubble, page)
        page = await self._pages.get_page(identity, command.page_id)
        if page.translation_id != bubble.translation_id:
            raise BubbleNotFoundError()
        return _BubbleSource(bubble, page)

    async def _save(
        self,
        uow: VocabUnitOfWork,
        staged: StagedFiles,
        user_id: int,
        term: str,
        command: SaveWordCommand,
        source: _BubbleSource | None,
        now: datetime,
    ) -> _Saved:
        entry = await uow.entries.get_by_term(user_id, term)
        cards: list[Card] = []
        created = False
        if entry is None:
            entry = await self._create_entry(uow, user_id, term, command, source, now)
            if entry is not None:
                created = True
                cards = await self._create_cards.execute(uow.cards, user_id, entry.id, now)
            else:  # yêu cầu đồng thời khác vừa tạo mục này: coi như từ đã có
                entry = await uow.entries.get_by_term(user_id, term)
        assert entry is not None
        if source is None:
            return _Saved(entry, created, None, False, cards)
        if not created and await uow.contexts.has_bubble(entry.id, source.bubble.id):
            raise VocabContextAlreadySavedError(details={"vocab_entry_id": entry.id})
        file_id = await self._make_snippet(uow, staged, user_id, source, now)
        context = await uow.contexts.add_if_absent(_new_context(entry.id, source, file_id, now))
        if context is None:
            raise VocabContextAlreadySavedError(details={"vocab_entry_id": entry.id})
        return _Saved(entry, created, context, file_id is None, cards)

    async def _create_entry(
        self,
        uow: VocabUnitOfWork,
        user_id: int,
        term: str,
        command: SaveWordCommand,
        source: _BubbleSource | None,
        now: datetime,
    ) -> VocabEntry | None:
        info = await self._dictionary.describe(term)
        return await uow.entries.add_if_absent(
            NewVocabEntry(
                user_id=user_id,
                term=term,
                origin=parse_origin(command.source),
                hsk_source=info.hsk_source,
                created_at=now,
                entry_id=info.entry_id,
                pinyin=_token_pinyin(source, term) or info.pinyin,
                meaning_vi=clean_meaning(command.meaning_vi) or info.meaning_vi,
                hsk_level=info.hsk_level,
            )
        )

    async def _make_snippet(
        self, uow: VocabUnitOfWork, staged: StagedFiles, user_id: int, source: _BubbleSource, now: datetime
    ) -> int | None:
        """Cắt và lưu ảnh ngữ cảnh; lỗi đọc/cắt chỉ làm thiếu ảnh (F07.01), không hủy việc lưu từ."""
        page, bubble = source.page, source.bubble
        if page is None or page.original_file_id is None:
            return None
        original = await uow.files.get(page.original_file_id)
        if original is None or original.removed_at is not None:
            return None
        box = snippet_box(bubble.x, bubble.y, bubble.w, bubble.h, original.width or 0, original.height or 0)
        if box is None:
            logger.warning("Khung cắt ảnh ngữ cảnh không hợp lệ cho bong bóng %s", bubble.id)
            return None
        try:
            upload = await self._cropper.crop(await self._storage.read(original.storage_key), box)
            stored = await store_image(staged, uow.files, upload, FileKind.SNIPPET, user_id, now)
        except (DomainError, OSError, ValueError) as exc:
            logger.warning(
                "Không cắt được ảnh ngữ cảnh của bong bóng %s: %s", bubble.id, exc.__class__.__name__
            )
            return None
        return stored.id


def _token_pinyin(source: _BubbleSource | None, term: str) -> str | None:
    """Pinyin của từ theo dữ liệu tách sẵn của bong bóng (chính xác hơn tra rời)."""
    if source is None:
        return None
    for token in source.bubble.tokens:
        if isinstance(token, dict) and token.get("word") == term and token.get("pinyin"):
            return str(token["pinyin"])
    return None


def _new_context(entry_id: int, source: _BubbleSource, file_id: int | None, now: datetime) -> NewVocabContext:
    page, bubble = source.page, source.bubble
    return NewVocabContext(
        vocab_entry_id=entry_id,
        sentence_zh=bubble.text_zh,
        created_at=now,
        bubble_id=bubble.id,
        page_id=page.page_id if page else None,
        sentence_vi=bubble.text_vi,
        snippet_file_id=file_id,
        source_label=source_label(page.series_title, page.chapter_number, page.page_no) if page else None,
    )
