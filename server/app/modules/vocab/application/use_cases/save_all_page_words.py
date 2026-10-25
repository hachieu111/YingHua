from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.common_chars import is_common_char
from app.core.errors import DomainError
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.dto import FailedWord, SaveAllWordsResult, SaveWordCommand
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.application.use_cases.save_word import SaveWordUseCase
from app.modules.vocab.domain.errors import PageHasNoWordsError
from app.modules.vocab.domain.rules import MAX_BULK_WORDS, collect_page_words

logger = logging.getLogger(__name__)

BULK_ORIGIN = "highlight"  # nguồn có sẵn gần nhất với "lưu từ lúc đọc"; không thêm giá trị enum mới


class SaveAllPageWordsUseCase:
    """F07.12 — Lưu tất cả từ của trang đang đọc mà chưa có trong sổ tay (US-NH-71, F07.01, F07.02).

    Gom từ chữ Hán đã tách của các bong bóng theo thứ tự đọc, bỏ từ đã có (mọi trạng thái; chỉ đếm vào
    `existing`), lấy tối đa 50 từ đầu rồi gọi `SaveWordUseCase` cho từng từ với bong bóng đầu tiên chứa từ —
    MỖI TỪ MỘT GIAO DỊCH RIÊNG nên lỗi một từ không hủy các từ khác. `remaining` là số từ chưa lưu do quá 50.
    Bong bóng chỉ có khi trang đã xử lý xong; trang chưa xong hoặc không có từ → `PageHasNoWordsError`.
    Tất cả từ đã có: trả `saved=[]` (không đổi gì), giao diện hiện thông báo.
    Chỉ bỏ qua từ MỘT chữ rất phổ biến (是, 吗, 的…) và trả trong `skipped`; từ hai chữ trở lên như 什么, 看看
    vẫn lưu vì vẫn đáng học — người học tự đánh dấu "Bỏ qua" nếu không cần (người dùng chốt 25/10/2026).
    """

    def __init__(
        self,
        uow_factory: Callable[[], VocabUnitOfWork],
        pages: PageAccessPort,
        save_word: SaveWordUseCase,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._save_word = save_word

    async def execute(self, identity: Identity, page_id: int) -> SaveAllWordsResult:
        page = await self._pages.get_page(identity, page_id)
        if page.translation_id is None:
            raise PageHasNoWordsError()
        async with self._uow_factory() as uow:
            bubbles = await uow.bubbles.list_by_translation(page.translation_id)
            words = collect_page_words([(b.id, b.idx, b.tokens) for b in bubbles])
            if not words:
                raise PageHasNoWordsError()
            have = await uow.entries.existing_terms(identity.user_id, [term for term, _ in words])
        skipped = [term for term, _ in words if term not in have and _is_common_single_char(term)]
        missing = [(t, b) for t, b in words if t not in have and not _is_common_single_char(t)]
        batch, rest = missing[:MAX_BULK_WORDS], missing[MAX_BULK_WORDS:]
        saved: list[str] = []
        existing = [term for term, _ in words if term in have]
        failed: list[FailedWord] = []
        for term, bubble_id in batch:
            try:
                result = await self._save_word.execute(
                    identity, SaveWordCommand(term, BULK_ORIGIN, bubble_id, page_id)
                )
            except DomainError as exc:
                failed.append(FailedWord(term, exc.code))
                continue
            except Exception:  # lỗi lạ ở một từ không được hủy cả lô
                logger.exception("Lỗi không lường trước khi lưu từ %s của trang %s", term, page_id)
                failed.append(FailedWord(term, "INTERNAL_ERROR"))
                continue
            (saved if result.created else existing).append(term)
        return SaveAllWordsResult(saved, existing, failed, len(rest), skipped)


def _is_common_single_char(term: str) -> bool:
    return len(term) == 1 and is_common_char(term)
