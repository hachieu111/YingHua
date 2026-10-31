"""Giao diện (port) mà tầng hạ tầng của M09 phải hiện thực."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.core.learning_events import LearningEventPort
from app.modules.admin.application.public import AuditLogRepository
from app.modules.auth.application.public import Identity
from app.modules.quiz.domain.entities import (
    DistractorCandidate,
    ExampleRow,
    GradedAnswer,
    MistakeReview,
    NewQuestion,
    NewQuiz,
    Quiz,
    QuizQuestion,
    QuizWord,
    RelatedCandidate,
    WordContext,
)
from app.modules.review.application.public import CardRepository
from app.modules.stats.application.public import ActivityRecorder
from app.modules.vocab.application.public import SaveWordCommand, SaveWordResult


@dataclass(frozen=True, slots=True)
class GenerationItem:
    """Dữ liệu một từ gửi cho LLM — chỉ từ, pinyin, nghĩa (security.md: không gửi thông tin người dùng)."""

    term: str
    pinyin: str | None
    meaning: str | None
    hsk_level: int | None = None


@dataclass(frozen=True, slots=True)
class QuizGenerationRequest:
    items: Sequence[GenerationItem]
    question_count: int
    learner_level: int | None = None  # chỉ là một con số, không định danh người học


@dataclass(frozen=True, slots=True)
class MistakeReviewRequest:
    """Dữ liệu gửi LLM để giải thích một câu sai: từ, pinyin, nghĩa, cấp HSK, hai lựa chọn liên quan và trình
    độ (một con số). Không có email, tên, mã người dùng, ngữ cảnh hay ghi chú riêng (security.md)."""

    term: str
    pinyin: str | None
    meaning: str | None
    hsk_level: int | None
    chosen: str | None  # None: người học bỏ trống câu này
    correct: str
    learner_level: int | None = None


@dataclass(frozen=True, slots=True)
class ExternalCall:
    """Một lần gọi dịch vụ ngoài để ghi nhật ký (không chứa nội dung, không chứa khóa)."""

    provider: str
    operation: str
    status: str  # ok | timeout | invalid | error
    latency_ms: int
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class LearnerProfile:
    hsk_level: int | None
    timezone: str | None


@dataclass(frozen=True, slots=True)
class EntryRef:
    """Mục từ sổ tay hiện tại của một câu hỏi (có thể đã đổi trạng thái sau khi ra đề)."""

    entry_id: int
    term: str
    status: str  # learning | known | ignored


class ExampleSource(Protocol):
    """Câu ví dụ Tatoeba của M06 kèm độ khó đã tính (F09.09)."""

    async def find(self, term: str, max_difficulty: int, limit: int) -> list[ExampleRow]:
        """Câu ví dụ của từ có `difficulty_level <= max_difficulty` (chưa tính độ khó thì không được chọn)."""
        ...

    async def get_many(self, example_ids: Sequence[int]) -> dict[int, ExampleRow]: ...

    async def sample_translations(self, difficulty: int, exclude_ids: Sequence[int], limit: int) -> list[str]:
        """Bản dịch Việt của các câu Tatoeba khác có cùng độ khó, làm phương án nhiễu."""
        ...


class ExampleLevelChecker(Protocol):
    """Độ khó câu do LLM viết: cấp HSK cao nhất của các từ trong câu (jieba + bảng HSK)."""

    async def difficulties(self, sentences: Sequence[str]) -> list[int | None]: ...


class ExternalCallLog(Protocol):
    async def record(self, call: ExternalCall) -> None:
        """Lỗi ghi nhật ký không được làm hỏng việc chính."""
        ...


class RelatedCandidateSource(Protocol):
    """Ứng viên từ mở rộng gắn với từ đã lưu (F09.09). Hiện thực ghép dữ liệu của M03/M04/M06/M07/M10 qua
    giao diện công khai của từng module."""

    async def candidates(
        self, user_id: int, saved: Sequence[QuizWord], learner_level: int | None
    ) -> list[RelatedCandidate]:
        """Đã lọc: cấp HSK trong giới hạn, có nghĩa ngắn, có câu ví dụ đạt độ khó, chưa có trong sổ tay
        và không nằm trong danh sách gợi ý đã bỏ qua."""
        ...


class WordSaver(Protocol):
    """Lưu từ vào sổ tay: `SaveWordUseCase` của M07 (F07.01)."""

    async def execute(self, identity: Identity, command: SaveWordCommand) -> SaveWordResult: ...


class QuizGenerator(Protocol):
    """Dịch vụ sinh đề (LLM, F09.06). Hiện thực chuyển mọi lỗi hạ tầng thành `QuizGeneratorUnavailableError`.

    Trả về JSON đã phân tích (hoặc bất kỳ giá trị nào nếu không phân tích được): kiểm tra lược đồ do
    `validate_llm_payload` đảm nhiệm, nên một đề sai cấu trúc không bao giờ vào CSDL.
    """

    async def generate(self, request: QuizGenerationRequest) -> object: ...


class MistakeReviewGenerator(Protocol):
    """Dịch vụ giải thích lỗi sai (LLM, F09.10). Hiện thực chuyển mọi lỗi hạ tầng thành
    `QuizGeneratorUnavailableError`. Trả JSON đã phân tích (hoặc `None` nếu không đọc được); kiểm lược đồ do
    `domain.mistake_review` đảm nhiệm."""

    async def generate(self, request: MistakeReviewRequest) -> object: ...


class TermFactsSource(Protocol):
    """Dữ liệu từ điển của một từ (M06), để giải thích được cả từ đã bị xóa khỏi sổ tay."""

    async def facts(self, term: str) -> QuizWord | None:
        """Pinyin, nghĩa ngắn và cấp HSK (`entry_id` = 0); None nếu từ điển không có từ này."""
        ...


class DistractorSource(Protocol):
    """Từ HSK ngẫu nhiên làm phương án nhiễu cho đề dự phòng (F09.08)."""

    async def sample(self, level: int, limit: int, exclude: Sequence[str]) -> list[DistractorCandidate]: ...


class LearnerProfileSource(Protocol):
    async def profile_of(self, user_id: int) -> LearnerProfile:
        """Trình độ HSK đã khai báo và múi giờ (M02); chưa khai báo thì `hsk_level` là None."""
        ...


class QuizVocabSource(Protocol):
    """Dữ liệu của M07 mà bài kiểm tra cần; M07 hiện thực (M09 không import nội bộ của M07)."""

    async def quizzable_words(self, user_id: int) -> list[QuizWord]:
        """Mọi từ không ở trạng thái "Bỏ qua" (F09.01)."""
        ...

    async def contexts(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, list[WordContext]]:
        """Câu ngữ cảnh của từng mục từ, mới nhất trước."""
        ...

    async def entries(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, EntryRef]:
        """Mục từ còn tồn tại; mục đã xóa vắng mặt."""
        ...

    async def saved_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        """Tập con của `terms` đã có trong sổ tay, mọi trạng thái (F09.09)."""
        ...

    async def mark_learning(self, user_id: int, entry_ids: Sequence[int], now: datetime) -> None:
        """Chuyển các mục từ đang "Đã thuộc" về "Đang học"; trạng thái khác giữ nguyên (F09.04)."""
        ...


class QuizRepository(Protocol):
    """Mọi truy vấn lọc theo `user_id` của chủ sở hữu."""

    async def add(
        self, new_quiz: NewQuiz, questions: Sequence[NewQuestion]
    ) -> tuple[Quiz, list[QuizQuestion]]: ...

    async def get(self, user_id: int, quiz_id: int) -> Quiz | None: ...

    async def get_for_update(self, user_id: int, quiz_id: int) -> Quiz | None:
        """Khóa dòng để hai lần nộp đồng thời được xử lý tuần tự."""
        ...

    async def questions(self, quiz_id: int) -> list[QuizQuestion]:
        """Theo thứ tự câu."""
        ...

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[Quiz], int]:
        """Mới nhất trước."""
        ...

    async def count_llm_between(self, user_id: int, start: datetime, end: datetime) -> int:
        """Số bài có `source <> 'fallback'` tạo trong [start, end) — dùng cho hạn mức LLM mỗi ngày."""
        ...

    async def save_result(self, quiz: Quiz, graded: Sequence[GradedAnswer]) -> None:
        """Ghi điểm, thời điểm nộp, mốc ôn sớm của bài và đáp án/kết quả từng câu."""
        ...

    async def recent_example_ids(self, user_id: int, quizzes: int) -> set[int]:
        """Mã câu ví dụ đã dùng trong `quizzes` bài gần nhất, để không lặp lại (F09.09)."""
        ...

    async def save_mistake_review(
        self, quiz_id: int, question_id: int, review: MistakeReview, at: datetime
    ) -> MistakeReview:
        """Lưu "Vì sao sai?" nếu câu chưa có; đã có (hai yêu cầu cùng lúc) thì giữ bản cũ.

        Trả bản đang lưu.
        """
        ...

    async def count_llm_mistake_reviews_between(self, user_id: int, start: datetime, end: datetime) -> int:
        """Số "Vì sao sai?" do LLM tạo trong [start, end) của người dùng — hạn mức riêng của F09.10."""
        ...

    async def delete(self, user_id: int, quiz_id: int) -> None: ...


class QuizUnitOfWork(Protocol):
    """Một giao dịch dùng chung với M07 (từ) và M08 (thẻ). Không commit thì mọi thay đổi bị hủy."""

    @property
    def quizzes(self) -> QuizRepository: ...

    @property
    def vocab(self) -> QuizVocabSource: ...

    @property
    def cards(self) -> CardRepository: ...

    @property
    def examples(self) -> ExampleSource: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    @property
    def activity(self) -> ActivityRecorder: ...

    @property
    def learning(self) -> LearningEventPort: ...

    async def __aenter__(self) -> QuizUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
