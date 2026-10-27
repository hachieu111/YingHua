from __future__ import annotations

from collections.abc import Callable, Sequence

from app.modules.auth.application.public import Identity
from app.modules.vocab.application.dto import SavedStatus
from app.modules.vocab.application.ports import VocabUnitOfWork


class GetSavedStatusUseCase:
    """F07.01, F07.11 — Trạng thái "đã lưu" của các từ và câu thoại đang hiển thị (US-NH-31, US-NH-70).

    Giao diện (trình đọc) hỏi lại máy chủ mỗi khi mở trang hoặc quay lại tab, nên dấu "đã lưu" đúng với
    dữ liệu thật cả sau khi tải lại hay khi từ vừa bị xóa ở Sổ tay. Chỉ đọc dữ liệu của chính người gọi;
    từ/bong bóng không thuộc về họ thì không có trong kết quả (không lộ dữ liệu người khác).
    """

    def __init__(self, uow_factory: Callable[[], VocabUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, identity: Identity, terms: Sequence[str], bubble_ids: Sequence[int], page_id: int | None
    ) -> SavedStatus:
        async with self._uow_factory() as uow:
            saved_terms = await uow.entries.existing_terms(identity.user_id, terms)
            page_terms = (
                await uow.entries.terms_with_context_on_page(identity.user_id, page_id, terms)
                if page_id
                else set()
            )
            saved_bubbles = await uow.sentences.saved_bubble_ids(identity.user_id, bubble_ids)
        return SavedStatus(sorted(saved_terms), sorted(page_terms), sorted(saved_bubbles))
