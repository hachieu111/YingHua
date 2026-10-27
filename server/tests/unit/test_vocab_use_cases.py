"""M07 — use case với repository giả: F07.01–F07.07, F08.09 (không cần CSDL, mạng hay Pillow thật)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from itertools import count
from typing import Any

import pytest

from app.core.errors import ExternalServiceError
from app.core.image_validation import ImageInfo, ImageUpload
from app.core.stored_files import FileKind, NewStoredFile, StoredFile
from app.modules.imaging.domain.entities import Bubble
from app.modules.library.application.dto import PageAccess, SeriesRef
from app.modules.review.application.use_cases.create_cards_for_entry import CreateCardsForEntryUseCase
from app.modules.review.infrastructure.fsrs_scheduler import FsrsScheduler
from app.modules.vocab.application.dto import SaveWordCommand
from app.modules.vocab.application.ports import TermInfo
from app.modules.vocab.application.use_cases.delete_context import DeleteContextUseCase
from app.modules.vocab.application.use_cases.delete_vocab import DeleteVocabUseCase
from app.modules.vocab.application.use_cases.list_decks import ListDecksUseCase
from app.modules.vocab.application.use_cases.save_word import SaveWordUseCase
from app.modules.vocab.application.use_cases.update_vocab import UpdateVocabUseCase
from app.modules.vocab.domain.entities import (
    ContextSummary,
    CropBox,
    NewVocabContext,
    NewVocabEntry,
    VocabContext,
    VocabEntry,
    VocabStatus,
)
from app.modules.vocab.domain.errors import (
    BubbleNotFoundError,
    InvalidTermError,
    InvalidVocabFieldError,
    InvalidVocabSourceError,
    InvalidVocabStatusError,
    NoteTooLongError,
    TermNotInBubbleError,
    VocabContextAlreadySavedError,
    VocabContextNotFoundError,
    VocabNotFoundError,
)
from tests.conftest import FixedClock
from tests.unit.activity_fakes import FakeActivity
from tests.unit.review_fakes import FakeAudit, FakeCards, identity

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
ORIGINAL_KEY = "original/aa/original.png"


class FakeEntries:
    def __init__(self) -> None:
        self.items: dict[int, VocabEntry] = {}
        self.lose_race_once = False
        self._ids = count(1)

    async def get(self, user_id: int, entry_id: int) -> VocabEntry | None:
        entry = self.items.get(entry_id)
        return entry if entry and entry.user_id == user_id else None

    async def get_many(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, VocabEntry]:
        return {i: e for i, e in self.items.items() if i in entry_ids and e.user_id == user_id}

    async def get_by_term(self, user_id: int, term: str) -> VocabEntry | None:
        return next((e for e in self.items.values() if e.user_id == user_id and e.term == term), None)

    async def add_if_absent(self, new_entry: NewVocabEntry) -> VocabEntry | None:
        if self.lose_race_once:  # yêu cầu đồng thời khác vừa tạo mục này
            self.lose_race_once = False
            self._insert(new_entry)
            return None
        if await self.get_by_term(new_entry.user_id, new_entry.term):
            return None
        return self._insert(new_entry)

    def _insert(self, n: NewVocabEntry) -> VocabEntry:
        entry = VocabEntry(
            id=next(self._ids),
            user_id=n.user_id,
            term=n.term,
            status=VocabStatus.LEARNING,
            origin=n.origin,
            hsk_source=n.hsk_source,
            created_at=n.created_at,
            updated_at=n.created_at,
            entry_id=n.entry_id,
            pinyin=n.pinyin,
            meaning_vi=n.meaning_vi,
            hsk_level=n.hsk_level,
        )
        self.items[entry.id] = entry
        return entry

    async def update(self, entry: VocabEntry) -> None:
        self.items[entry.id] = entry

    async def delete(self, user_id: int, entry_id: int) -> None:
        self.items.pop(entry_id, None)

    async def starred_ids(self, user_id: int) -> list[int]:
        return [e.id for e in self.items.values() if e.user_id == user_id and e.is_starred]


class FakeContexts:
    def __init__(self) -> None:
        self.items: dict[int, VocabContext] = {}
        self._ids = count(1)

    async def add_if_absent(self, n: NewVocabContext) -> VocabContext | None:
        if n.bubble_id is not None and await self.has_bubble(n.vocab_entry_id, n.bubble_id):
            return None
        ctx = VocabContext(
            id=next(self._ids),
            vocab_entry_id=n.vocab_entry_id,
            sentence_zh=n.sentence_zh,
            created_at=n.created_at,
            bubble_id=n.bubble_id,
            page_id=n.page_id,
            sentence_vi=n.sentence_vi,
            snippet_file_id=n.snippet_file_id,
            source_label=n.source_label,
        )
        self.items[ctx.id] = ctx
        return ctx

    async def has_bubble(self, vocab_entry_id: int, bubble_id: int) -> bool:
        return any(
            c.vocab_entry_id == vocab_entry_id and c.bubble_id == bubble_id for c in self.items.values()
        )

    async def list_for_entry(self, vocab_entry_id: int) -> list[VocabContext]:
        rows = [c for c in self.items.values() if c.vocab_entry_id == vocab_entry_id]
        return sorted(rows, key=lambda c: c.id, reverse=True)

    async def get(self, vocab_entry_id: int, context_id: int) -> VocabContext | None:
        ctx = self.items.get(context_id)
        return ctx if ctx and ctx.vocab_entry_id == vocab_entry_id else None

    async def delete(self, context_id: int) -> None:
        self.items.pop(context_id, None)

    async def summaries(self, entry_ids: Sequence[int]) -> dict[int, ContextSummary]:
        result: dict[int, ContextSummary] = {}
        for entry_id in entry_ids:
            rows = await self.list_for_entry(entry_id)
            if rows:
                result[entry_id] = ContextSummary(len(rows), rows[0])
        return result

    async def snippet_file_ids(self, vocab_entry_id: int) -> list[int]:
        rows = await self.list_for_entry(vocab_entry_id)
        return [c.snippet_file_id for c in rows if c.snippet_file_id is not None]

    async def page_links(self, user_id: int) -> list[tuple[int, int]]:
        return [(c.vocab_entry_id, c.page_id) for c in self.items.values() if c.page_id is not None]

    async def entry_ids_for_pages(self, user_id: int, page_ids: Sequence[int]) -> list[int]:
        return sorted({c.vocab_entry_id for c in self.items.values() if c.page_id in page_ids})


class FakeFiles:
    def __init__(self) -> None:
        self.items: dict[int, StoredFile] = {}
        self._ids = count(100)
        self.items[1] = StoredFile(
            1, FileKind.ORIGINAL, ORIGINAL_KEY, "0" * 64, "image/png", 10, NOW, width=200, height=300
        )

    async def add(self, new_file: NewStoredFile) -> StoredFile:
        stored = StoredFile(
            id=next(self._ids),
            kind=new_file.kind,
            storage_key=new_file.storage_key,
            sha256=new_file.sha256,
            mime_type=new_file.mime_type,
            size_bytes=new_file.size_bytes,
            created_at=new_file.created_at,
            width=new_file.width,
            height=new_file.height,
            owner_id=new_file.owner_id,
            expires_at=new_file.expires_at,
        )
        self.items[stored.id] = stored
        return stored

    async def get(self, file_id: int) -> StoredFile | None:
        return self.items.get(file_id)

    async def delete_many(self, file_ids: Sequence[int]) -> list[str]:
        return [self.items.pop(i).storage_key for i in file_ids if i in self.items]


class FakeBubbles:
    def __init__(self, bubbles: list[Bubble]) -> None:
        self._items = {b.id: b for b in bubbles}

    async def get(self, bubble_id: int) -> Bubble | None:
        return self._items.get(bubble_id)


class FakeVocabUow:
    def __init__(self, bubbles: list[Bubble]) -> None:
        self.entries = FakeEntries()
        self.contexts = FakeContexts()
        self.cards = FakeCards()
        self.files = FakeFiles()
        self.bubbles = FakeBubbles(bubbles)
        self.audit = FakeAudit()
        self.activity = FakeActivity()
        self.commits = 0

    async def __aenter__(self) -> FakeVocabUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {ORIGINAL_KEY: b"original-image"}
        self._ids = count(1)

    async def save(self, data: bytes, folder: str, extension: str) -> str:
        key = f"{folder}/{next(self._ids)}.{extension}"
        self.files[key] = data
        return key

    async def read(self, key: str) -> bytes:
        return self.files[key]

    async def delete(self, key: str) -> None:
        self.files.pop(key, None)


class FakePages:
    def __init__(self) -> None:
        self.page = PageAccess(
            page_id=7,
            page_no=3,
            translation_id=50,
            original_file_id=1,
            width=200,
            height=300,
            can_edit=False,
            chapter_id=4,
            chapter_number=Decimal("2.0"),
            series_id=9,
            series_title="Hoa Hồng",
        )
        self.readable = True

    async def can_read_translation(self, identity: object, translation_id: int) -> bool:
        return self.readable and translation_id == 50

    async def get_page(self, identity: object, page_id: int, *, require_edit: bool = False) -> PageAccess:
        return self.page

    async def readable_page_for_translation(self, identity: object, translation_id: int) -> PageAccess | None:
        return self.page

    async def describe_pages(self, identity: object, page_ids: Sequence[int]) -> list[PageAccess]:
        return [self.page] if self.page.page_id in page_ids else []

    async def series_of_pages(self, identity: object, page_ids: Sequence[int]) -> dict[int, SeriesRef]:
        return {7: SeriesRef(9, "Hoa Hồng")} if 7 in page_ids else {}

    async def page_ids_of_series(self, series_id: int) -> list[int]:
        return [7] if series_id == 9 else []


class FakeDictionary:
    async def describe(self, term: str) -> TermInfo:
        return TermInfo(entry_id=5, pinyin="nǐ hǎo", meaning_vi="xin chào", hsk_level=1, hsk_source="list")

    async def sino_vietnamese(self, terms: Sequence[str]) -> dict[str, str]:
        return {t: "nhĩ hảo" for t in terms}


class FakeCropper:
    def __init__(self) -> None:
        self.boxes: list[CropBox] = []
        self.error: Exception | None = None

    async def crop(self, image: bytes, box: CropBox) -> ImageUpload:
        if self.error:
            raise self.error
        self.boxes.append(box)
        info = ImageInfo("image/png", "png", "f" * 64, 4, 10, 10)
        return ImageUpload(b"snip", info)


def _bubble(bubble_id: int = 11, text: str = "你好吗") -> Bubble:
    return Bubble(
        id=bubble_id,
        translation_id=50,
        idx=bubble_id,
        class_name="speech_bubble",
        x=50,
        y=60,
        w=40,
        h=30,
        text_zh=text,
        pinyin="nǐ hǎo ma",
        text_vi="Bạn khỏe không",
        tokens=[{"word": "你好", "pinyin": "nǐ hǎo", "entry_id": None}],
    )


class Env:
    def __init__(self) -> None:
        self.uow = FakeVocabUow([_bubble(11), _bubble(12, "你好，再见")])
        self.pages = FakePages()
        self.storage = FakeStorage()
        self.cropper = FakeCropper()
        self.clock = FixedClock(NOW)
        self.dictionary = FakeDictionary()
        self.save = SaveWordUseCase(
            lambda: self.uow,
            self.pages,
            self.dictionary,
            self.cropper,
            CreateCardsForEntryUseCase(FsrsScheduler(enable_fuzzing=False)),
            self.storage,
            self.clock,
        )


def _cmd(term: str = "你好", bubble_id: int | None = 11, source: str = "highlight") -> SaveWordCommand:
    return SaveWordCommand(term=term, source=source, bubble_id=bubble_id)


async def test_save_new_word_creates_entry_context_snippet_and_three_cards_in_one_transaction() -> None:
    """F07.01, F08.09, US-NH-31: mục từ + ngữ cảnh + ảnh cắt + 3 thẻ, một giao dịch."""
    env = Env()
    result = await env.save.execute(identity(), _cmd())
    assert result.created and result.context is not None and not result.snippet_missing
    entry = result.detail.entry
    assert (entry.term, entry.status, entry.hsk_level, entry.hsk_source) == (
        "你好",
        VocabStatus.LEARNING,
        1,
        "list",
    )
    assert entry.pinyin == "nǐ hǎo" and entry.meaning_vi == "xin chào"
    assert len(result.cards) == 3 and len(env.uow.cards.items) == 3
    assert all(c.schedule.due_at == NOW for c in env.uow.cards.items.values())
    ctx = result.context
    assert (ctx.sentence_zh, ctx.sentence_vi, ctx.page_id) == ("你好吗", "Bạn khỏe không", 7)
    assert ctx.source_label == "Hoa Hồng · Chương 2 · Trang 3"
    snippet = env.uow.files.items[ctx.snippet_file_id or 0]
    assert snippet.kind is FileKind.SNIPPET and snippet.owner_id == 1 and snippet.expires_at is None
    assert env.uow.commits == 1
    # Khung cắt có lề quanh bong bóng (50,60,40x30) và nằm trong ảnh 200x300.
    box = env.cropper.boxes[0]
    assert box.left < 50 and box.top < 60 and box.right > 90 and box.bottom > 90
    assert box.left >= 0 and box.right <= 200 and box.bottom <= 300


async def test_save_again_with_new_bubble_adds_context_without_new_cards() -> None:
    """F07.02, US-NH-32: lưu lại từ đã có chỉ thêm ngữ cảnh, không tạo thẻ, không đổi lịch ôn."""
    env = Env()
    first = await env.save.execute(identity(), _cmd(bubble_id=11))
    schedules = {i: c.schedule for i, c in env.uow.cards.items.items()}
    second = await env.save.execute(identity(), _cmd(bubble_id=12))
    assert not second.created and second.context is not None and second.cards == []
    assert second.detail.entry.id == first.detail.entry.id
    assert len(env.uow.entries.items) == 1 and len(env.uow.contexts.items) == 2
    assert len(env.uow.cards.items) == 3
    assert {i: c.schedule for i, c in env.uow.cards.items.items()} == schedules
    assert len(second.detail.contexts) == 2


async def test_save_same_bubble_twice_reports_context_already_saved() -> None:
    env = Env()
    await env.save.execute(identity(), _cmd())
    with pytest.raises(VocabContextAlreadySavedError) as caught:
        await env.save.execute(identity(), _cmd())
    assert caught.value.code == "VOCAB_CONTEXT_ALREADY_SAVED"
    assert len(env.uow.contexts.items) == 1 and len(env.uow.cards.items) == 3
    assert len(env.storage.files) == 2  # ảnh gốc + đúng một ảnh cắt, không có ảnh mồ côi


async def test_concurrent_double_save_creates_one_entry_and_one_card_set() -> None:
    """F07.02: hai lần bấm nhanh chỉ một mục — yêu cầu thua cuộc đua coi như từ đã có."""
    env = Env()
    env.uow.entries.lose_race_once = True
    result = await env.save.execute(identity(), _cmd())
    assert not result.created and result.cards == [] and len(env.uow.cards.items) == 0
    assert len(env.uow.entries.items) == 1


async def test_save_without_bubble_creates_entry_and_cards_but_no_context() -> None:
    """F07.01: nguồn lookup/manual không có ngữ cảnh; lưu lại không đổi gì."""
    env = Env()
    first = await env.save.execute(identity(), _cmd(bubble_id=None, source="lookup"))
    assert first.created and first.context is None and len(first.cards) == 3
    assert first.detail.contexts == []
    again = await env.save.execute(identity(), _cmd(bubble_id=None, source="lookup"))
    assert not again.created and again.context is None and len(env.uow.cards.items) == 3


async def test_save_uses_bubble_token_pinyin_and_manual_meaning() -> None:
    env = Env()
    result = await env.save.execute(
        identity(), SaveWordCommand("你好", "manual", bubble_id=11, meaning_vi="  chào bạn ")
    )
    assert result.detail.entry.pinyin == "nǐ hǎo" and result.detail.entry.meaning_vi == "chào bạn"


async def test_save_when_snippet_cannot_be_cut_still_saves_word_with_sentence() -> None:
    """F07.01 ngoại lệ: không cắt được ảnh vẫn lưu từ kèm câu văn và báo thiếu ảnh."""
    env = Env()
    env.cropper.error = ExternalServiceError()
    result = await env.save.execute(identity(), _cmd())
    assert result.created and result.snippet_missing
    assert result.context is not None and result.context.snippet_file_id is None
    assert result.context.sentence_zh == "你好吗"


async def test_save_rolls_back_and_removes_snippet_file_when_card_creation_fails() -> None:
    """F08.09 ngoại lệ: lỗi tạo thẻ hủy cả giao dịch, ảnh cắt mồ côi bị dọn."""
    env = Env()

    class Boom(CreateCardsForEntryUseCase):
        async def execute(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("lỗi tạo thẻ")

    env.save._create_cards = Boom(FsrsScheduler())
    with pytest.raises(RuntimeError):
        await env.save.execute(identity(), _cmd())
    assert env.uow.commits == 0
    assert set(env.storage.files) == {ORIGINAL_KEY}


async def test_save_validates_term_source_and_bubble() -> None:
    env = Env()
    for bad in ("", "   ", "hello", "x" * 33 + "你"):
        with pytest.raises(InvalidTermError):
            await env.save.execute(identity(), _cmd(term=bad))
    with pytest.raises(InvalidVocabSourceError):
        await env.save.execute(identity(), _cmd(source="khác"))
    with pytest.raises(TermNotInBubbleError):
        await env.save.execute(identity(), _cmd(term="再见"))
    with pytest.raises(BubbleNotFoundError):
        await env.save.execute(identity(), _cmd(bubble_id=999))
    env.pages.readable = False
    with pytest.raises(BubbleNotFoundError):
        await env.save.execute(identity(), _cmd())
    assert env.uow.entries.items == {}


async def _saved(env: Env, bubble_id: int = 11) -> VocabEntry:
    return (await env.save.execute(identity(), _cmd(bubble_id=bubble_id))).detail.entry


def _update(env: Env) -> UpdateVocabUseCase:
    return UpdateVocabUseCase(lambda: env.uow, env.pages, env.dictionary, env.clock, note_max_chars=1000)


async def test_update_status_note_meaning_and_star() -> None:
    """F07.03, F07.04, US-NH-33, US-NH-34."""
    env = Env()
    entry = await _saved(env)
    detail = await _update(env).execute(
        identity(),
        entry.id,
        {"status": "known", "note": "  mẹo <b>nhớ</b>  ", "is_starred": True, "meaning_vi": "chào"},
    )
    assert detail.entry.status is VocabStatus.KNOWN and detail.entry.note == "mẹo <b>nhớ</b>"
    assert detail.entry.is_starred and detail.entry.meaning_vi == "chào"
    cleared = await _update(env).execute(identity(), entry.id, {"note": ""})
    assert cleared.entry.note is None and cleared.entry.status is VocabStatus.KNOWN
    back = await _update(env).execute(identity(), entry.id, {"status": "learning"})
    assert back.entry.status is VocabStatus.LEARNING


async def test_update_rejects_bad_values_and_other_users() -> None:
    env = Env()
    entry = await _saved(env)
    with pytest.raises(InvalidVocabStatusError):
        await _update(env).execute(identity(), entry.id, {"status": "mastered"})
    with pytest.raises(NoteTooLongError):
        await _update(env).execute(identity(), entry.id, {"note": "a" * 1001})
    assert (await _update(env).execute(identity(), entry.id, {"note": "a" * 1000})).entry.note == "a" * 1000
    with pytest.raises(InvalidVocabFieldError):
        await _update(env).execute(identity(), entry.id, {"term": "改"})
    with pytest.raises(InvalidVocabFieldError):
        await _update(env).execute(identity(), entry.id, {"is_starred": "yes"})
    with pytest.raises(VocabNotFoundError):
        await _update(env).execute(identity(2), entry.id, {"note": "x"})


async def test_delete_context_keeps_entry_and_cards_even_for_last_context() -> None:
    """F07.05, US-NH-35 TC3: xóa ngữ cảnh cuối cùng thì từ vẫn còn, ảnh cắt bị xóa."""
    env = Env()
    entry = await _saved(env)
    await _saved(env, bubble_id=12)
    delete = DeleteContextUseCase(lambda: env.uow, env.storage, env.clock)
    for context in list(env.uow.contexts.items.values()):
        await delete.execute(identity(), entry.id, context.id)
    assert entry.id in env.uow.entries.items and len(env.uow.cards.items) == 3
    assert env.uow.contexts.items == {}
    assert set(env.storage.files) == {ORIGINAL_KEY}
    with pytest.raises(VocabContextNotFoundError):
        await delete.execute(identity(), entry.id, 12345)
    with pytest.raises(VocabNotFoundError):
        await delete.execute(identity(2), entry.id, 1)


async def test_delete_vocab_removes_snippet_files_and_allows_fresh_start() -> None:
    """F07.06, US-NH-36: xóa từ gỡ ảnh cắt; lưu lại sau đó là từ mới với đủ 3 thẻ."""
    env = Env()
    entry = await _saved(env)
    with pytest.raises(VocabNotFoundError):
        await DeleteVocabUseCase(lambda: env.uow, env.storage, env.clock).execute(identity(2), entry.id)
    await DeleteVocabUseCase(lambda: env.uow, env.storage, env.clock).execute(identity(), entry.id)
    assert env.uow.entries.items == {} and set(env.storage.files) == {ORIGINAL_KEY}
    env.uow.cards.items.clear()  # ON DELETE CASCADE ở CSDL thật
    env.uow.contexts.items.clear()
    again = await env.save.execute(identity(), _cmd())
    assert again.created and len(again.cards) == 3


async def test_list_decks_groups_by_series_and_includes_starred_deck() -> None:
    """F07.07, F08.01: bộ thẻ theo truyện và bộ "Từ đánh dấu sao"."""
    env = Env()
    entry = await _saved(env)
    await env.save.execute(identity(), _cmd(term="再见", bubble_id=12))
    await _update(env).execute(identity(), entry.id, {"is_starred": True})
    decks = await ListDecksUseCase(lambda: env.uow, env.pages, env.clock).execute(identity())
    by_key = {d.key: d for d in decks.items}
    assert by_key["starred"].word_count == 1 and by_key["starred"].title == "Từ đánh dấu sao"
    series = by_key["series:9"]
    assert (series.title, series.word_count, series.reviewed_count, series.due_count) == ("Hoa Hồng", 2, 0, 6)
    # Từ chuyển sang "Đã thuộc" thì thẻ không còn tính là đến hạn.
    await _update(env).execute(identity(), entry.id, {"status": "known"})
    again = {
        d.key: d
        for d in (await ListDecksUseCase(lambda: env.uow, env.pages, env.clock).execute(identity())).items
    }
    assert again["series:9"].due_count == 3 and again["series:9"].word_count == 2
