from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuizConfig:
    """Giới hạn nghiệp vụ của M09, lấy từ Settings ở tầng lắp ghép."""

    question_count: int  # số câu mặc định (F09.01)
    min_words: int  # sổ tay cần tối thiểu bấy nhiêu từ mới ra đề
    daily_llm_limit: int  # số đề LLM mỗi người mỗi ngày (F13.05)
    llm_enabled: bool
