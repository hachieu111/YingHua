"""Soạn đề: LLM trước (nếu được phép), kiểm lược đồ, sinh lại tối đa một lần, rồi đề dự phòng (F09.06-08)."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

from app.core.glosses import short_meaning
from app.modules.quiz.application.llm_review import LlmReviewer
from app.modules.quiz.application.ports import (
    DistractorSource,
    ExampleSource,
    GenerationItem,
    QuizGenerationRequest,
    QuizGenerator,
)
from app.modules.quiz.domain.entities import (
    DistractorCandidate,
    FallbackReason,
    NewQuestion,
    QuestionOrigin,
    QuizSource,
    QuizWord,
    RelatedCandidate,
    TargetKind,
    WordContext,
)
from app.modules.quiz.domain.errors import QuizGeneratorUnavailableError
from app.modules.quiz.domain.examples import (
    build_example_question,
    choose_example,
    example_difficulty_cap,
)
from app.modules.quiz.domain.fallback import (
    DistractorPools,
    build_choice_question,
    build_fallback_question,
    levels_to_fetch,
)
from app.modules.quiz.domain.llm_schema import LlmQuestions, validate_llm_payload
from app.modules.quiz.domain.related import best_link, build_hint
from app.modules.quiz.domain.rules import FALLBACK_NOTE, MIXED_NOTE

logger = logging.getLogger(__name__)

POOL_SIZE_PER_LEVEL = 24  # số từ HSK ngẫu nhiên nạp cho mỗi cấp làm nguồn nhiễu
MAX_LLM_ATTEMPTS = 2  # lần đầu + sinh lại một lần (F09.07)
EXAMPLE_FETCH_LIMIT = 30
TRANSLATION_POOL_SIZE = 12


@dataclass(frozen=True, slots=True)
class DraftInput:
    words: Sequence[QuizWord]  # từ đã lưu được chọn ra đề
    pool_words: Sequence[QuizWord]  # mọi từ ra đề được trong sổ tay: nguồn nhiễu dự phòng cuối cùng
    contexts: Mapping[int, Sequence[WordContext]]
    default_level: int
    blocked: FallbackReason | None  # không được gọi LLM vì lý do này (tắt, hết hạn mức ngày)
    related: Sequence[RelatedCandidate] = ()  # từ mở rộng đã chọn (F09.09)
    learner_level: int | None = None
    # Mã câu ví dụ không được dùng lại; builder bổ sung các câu vừa chọn để một bài không lặp câu.
    used_example_ids: set[int] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class DraftedQuiz:
    questions: list[NewQuestion]
    source: QuizSource
    note: str | None
    fallback_reason: FallbackReason | None
    related_count: int = 0


class FallbackQuestionBuilder:
    """Đề dự phòng từ từ điển (F09.08): nạp nhiễu cùng cấp HSK (và cấp lân cận) rồi sinh câu cho từng từ.

    Mỗi từ (đã lưu hoặc mở rộng) ưu tiên câu hỏi dựa trên câu ví dụ Tatoeba theo độ khó (F09.09); hết câu
    ví dụ thì lùi về câu ngữ cảnh trong sổ tay (chỉ từ đã lưu) rồi câu hỏi theo định nghĩa.
    """

    def __init__(self, distractors: DistractorSource, examples: ExampleSource, rng: random.Random) -> None:
        self._distractors = distractors
        self._examples = examples
        self._rng = rng

    async def build(self, words: Sequence[QuizWord], draft: DraftInput) -> list[NewQuestion]:
        pools = await self._pools([w.hsk_level for w in words], draft)
        questions: list[NewQuestion] = []
        translations: dict[int, list[str]] = {}
        for index, word in enumerate(words):
            contexts = draft.contexts.get(word.entry_id, ())
            question = await self._with_example(word, index, draft, pools, translations)
            if question is None:
                question = build_fallback_question(
                    word, index, contexts, pools, draft.default_level, self._rng
                )
            questions.append(question)
        return questions

    async def build_related(self, draft: DraftInput) -> list[NewQuestion]:
        """Câu trắc nghiệm cho từ mở rộng, kèm gợi ý; từ không dựng được câu bị bỏ (F09.09)."""
        pools = await self._pools([c.hsk_level for c in draft.related], draft)
        questions: list[NewQuestion] = []
        translations: dict[int, list[str]] = {}
        for index, candidate in enumerate(draft.related):
            word = QuizWord(
                0, candidate.term, candidate.pinyin, candidate.meaning_vi, candidate.hsk_level, ""
            )
            question = await self._with_example(word, index, draft, pools, translations)
            if question is None:
                question = build_choice_question(word, index, pools, draft.default_level, self._rng)
            if question is None:
                logger.warning("Không dựng được câu cho từ mở rộng %s", candidate.term)
                continue
            hint = build_hint(candidate)
            questions.append(
                replace(
                    question,
                    vocab_entry_id=None,
                    target_kind=TargetKind.RELATED,
                    related_entry_id=best_link(candidate).bridge_entry_id,
                    hint=hint,
                )
            )
        return questions

    async def build_example_only(self, word: QuizWord, index: int, draft: DraftInput) -> NewQuestion | None:
        """Một câu dựa trên câu ví dụ cho `word`, dạng theo `index`; không có câu phù hợp thì None, không
        lùi về câu theo định nghĩa (F09.10 bước 6: chỉ hiện giải thích)."""
        pools = await self._pools([word.hsk_level], draft)
        return await self._with_example(word, index, draft, pools, {})

    async def _pools(self, word_levels: Sequence[int | None], draft: DraftInput) -> DistractorPools:
        exclude = [w.term for w in draft.words] + [c.term for c in draft.related]
        levels = sorted({lv for level in word_levels for lv in levels_to_fetch(level or draft.default_level)})
        by_level = {lv: await self._distractors.sample(lv, POOL_SIZE_PER_LEVEL, exclude) for lv in levels}
        chosen = set(exclude)
        notebook = [
            DistractorCandidate(w.term, w.meaning_vi, w.pinyin)
            for w in draft.pool_words
            if w.term not in chosen
        ]
        return DistractorPools(by_level, notebook)

    async def _with_example(
        self,
        word: QuizWord,
        index: int,
        draft: DraftInput,
        pools: DistractorPools,
        translations: dict[int, list[str]],
    ) -> NewQuestion | None:
        cap = example_difficulty_cap(draft.learner_level, word.hsk_level)
        found = await self._examples.find(word.term, cap, EXAMPLE_FETCH_LIMIT)
        example = choose_example(found, word.term, draft.used_example_ids, self._rng)
        if example is None:
            return None
        difficulty = example.difficulty_level or cap
        if difficulty not in translations:
            translations[difficulty] = await self._examples.sample_translations(
                difficulty, [example.id], TRANSLATION_POOL_SIZE
            )
        question = build_example_question(
            word,
            index,
            example,
            word.hsk_level or draft.default_level,
            pools,
            translations[difficulty],
            self._rng,
        )
        if question is not None:
            draft.used_example_ids.add(example.id)
        return question


class QuizDrafter:
    """Bảo đảm luôn có đề: mọi lỗi của LLM đều thành đề dự phòng, không lộ lỗi kỹ thuật."""

    def __init__(
        self,
        generator: QuizGenerator,
        fallback: FallbackQuestionBuilder,
        timeout_seconds: float,
        reviewer: LlmReviewer | None = None,
    ) -> None:
        self._generator = generator
        self._fallback = fallback
        self._timeout = timeout_seconds
        self._reviewer = reviewer

    async def draft(self, draft: DraftInput) -> DraftedQuiz:
        """Đề đủ cả câu từ đã lưu (LLM hoặc dự phòng) lẫn câu từ mở rộng (luôn dựng từ từ điển)."""
        saved = await self._draft_saved(draft)
        related = await self._fallback.build_related(draft) if draft.related else []
        return replace(saved, questions=[*saved.questions, *related], related_count=len(related))

    async def _draft_saved(self, draft: DraftInput) -> DraftedQuiz:
        if draft.blocked is not None:
            return await self._all_fallback(draft, draft.blocked)
        try:
            validated = await asyncio.wait_for(self._ask_llm(draft), self._timeout)
            llm_questions = await self._review(validated, draft)
        except asyncio.TimeoutError:
            return await self._all_fallback(draft, FallbackReason.TIMEOUT)
        except QuizGeneratorUnavailableError as exc:
            return await self._all_fallback(draft, _reason_of(exc))
        except Exception:  # lỗi lạ của adapter cũng không được chặn người học có bài
            logger.exception("Lỗi không lường trước khi sinh đề bằng LLM")
            return await self._all_fallback(draft, FallbackReason.NETWORK)
        if llm_questions is None:
            return await self._all_fallback(draft, FallbackReason.INVALID_SCHEMA)
        return await self._complete(draft, llm_questions)

    async def _review(self, validated: LlmQuestions | None, draft: DraftInput) -> list[NewQuestion] | None:
        if validated is None or self._reviewer is None:
            return validated.questions if validated else None
        return await self._reviewer.review(
            validated, draft.words, draft.learner_level, draft.used_example_ids
        )

    async def _ask_llm(self, draft: DraftInput) -> LlmQuestions | None:
        request = QuizGenerationRequest(
            [
                GenerationItem(w.term, w.pinyin, short_meaning(w.meaning_vi) or None, w.hsk_level)
                for w in draft.words
            ],
            len(draft.words),
            draft.learner_level,
        )
        for _ in range(MAX_LLM_ATTEMPTS):
            validated = validate_llm_payload(await self._generator.generate(request), draft.words)
            if validated is not None:
                return validated
        return None

    async def _all_fallback(self, draft: DraftInput, reason: FallbackReason) -> DraftedQuiz:
        logger.warning("Dùng đề dự phòng cho bài kiểm tra: %s", reason.value)
        questions = await self._fallback.build(draft.words, draft)
        return DraftedQuiz(questions, QuizSource.FALLBACK, FALLBACK_NOTE, reason)

    async def _complete(self, draft: DraftInput, llm_questions: list[NewQuestion]) -> DraftedQuiz:
        """Bù câu dự phòng cho từ LLM bỏ sót để mỗi từ đúng một câu, giữ thứ tự (F09.07 bước 5)."""
        by_entry = {q.vocab_entry_id: q for q in llm_questions}
        missing = [w for w in draft.words if w.entry_id not in by_entry]
        patches = iter(await self._fallback.build(missing, draft) if missing else [])
        questions = [by_entry[w.entry_id] if w.entry_id in by_entry else next(patches) for w in draft.words]
        if not missing:
            return DraftedQuiz(questions, QuizSource.LLM, None, None)
        logger.warning("Bù %d câu dự phòng vào đề LLM", len(missing))
        if all(q.origin is QuestionOrigin.FALLBACK for q in questions):  # không câu nào của LLM dùng được
            return DraftedQuiz(questions, QuizSource.FALLBACK, FALLBACK_NOTE, FallbackReason.INVALID_SCHEMA)
        return DraftedQuiz(questions, QuizSource.MIXED, MIXED_NOTE, None)


def _reason_of(exc: QuizGeneratorUnavailableError) -> FallbackReason:
    try:
        return FallbackReason(exc.reason)
    except ValueError:
        return FallbackReason.NETWORK
