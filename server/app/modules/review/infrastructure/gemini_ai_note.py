"""Sinh Thẻ mở rộng AI bằng Google Gemini (F08.11, US-NH-75) qua client dùng chung `app.core.llm_gemini`.

Nội dung gửi đi chỉ gồm từ, pinyin, nghĩa ngắn, cấp HSK, trình độ của người học (một con số) và dữ liệu
phân rã chữ Hán của từ điển: không có email, tên hay mã người dùng, ngữ cảnh hay ghi chú riêng (security.md).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.glosses import short_meaning
from app.core.llm_gemini import (
    BASE_URL,
    DEFAULT_THINKING_LEVEL,
    CallRecorder,
    GeminiClient,
    LlmUnavailableError,
    Sleep,
)
from app.modules.review.application.dto import AiNoteRequest
from app.modules.review.domain.ai_note import EXAMPLE_COUNT, PHRASE_MAX, PHRASE_MIN, CharParts
from app.modules.review.domain.errors import AiNoteGeneratorUnavailableError

OPERATION = "ai_note"

_STRING = {"type": "STRING"}
_SENTENCE = {
    "type": "OBJECT",
    "properties": {"zh": _STRING, "pinyin": _STRING, "vi": _STRING},
    "required": ["zh", "pinyin", "vi"],
}
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "examples": {"type": "ARRAY", "items": _SENTENCE},
        "mnemonic": _STRING,
        "phrases": {"type": "ARRAY", "items": _SENTENCE},
    },
    "required": ["examples", "mnemonic", "phrases"],
}


def _parts_line(part: CharParts) -> str:
    pieces = []
    if part.components:
        pieces.append("gồm " + " + ".join(part.components))
    if part.radical:
        pieces.append(f"bộ {part.radical}")
    if part.han_viet:
        pieces.append(f"âm Hán Việt {part.han_viet}")
    return f"- {part.ch}: {', '.join(pieces) or 'chưa có dữ liệu'}"


def build_prompt(request: AiNoteRequest) -> str:
    """Prompt tiếng Việt; chỉ chứa dữ liệu từ vựng và dữ liệu chữ Hán, không định danh người học."""
    level = request.learner_level
    max_level = (level + 1) if level is not None else None
    level_text = f"HSK {level}" if level is not None else "chưa xác định (hãy dùng từ vựng HSK 1-3)"
    sentence_rule = f"chỉ dùng từ vựng HSK {max_level} trở xuống" if max_level else "chỉ dùng từ vựng HSK 1-3"
    word_level = f"HSK {request.hsk_level}" if request.hsk_level else "ngoài HSK"
    meaning = short_meaning(request.meaning) or "-"
    parts = "\n".join(_parts_line(p) for p in request.parts) or "- (không có dữ liệu chiết tự)"
    return (
        "Bạn là giáo viên tiếng Trung cho người học Việt Nam. Hãy tạo thẻ học mở rộng cho MỘT từ.\n"
        f"Từ: {request.term} | pinyin: {request.pinyin or '-'} | nghĩa: {meaning} | cấp HSK: {word_level}\n"
        f"Trình độ người học: {level_text}.\n\n"
        f"Dữ liệu phân rã chữ Hán của từ điển:\n{parts}\n\n"
        "Yêu cầu:\n"
        f'- "examples": đúng {EXAMPLE_COUNT} câu ví dụ MỚI, ngắn (5-15 chữ Hán), mỗi câu chứa đúng từ trên, '
        f'{sentence_rule}; mỗi câu có "zh" (tiếng Trung), "pinyin", "vi" (bản dịch tiếng Việt).\n'
        '- "mnemonic": 1-2 câu tiếng Việt giúp nhớ chữ theo chiết tự. CHỈ nhắc tới các chữ và thành phần có '
        "trong dữ liệu phân rã ở trên, tuyệt đối không bịa thêm thành phần khác.\n"
        f'- "phrases": {PHRASE_MIN}-{PHRASE_MAX} cụm từ ngắn thường đi kèm với từ này, mỗi cụm chứa đúng từ '
        'đó và có "zh", "pinyin", "vi".\n'
        "- Chỉ trả về JSON đúng lược đồ, không thêm chữ nào khác."
    )


class GeminiAiNoteGenerator:
    """Hiện thực `AiNoteGenerator` bằng Gemini. Lỗi hạ tầng đổi thành `AiNoteGeneratorUnavailableError`;
    phản hồi bị chặn/cắt giữa chừng/JSON hỏng trả `None` (use case coi là không hợp lệ và dùng dự phòng)."""

    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float,
        record: CallRecorder,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        base_url: str = BASE_URL,
        thinking_level: str | None = DEFAULT_THINKING_LEVEL,
    ) -> None:
        self._client = GeminiClient(
            api_key,
            model,
            timeout_seconds,
            OPERATION,
            record,
            transport=transport,
            sleep=sleep,
            base_url=base_url,
            thinking_level=thinking_level,
        )

    async def generate(self, request: AiNoteRequest) -> object:
        try:
            return await self._client.generate_json(build_prompt(request), RESPONSE_SCHEMA)
        except LlmUnavailableError as exc:
            raise AiNoteGeneratorUnavailableError(exc.reason) from exc


class DisabledAiNoteGenerator:
    """Khi LLM tắt hoặc chưa cấu hình khóa: luôn báo không khả dụng để dùng nội dung dự phòng."""

    async def generate(self, request: AiNoteRequest) -> object:
        raise AiNoteGeneratorUnavailableError("llm_disabled")
