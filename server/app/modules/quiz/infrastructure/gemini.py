"""Sinh đề bằng Google Gemini qua REST (F09.06, US-LLM-01).

Chỉ dùng `httpx` (đã có trong requirements). Khóa API gửi qua header `x-goog-api-key`, KHÔNG nằm trong URL
hay query nên không lọt vào log của httpx. Nội dung gửi đi chỉ gồm từ, pinyin, nghĩa ngắn, cấp HSK và trình độ
của người học (một con số): tuyệt đối không có email, tên hay mã người dùng (security.md).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.llm_gemini import (
    API_KEY_HEADER,
    BASE_URL,
    DEFAULT_THINKING_LEVEL,
    GeminiClient,
    LlmCall,
    LlmUnavailableError,
    Sleep,
)
from app.modules.quiz.application.ports import (
    ExternalCall,
    ExternalCallLog,
    GenerationItem,
    QuizGenerationRequest,
)
from app.modules.quiz.domain.errors import QuizGeneratorUnavailableError

__all__ = ["API_KEY_HEADER", "RESPONSE_SCHEMA", "GeminiQuizGenerator", "build_prompt"]

OPERATION = "generate_quiz"

_STRING = {"type": "STRING"}
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "questions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "term": _STRING,
                    "type": {"type": "STRING", "enum": ["multiple_choice", "fill_blank"]},
                    "prompt": _STRING,
                    "options": {"type": "ARRAY", "items": _STRING},
                    "answer": _STRING,
                    "explanation": _STRING,
                    "example_zh": _STRING,
                    "example_vi": _STRING,
                },
                "required": ["term", "type", "prompt", "answer", "explanation", "example_zh", "example_vi"],
            },
        }
    },
    "required": ["questions"],
}


def build_prompt(request: QuizGenerationRequest) -> str:
    """Prompt tiếng Việt; chỉ chứa dữ liệu từ vựng, không có thông tin định danh người học."""
    level = request.learner_level
    max_level = (level + 1) if level is not None else None
    level_text = f"HSK {level}" if level is not None else "chưa xác định (hãy dùng từ vựng HSK 1-3)"
    sentence_rule = f"chỉ dùng từ vựng HSK {max_level} trở xuống" if max_level else "chỉ dùng từ vựng HSK 1-3"
    lines = "\n".join(_item_line(i, item) for i, item in enumerate(request.items, start=1))
    return (
        "Bạn là giáo viên tiếng Trung cho người học Việt Nam. Hãy tạo bài kiểm tra từ vựng "
        f"gồm đúng {request.question_count} câu, mỗi từ dưới đây đúng MỘT câu. "
        f"Trình độ người học: {level_text}.\n\n"
        f"Danh sách từ (từ | pinyin | nghĩa | cấp HSK):\n{lines}\n\n"
        "Yêu cầu:\n"
        '- Xen kẽ hai dạng: "multiple_choice" (4 lựa chọn, đúng 1 đáp án; đáp án phải nằm trong "options"; '
        'các lựa chọn sai hợp lý, cùng loại với đáp án) và "fill_blank" (điền chữ Hán; "answer" đúng bằng từ '
        'đang hỏi, "options" để trống, trong "prompt" thay từ đó bằng '
        'đúng một "＿＿"). Câu điền từ phải là câu tiếng Trung đầy đủ, có ngữ cảnh chỉ MỘT đáp án hợp lý '
        '(không viết câu mơ hồ như "这是＿＿的词语") và kèm nghĩa tiếng Việt của từ trong ngoặc ở cuối, '
        'ví dụ "(nghĩa: bạn bè)". Mọi lựa chọn nghĩa tiếng Việt là cụm ngắn, không chép nguyên định nghĩa '
        "từ điển.\n"
        '- "term" phải đúng nguyên văn từ trong danh sách. Câu hỏi và giải thích viết bằng tiếng Việt, '
        "đáp án nghĩa phải đúng với nghĩa đã cho. Viết thật ngắn gọn: câu hỏi và giải thích mỗi phần "
        "không quá 15 từ, mỗi lựa chọn không quá 6 từ.\n"
        f"- Với mỗi từ viết một câu ví dụ MỚI, ngắn (5-15 chữ Hán), có chứa từ đó, {sentence_rule}: "
        '"example_zh" là câu tiếng Trung, "example_vi" là bản dịch tiếng Việt.\n'
        "- Chỉ trả về JSON đúng lược đồ, không thêm chữ nào khác."
    )


def _item_line(index: int, item: GenerationItem) -> str:
    level = f"HSK {item.hsk_level}" if item.hsk_level else "ngoài HSK"
    return f"{index}. {item.term} | {item.pinyin or '-'} | {item.meaning or '-'} | {level}"


class GeminiQuizGenerator:
    """Hiện thực `QuizGenerator` bằng Gemini (client dùng chung ở `app.core.llm_gemini`). Mọi lỗi hạ tầng đổi
    thành `QuizGeneratorUnavailableError`; phản hồi bị chặn/cắt giữa chừng/JSON hỏng trả `None` (use case coi
    là sai lược đồ và sinh lại một lần)."""

    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float,
        call_log: ExternalCallLog,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        base_url: str = BASE_URL,
        thinking_level: str | None = DEFAULT_THINKING_LEVEL,
    ) -> None:
        async def record(call: LlmCall) -> None:
            await call_log.record(
                ExternalCall(call.provider, call.operation, call.status, call.latency_ms, call.error_code)
            )

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

    async def generate(self, request: QuizGenerationRequest) -> object:
        try:
            return await self._client.generate_json(build_prompt(request), RESPONSE_SCHEMA)
        except LlmUnavailableError as exc:
            raise QuizGeneratorUnavailableError(exc.reason, exc.message) from exc
