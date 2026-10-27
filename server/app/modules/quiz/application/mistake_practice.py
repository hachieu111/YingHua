"""Câu luyện dự phòng cho "Vì sao sai?" (F09.10 bước 6): dựng từ câu ví dụ trong từ điển/Tatoeba."""

from __future__ import annotations

from app.modules.quiz.application.drafting import DraftInput, FallbackQuestionBuilder
from app.modules.quiz.domain.entities import ExampleForm, PracticeQuestion, QuizQuestion, QuizWord
from app.modules.quiz.domain.mistake_review import practice_from_question

DEFAULT_LEVEL = 3  # cấp chọn nhiễu khi từ và người học đều chưa có cấp HSK (như F09.08)
_FORM_ORDER = (ExampleForm.CLOZE, ExampleForm.SENSE, ExampleForm.TRANSLATE)


class MistakePracticeBuilder:
    """Cùng bộ lọc độ khó và cách chọn nhiễu cùng cấp HSK như đề dự phòng; không tìm được câu ví dụ phù hợp
    thì trả None (chỉ hiện phần giải thích). Ưu tiên dạng câu khác dạng của câu vừa làm sai."""

    def __init__(self, builder: FallbackQuestionBuilder) -> None:
        self._builder = builder

    async def build(
        self, word: QuizWord, wrong: QuizQuestion, learner_level: int | None
    ) -> PracticeQuestion | None:
        used = {wrong.example_id} if wrong.example_id is not None else set()
        draft = DraftInput(
            words=[word],
            pool_words=[],
            contexts={},
            default_level=word.hsk_level or learner_level or DEFAULT_LEVEL,
            blocked=None,
            learner_level=learner_level,
            used_example_ids=used,
        )
        index = _FORM_ORDER.index(wrong.example_form) + 1 if wrong.example_form in _FORM_ORDER else 0
        question = await self._builder.build_example_only(word, index, draft)
        return practice_from_question(question) if question is not None else None
