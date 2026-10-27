"""Giải thích lỗi sai bằng Google Gemini qua REST (F09.10, US-NH-79), client chung `app.core.llm_gemini`.

Nội dung gửi đi chỉ gồm từ, pinyin, nghĩa ngắn, cấp HSK, hai lựa chọn liên quan (đã chọn, đúng) và trình độ
của người học (một con số): không có email, tên, mã người dùng, ngữ cảnh hay ghi chú riêng (security.md).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.llm_gemini import (
    BASE_URL,
    DEFAULT_THINKING_LEVEL,
    CallRecorder,
    GeminiClient,
    LlmUnavailableError,
    Sleep,
)
from app.modules.quiz.application.ports import MistakeReviewRequest
from app.modules.quiz.domain.errors import QuizGeneratorUnavailableError

OPERATION = "mistake_review"

_STRING = {"type": "STRING"}
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "explanation": _STRING,
        "difference": _STRING,
        "practice": {
            "type": "OBJECT",
            "properties": {
                "prompt": _STRING,
                "options": {"type": "ARRAY", "items": _STRING},
                "answer": _STRING,
                "explanation": _STRING,
            },
            "required": ["prompt", "options", "answer", "explanation"],
        },
    },
    "required": ["explanation", "difference", "practice"],
}


def build_prompt(request: MistakeReviewRequest) -> str:
    """Prompt tiếng Việt; chỉ chứa dữ liệu từ vựng và hai lựa chọn liên quan."""
    level = request.learner_level
    level_text = f"HSK {level}" if level is not None else "chưa xác định (hãy dùng từ vựng HSK 1-3)"
    sentence_rule = f"HSK {level + 1} trở xuống" if level is not None else "HSK 1-3"
    word_level = f"HSK {request.hsk_level}" if request.hsk_level else "ngoài HSK"
    chosen = f"“{request.chosen}”" if request.chosen else "(người học bỏ trống câu này)"
    return (
        "Bạn là giáo viên tiếng Trung cho người học Việt Nam. Người học vừa làm SAI một câu kiểm tra về "
        "MỘT từ. Hãy giải thích lỗi và ra một câu luyện thêm.\n"
        f"Từ: {request.term} | pinyin: {request.pinyin or '-'} | nghĩa: {request.meaning or '-'} | "
        f"cấp: {word_level}\n"
        f"Đáp án người học đã chọn: {chosen}\n"
        f"Đáp án đúng: “{request.correct}”\n"
        f"Trình độ người học: {level_text}.\n\n"
        "Yêu cầu (viết tiếng Việt, thật ngắn gọn):\n"
        '- "explanation": vì sao đáp án đã chọn không đúng (không quá 40 từ).\n'
        '- "difference": điểm khác giữa đáp án đã chọn và đáp án đúng, chỉ ra từ dễ nhầm nếu có '
        "(không quá 40 từ).\n"
        '- "practice": MỘT câu trắc nghiệm mới về đúng từ trên, đúng 4 lựa chọn khác nhau, đúng 1 đáp án; '
        '"answer" phải trùng nguyên văn một lựa chọn trong "options". Dạng câu hỏi: hoặc hỏi nghĩa '
        f"tiếng Việt của từ trong một câu tiếng Trung ngắn ({sentence_rule}) có chứa từ đó, hoặc chọn chữ "
        'Hán điền vào chỗ trống "＿＿" (đáp án đúng bằng đúng từ đang học). Lựa chọn nghĩa là cụm ngắn '
        'không quá 6 từ, đáp án nghĩa phải đúng với nghĩa đã cho; "explanation" của câu luyện không quá '
        "20 từ.\n"
        "- Chỉ trả về JSON đúng lược đồ, không thêm chữ nào khác."
    )


class GeminiMistakeReviewGenerator:
    """Hiện thực `MistakeReviewGenerator` bằng Gemini. Lỗi hạ tầng đổi thành `QuizGeneratorUnavailableError`;
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

    async def generate(self, request: MistakeReviewRequest) -> object:
        try:
            return await self._client.generate_json(build_prompt(request), RESPONSE_SCHEMA)
        except LlmUnavailableError as exc:
            raise QuizGeneratorUnavailableError(exc.reason, exc.message) from exc


class DisabledMistakeReviewGenerator:
    """Khi LLM tắt hoặc chưa cấu hình khóa: luôn báo không khả dụng để dùng nội dung dự phòng."""

    async def generate(self, request: MistakeReviewRequest) -> object:
        raise QuizGeneratorUnavailableError("llm_disabled", "LLM đang tắt")
