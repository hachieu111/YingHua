"""Bề mặt công khai của M09 cho module khác (M07 hiện thực nguồn từ cho bài kiểm tra, M12 thống kê)."""

from __future__ import annotations

from app.modules.quiz.application.ports import EntryRef, QuizVocabSource
from app.modules.quiz.domain.entities import Quiz, QuizSource, QuizStatus, QuizWord, WordContext

__all__ = [
    "EntryRef",
    "Quiz",
    "QuizSource",
    "QuizStatus",
    "QuizVocabSource",
    "QuizWord",
    "WordContext",
]
