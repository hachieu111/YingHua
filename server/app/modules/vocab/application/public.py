"""Bề mặt công khai của M07 cho module khác (M09 chọn từ ra đề, M10 nhận gợi ý, M12 thống kê)."""

from __future__ import annotations

from app.modules.vocab.application.dto import SaveWordCommand, SaveWordResult
from app.modules.vocab.application.use_cases.save_word import SaveWordUseCase
from app.modules.vocab.domain.entities import VocabEntry, VocabStatus

__all__ = ["SaveWordCommand", "SaveWordResult", "SaveWordUseCase", "VocabEntry", "VocabStatus"]
