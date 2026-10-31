"""Giao diện (port) mà tầng hạ tầng của M08 phải hiện thực."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from app.core.learning_events import LearningEventPort
from app.modules.admin.application.public import AuditLogRepository
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import AiNoteRequest, EntryFace
from app.modules.review.domain.ai_note import AiExample, AiNote, AiPhrase, CharParts
from app.modules.review.domain.entities import (
    Card,
    CardFilter,
    DeckRef,
    EntrySrsSummary,
    NewCard,
    NewReviewLog,
    Rating,
    ReviewLog,
    SchedulingState,
)
from app.modules.review.domain.fsrs_profile import FsrsProfile, OptimizerLog
from app.modules.stats.application.public import ActivityRecorder


class CardScheduler(Protocol):
    """Bộ lập lịch lặp lại ngắt quãng (FSRS). Domain/application không biết thư viện cụ thể."""

    def new_state(self, now: datetime) -> SchedulingState:
        """Trạng thái của thẻ mới: đến hạn ngay tại `now`."""
        ...

    def review(
        self, state: SchedulingState, rating: Rating, now: datetime, profile: FsrsProfile | None = None
    ) -> SchedulingState:
        """Trạng thái mới (S, D, hạn ôn) sau khi chấm `rating` tại `now`.

        `profile` là tham số riêng của người học (F08.08); None thì dùng tham số mặc định chung.
        """
        ...


class RetrievabilityEstimator(Protocol):
    """Ước lượng xác suất nhớ R của một thẻ tại thời điểm `now` (FSRS)."""

    def retrievability(self, state: SchedulingState, now: datetime) -> float:
        """R trong [0, 1]; thẻ chưa từng ôn có R = 0."""
        ...


class CardRepository(Protocol):
    """Mọi truy vấn lọc theo `user_id` của người đang đăng nhập."""

    async def add_many(self, new_cards: Sequence[NewCard]) -> list[Card]: ...

    async def get(self, user_id: int, card_id: int) -> Card | None: ...

    async def get_for_update(self, user_id: int, card_id: int) -> Card | None:
        """Khóa dòng để hai lượt chấm đồng thời của một thẻ được xử lý tuần tự."""
        ...

    async def save(self, card: Card) -> None:
        """Ghi trạng thái lập lịch, số lượt, cờ tạm ngưng của thẻ."""
        ...

    async def list_due(
        self,
        user_id: int,
        now: datetime,
        limit: int,
        entry_ids: Sequence[int] | None,
        exclude_card_id: int | None,
    ) -> list[Card]:
        """Thẻ đến hạn (`due_at <= now`), không tạm ngưng, thuộc từ "Đang học"; quá hạn lâu nhất trước."""
        ...

    async def count_due(
        self, user_id: int, as_of: datetime, entry_ids: Sequence[int] | None, exclude_card_id: int | None
    ) -> int: ...

    async def next_due_after(self, user_id: int, now: datetime) -> datetime | None:
        """Hạn sớm nhất sau `now` trong các thẻ có thể ôn."""
        ...

    async def count_due_words(self, user_id: int, as_of: datetime) -> int:
        """Số mục từ có ít nhất một thẻ đến hạn (cùng điều kiện với `count_due`)."""
        ...

    async def count_cards(self, user_id: int) -> int:
        """Tổng số thẻ của người học (kể cả đang tạm ngưng)."""
        ...

    async def list_for_entry(self, user_id: int, vocab_entry_id: int) -> list[Card]: ...

    async def list_for_entries(self, user_id: int, vocab_entry_ids: Sequence[int]) -> list[Card]:
        """Thẻ (kể cả đang tạm ngưng) của các mục từ, theo lô."""
        ...

    async def bury_siblings(
        self, user_id: int, vocab_entry_id: int, graded_card_id: int, now: datetime, until: datetime
    ) -> int:
        """Dời các thẻ khác (không tạm ngưng) của cùng mục từ đang đến hạn sang `until`; giữ S, D.

        Trả số thẻ đã dời.
        """
        ...

    async def reschedule_now(self, user_id: int, vocab_entry_ids: Sequence[int], now: datetime) -> int:
        """Đặt `due_at = now`, bỏ tạm ngưng cho mọi thẻ của các mục từ; giữ S, D. Trả số thẻ đã đổi."""
        ...

    async def search(self, flt: CardFilter, offset: int, limit: int) -> tuple[list[Card], int]:
        """Thẻ của `flt.user_id` theo bộ lọc, đến hạn sớm nhất trước, kèm tổng số (F13.07)."""
        ...

    async def summaries_for_entries(
        self, user_id: int, entry_ids: Sequence[int], now: datetime
    ) -> dict[int, EntrySrsSummary]:
        """Tóm tắt thẻ theo lô; mục từ chưa có thẻ không xuất hiện."""
        ...


class ReviewLogRepository(Protocol):
    async def add(self, new_log: NewReviewLog) -> ReviewLog:
        """Raise PresentationIdTakenError nếu mã lượt hiển thị đã có."""
        ...

    async def find_by_presentation(self, presentation_id: uuid.UUID) -> ReviewLog | None: ...

    async def list_for_card(self, card_id: int, offset: int, limit: int) -> tuple[list[ReviewLog], int]:
        """Mới nhất trước."""
        ...

    async def count_between(self, user_id: int, start: datetime, end: datetime) -> int:
        """Số lượt ôn có `start <= reviewed_at < end`."""
        ...

    async def count_for_user(self, user_id: int) -> int:
        """Tổng số lượt ôn của người học."""
        ...

    async def count_recalled_for_user(self, user_id: int) -> int:
        """Số lượt ôn không chọn "Quên" (F12.01)."""
        ...

    async def list_for_optimizer(self, user_id: int, limit: int) -> list[OptimizerLog]:
        """`limit` lượt ôn gần nhất, cũ nhất trước, dùng để tối ưu tham số FSRS (F08.08)."""
        ...


class FsrsProfileRepository(Protocol):
    """Tham số FSRS riêng từng người (F08.08)."""

    async def get(self, user_id: int) -> FsrsProfile | None: ...

    async def save(self, user_id: int, profile: FsrsProfile, review_count: int, now: datetime) -> None:
        """Thêm mới hoặc thay thế; `review_count` là số lượt ôn lúc tối ưu."""
        ...

    async def users_to_optimize(
        self, min_reviews: int, min_new_reviews: int, stale_before: datetime, limit: int
    ) -> list[int]:
        """Người học đủ `min_reviews` lượt ôn và chưa có tham số, hoặc lần tối ưu cuối trước `stale_before`
        và đã có thêm ít nhất `min_new_reviews` lượt ôn mới; tối đa `limit` người,
        ít được tối ưu nhất trước."""
        ...


class FsrsParameterOptimizer(Protocol):
    """Bộ tối ưu tham số FSRS (thư viện `fsrs`). Raise `FsrsOptimizerUnavailableError` khi môi trường thiếu
    phụ thuộc, `InvalidFsrsParametersError` khi kết quả không hợp lệ hoặc làm lịch ôn bất thường."""

    async def optimize(self, logs: Sequence[OptimizerLog]) -> tuple[float, ...]: ...


class VocabCardSource(Protocol):
    """Dữ liệu của M07 mà thẻ cần; M07 hiện thực (M08 không import nội bộ của M07)."""

    async def faces(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, EntryFace]: ...

    async def status_counts(self, user_id: int) -> dict[str, int]:
        """Số mục từ theo trạng thái; luôn đủ ba khóa learning, known, ignored."""
        ...

    async def entry_ids_for_deck(self, user_id: int, deck: DeckRef) -> list[int]:
        """Mã mục từ thuộc bộ thẻ (kể cả từ chưa có ngữ cảnh khi deck là `starred`)."""
        ...


class UserTimezoneSource(Protocol):
    async def timezone_of(self, identity: Identity, owner_id: int) -> str | None:
        """Múi giờ của `owner_id`; `identity` là người gọi (chính chủ hoặc quản trị viên)."""
        ...


class ReviewUnitOfWork(Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    @property
    def cards(self) -> CardRepository: ...

    @property
    def logs(self) -> ReviewLogRepository: ...

    @property
    def vocab(self) -> VocabCardSource: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    @property
    def ai_notes(self) -> AiNoteRepository: ...

    @property
    def fsrs_profiles(self) -> FsrsProfileRepository: ...

    @property
    def activity(self) -> ActivityRecorder: ...

    @property
    def learning(self) -> LearningEventPort: ...

    async def __aenter__(self) -> ReviewUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...


class AiNoteRepository(Protocol):
    """Bộ đệm Thẻ mở rộng AI (F08.11). Quyền sở hữu mục từ do người gọi kiểm trước qua `VocabCardSource`."""

    async def get(self, vocab_entry_id: int) -> AiNote | None: ...

    async def save(self, note: AiNote) -> None:
        """Thêm mới hoặc ghi đè toàn bộ (kể cả `regenerate_count`, `generated_at`)."""
        ...

    async def count_llm_between(self, user_id: int, start: datetime, end: datetime) -> int:
        """Số thẻ nguồn `llm` của người học sinh trong [start, end): dùng cho hạn mức mỗi ngày."""
        ...


class AiNoteGenerator(Protocol):
    """Dịch vụ LLM sinh Thẻ mở rộng (F08.11). Hiện thực chuyển mọi lỗi hạ tầng thành
    `AiNoteGeneratorUnavailableError`; trả JSON đã phân tích hoặc None nếu phản hồi hỏng/bị chặn."""

    async def generate(self, request: AiNoteRequest) -> object: ...


class WordKnowledge(Protocol):
    """Dữ liệu từ điển M06 cho Thẻ mở rộng: chiết tự, câu ví dụ, cụm đi kèm (qua giao diện công khai)."""

    async def char_parts(self, term: str) -> list[CharParts]:
        """Phân rã từng chữ của từ; chữ chưa có dữ liệu thì vắng mặt."""
        ...

    async def examples(self, term: str, max_difficulty: int, limit: int) -> list[AiExample]:
        """Câu ví dụ chứa `term` (Tatoeba có độ khó ≤ `max_difficulty`, rồi ví dụ của mục từ điển)."""
        ...

    async def collocations(self, term: str, limit: int) -> list[AiPhrase]:
        """Từ ghép/cụm ngắn chứa `term` kèm nghĩa ngắn."""
        ...


class SentenceLevelChecker(Protocol):
    """Độ khó câu: cấp HSK cao nhất của các từ trong câu (jieba + bảng HSK); None nếu không xác định."""

    async def difficulties(self, sentences: Sequence[str]) -> list[int | None]: ...


class LearnerProfileSource(Protocol):
    async def profile_of(self, user_id: int) -> tuple[int | None, str | None]:
        """(trình độ HSK đã khai báo, múi giờ) của người học (M02)."""
        ...
