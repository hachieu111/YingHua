from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuizConfig:
    """Giới hạn nghiệp vụ của M09, lấy từ Settings ở tầng lắp ghép.

    Công tắc LLM và hạn mức đề LLM mỗi ngày không nằm ở đây mà đi qua port `AiPolicy` (F13.05, F17.04).
    """

    question_count: int  # số câu mặc định (F09.01)
    min_words: int  # sổ tay cần tối thiểu bấy nhiêu từ mới ra đề
