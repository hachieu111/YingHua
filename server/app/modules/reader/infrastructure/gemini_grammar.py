"""Phân tích ngữ pháp câu thoại bằng Google Gemini qua REST (F05.09, US-NH-78).

Dùng client chung `app.core.llm_gemini` (khóa API gửi qua header, không nằm trong URL). Nội dung gửi đi
chỉ gồm câu chữ Hán và bản dịch tự động dùng chung của bong bóng:
không có email, tên, mã người dùng, bản sửa dịch cá nhân hay ghi chú riêng,
và cũng không có trình độ vì kết quả được lưu dùng chung cho mọi người (security.md).
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
from app.modules.reader.application.ports import GrammarRequest
from app.modules.reader.domain.errors import GrammarAnalyzerUnavailableError
from app.modules.reader.domain.grammar import EXAMPLE_MAX_HSK_LEVEL, LABELS, MAX_POINTS

OPERATION = "grammar"

_STRING = {"type": "STRING"}


def _node_schema(children: dict[str, Any] | None = None) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "label": {"type": "STRING", "enum": list(LABELS)},
        "text": _STRING,
        "note": _STRING,
    }
    if children is not None:
        properties["children"] = {"type": "ARRAY", "items": children}
    return {"type": "OBJECT", "properties": properties, "required": ["label", "text"]}


# Gemini không nhận lược đồ đệ quy nên cây được khai báo cố định ba tầng.
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "tree": {"type": "ARRAY", "items": _node_schema(_node_schema(_node_schema()))},
        "points": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "pattern": _STRING,
                    "name": _STRING,
                    "explanation": _STRING,
                    "example_zh": _STRING,
                    "example_vi": _STRING,
                },
                "required": ["pattern", "name", "explanation", "example_zh", "example_vi"],
            },
        },
    },
    "required": ["tree", "points"],
}


def build_prompt(request: GrammarRequest) -> str:
    """Prompt tiếng Việt; chỉ chứa câu chữ Hán và bản dịch tự động dùng chung."""
    labels = ", ".join(f'"{key}" ({vi})' for key, vi in LABELS.items())
    translation = f"Bản dịch tham khảo: {request.translation_vi}\n" if request.translation_vi else ""
    return (
        "Bạn là giáo viên ngữ pháp tiếng Trung cho người học Việt Nam. Hãy phân tích MỘT câu thoại truyện "
        "tranh dưới đây.\n"
        f"Câu: {request.sentence}\n{translation}\n"
        "Yêu cầu:\n"
        '- "tree": cây cú pháp. Mảng "tree" gồm các thành phần ngoài cùng của câu theo ĐÚNG thứ tự trong '
        'câu; mỗi nút có "label", "text" (đoạn chữ lấy nguyên văn từ câu) và "note" (giải thích vai trò '
        'bằng tiếng Việt, không quá 15 từ); thành phần phức tạp thì tách tiếp bằng "children" (tối đa 3 '
        'tầng). Nút có "children" thì "text" bằng đúng phần ghép của các nút con. Nhãn phải đúng vai trò: '
        '"note" và "label" của cùng một nút phải khớp nhau (chủ ngữ gắn "subject", động từ chính gắn '
        '"predicate"). Ghép "text" của mọi nút lá '
        "theo thứ tự (bỏ dấu câu) PHẢI ra đúng câu gốc: không thêm, bớt hay đổi chữ.\n"
        f'- Nhãn "label" chỉ được là một trong: {labels}.\n'
        f'- "points": từ 1 đến {MAX_POINTS} điểm ngữ pháp trọng tâm của câu (bỏ qua nếu câu chỉ có từ '
        'đơn giản). Mỗi điểm có "pattern" (cấu trúc viết bằng chữ Hán, dùng chính các chữ cố định của '
        'cấu trúc, ví dụ "把 + 宾语 + 动词" hoặc "不但……而且……"; chỉ một dạng, không dùng dấu /), "'
        'name" (tên cấu trúc tiếng Việt), '
        '"explanation" (giải thích tiếng Việt, không quá 40 từ), "example_zh" (một câu ví dụ MỚI, ngắn '
        f"5-15 chữ Hán viết liền không có dấu cách, chỉ dùng từ vựng HSK {EXAMPLE_MAX_HSK_LEVEL} trở xuống, "
        'chứa đủ các chữ cố định của "pattern" theo đúng thứ tự) và "example_vi" '
        "(bản dịch tiếng Việt của ví dụ).\n"
        "- Chỉ trả về JSON đúng lược đồ, không thêm chữ nào khác."
    )


class GeminiGrammarAnalyzer:
    """Hiện thực `GrammarAnalyzer` bằng Gemini. Lỗi hạ tầng đổi thành `GrammarAnalyzerUnavailableError`;
    phản hồi bị chặn/cắt giữa chừng/JSON hỏng trả `None` (use case coi là không hợp lệ)."""

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

    async def analyze(self, request: GrammarRequest) -> object:
        try:
            return await self._client.generate_json(build_prompt(request), RESPONSE_SCHEMA)
        except LlmUnavailableError as exc:
            raise GrammarAnalyzerUnavailableError(exc.reason, exc.message) from exc


class DisabledGrammarAnalyzer:
    """Khi LLM tắt hoặc chưa cấu hình khóa: luôn báo không khả dụng."""

    async def analyze(self, request: GrammarRequest) -> object:
        raise GrammarAnalyzerUnavailableError("llm_disabled", "LLM đang tắt")
