"""Bề mặt công khai ở tầng api của M07 cho router của module khác (M10 nhận gợi ý bằng cách lưu từ)."""

from __future__ import annotations

from app.modules.vocab.api.dependencies import VocabServices, build_vocab_services
from app.modules.vocab.api.schemas import SaveWordResponse

__all__ = ["SaveWordResponse", "VocabServices", "build_vocab_services"]
