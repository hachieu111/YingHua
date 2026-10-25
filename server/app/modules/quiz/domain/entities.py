"""Thực thể của M09 Kiểm tra — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QuizStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"


class QuizSource(str, Enum):
    """Nguồn đề: do LLM sinh, hoàn toàn dự phòng, hoặc LLM pha câu dự phòng (F09.07)."""

    LLM = "llm"
    FALLBACK = "fallback"
    MIXED = "mixed"


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"


class TargetKind(str, Enum):
    """Đối tượng được hỏi: từ đã lưu trong sổ tay hoặc từ mở rộng liên quan (F09.09)."""

    SAVED = "saved"
    RELATED = "related"


class ExampleForm(str, Enum):
    """Dạng câu hỏi dựa trên câu ví dụ (F09.09)."""

    CLOZE = "cloze"  # điền từ vào chỗ trống, chọn chữ Hán
    SENSE = "sense"  # nghĩa của từ (đánh dấu 【】) trong câu
    TRANSLATE = "translate"  # chọn bản dịch đúng của cả câu

    @property
    def reveals_sentence(self) -> bool:
        """Câu gốc có an toàn để hiện trước khi nộp bài không (dạng điền từ chứa đáp án trong câu)."""
        return self is not ExampleForm.CLOZE


class RelatedSource(str, Enum):
    """Nguồn của ứng viên từ mở rộng, xếp theo độ mạnh giảm dần (F09.09)."""

    SHARED_CHAR = "shared_char"  # có chung chữ Hán với một từ đã lưu
    ENCOUNTERED = "encountered"  # từng gặp khi đọc truyện hoặc đã tra mà chưa lưu
    SHARED_COMPONENT = "shared_component"  # chung thành phần/bộ thủ
    SAME_LEVEL = "same_level"  # cùng cấp HSK với một từ đã lưu


class QuestionOrigin(str, Enum):
    LLM = "llm"
    FALLBACK = "fallback"


class FallbackReason(str, Enum):
    """Vì sao phải dùng đề dự phòng (F09.08 bước 4); chỉ để ghi nhật ký, không báo người học."""

    LLM_DISABLED = "llm_disabled"
    TIMEOUT = "timeout"
    INVALID_SCHEMA = "invalid_schema"
    NETWORK = "network"
    DAILY_LIMIT = "daily_limit"


@dataclass(slots=True)
class Quiz:
    id: int
    user_id: int
    source: QuizSource
    status: QuizStatus
    question_count: int
    created_at: datetime
    note: str | None = None
    fallback_reason: FallbackReason | None = None
    score: int | None = None
    submitted_at: datetime | None = None
    wrong_cards_rescheduled_at: datetime | None = None
    related_score: int | None = None
    related_count: int = 0  # số câu từ mở rộng; `score`/`question_count` chỉ tính câu từ đã lưu


@dataclass(slots=True)
class QuizQuestion:
    id: int
    quiz_id: int
    position: int
    question_type: QuestionType
    prompt: str
    correct_answer: str
    origin: QuestionOrigin
    options: list[str] | None = None
    accepted_answers: list[str] = field(default_factory=list)
    explanation: str | None = None
    vocab_entry_id: int | None = None  # None: từ đã bị xóa khỏi sổ tay sau khi ra đề
    user_answer: str | None = None
    is_correct: bool | None = None
    term: str = ""  # từ được hỏi (vocab_entry_id NULL với từ mở rộng)
    target_kind: TargetKind = TargetKind.SAVED
    related_entry_id: int | None = None  # từ đã lưu làm cầu nối của từ mở rộng
    example_id: int | None = None
    example_form: ExampleForm | None = None
    hint: str | None = None


@dataclass(frozen=True, slots=True)
class NewQuiz:
    user_id: int
    source: QuizSource
    question_count: int
    created_at: datetime
    note: str | None = None
    fallback_reason: FallbackReason | None = None
    related_count: int = 0


@dataclass(frozen=True, slots=True)
class NewQuestion:
    """Câu hỏi chưa lưu; vị trí do thứ tự trong danh sách quyết định."""

    question_type: QuestionType
    prompt: str
    correct_answer: str
    origin: QuestionOrigin
    options: list[str] | None = None
    accepted_answers: list[str] = field(default_factory=list)
    explanation: str | None = None
    vocab_entry_id: int | None = None
    term: str = ""
    target_kind: TargetKind = TargetKind.SAVED
    related_entry_id: int | None = None
    example_id: int | None = None
    example_form: ExampleForm | None = None
    hint: str | None = None


@dataclass(frozen=True, slots=True)
class GradedAnswer:
    question_id: int
    user_answer: str | None
    is_correct: bool


@dataclass(frozen=True, slots=True)
class QuizWord:
    """Một từ trong sổ tay có thể ra đề (không ở trạng thái "Bỏ qua")."""

    entry_id: int
    term: str
    pinyin: str | None
    meaning_vi: str | None
    hsk_level: int | None
    status: str  # learning | known


@dataclass(frozen=True, slots=True)
class WordContext:
    sentence_zh: str
    sentence_vi: str | None


@dataclass(frozen=True, slots=True)
class DistractorCandidate:
    """Từ dùng làm phương án nhiễu; `meaning_vi` là nghĩa thô, chưa rút gọn."""

    term: str
    meaning_vi: str | None
    pinyin: str | None = None


@dataclass(frozen=True, slots=True)
class ExampleRow:
    """Câu ví dụ Tatoeba kèm độ khó đã tính (F09.09)."""

    id: int
    zh: str
    pinyin: str | None
    vi: str | None
    difficulty_level: int | None


@dataclass(frozen=True, slots=True)
class RelatedLink:
    """Một lý do chọn từ mở rộng: nguồn, từ đã lưu làm cầu nối và chi tiết dùng cho gợi ý."""

    source: RelatedSource
    bridge_entry_id: int
    bridge_term: str
    bridge_meaning: str | None = None
    detail: str | None = None  # chữ chung, thành phần chung hoặc tên truyện đã gặp


@dataclass(frozen=True, slots=True)
class RelatedCandidate:
    """Từ mở rộng chưa có trong sổ tay; mỗi ứng viên có ít nhất một liên kết với từ đã lưu."""

    term: str
    pinyin: str | None
    meaning_vi: str | None
    hsk_level: int | None
    links: tuple[RelatedLink, ...]
    han_viet: str | None = None
