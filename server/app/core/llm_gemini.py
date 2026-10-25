"""Client Google Gemini qua REST, dùng chung cho M09 (sinh đề, F09.06) và M08 (Thẻ mở rộng AI, F08.11).

Chỉ dùng `httpx` (đã có trong requirements). Khóa API gửi qua header `x-goog-api-key`, KHÔNG nằm trong URL
hay query nên không lọt vào log của httpx. Client không biết nghiệp vụ: nhận prompt + lược đồ phản hồi và trả
JSON đã phân tích; người gọi chịu trách nhiệm chỉ đưa vào prompt dữ liệu không định danh (security.md).

Mọi lỗi hạ tầng (mạng, quá thời gian, mã HTTP lỗi) đổi thành `LlmUnavailableError`; phản hồi bị chặn, cắt giữa
chừng hoặc JSON hỏng trả `None` (người gọi coi là sai lược đồ).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

logger = logging.getLogger(__name__)

PROVIDER = "gemini"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
API_KEY_HEADER = "x-goog-api-key"
TEMPERATURE = 0.7
DEFAULT_THINKING_LEVEL = "low"
RETRY_BACKOFF_SECONDS = 0.8
MAX_ATTEMPTS = 2  # lần đầu + thử lại tối đa một lần
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
FINISH_OK = "STOP"

REASON_TIMEOUT = "timeout"
REASON_NETWORK = "network"

Sleep = Callable[[float], Awaitable[None]]


class LlmUnavailableError(Exception):
    """LLM không dùng được (mạng, quá thời gian, mã HTTP lỗi). `reason` là `timeout` hoặc `network`."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class LlmCall:
    """Một lần gọi LLM để ghi nhật ký: không chứa nội dung, không chứa khóa."""

    provider: str
    operation: str
    status: str  # ok | timeout | invalid | error
    latency_ms: int
    error_code: str | None = None


CallRecorder = Callable[[LlmCall], Awaitable[None]]


class GeminiClient:
    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float,
        operation: str,
        record: CallRecorder,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        base_url: str = BASE_URL,
        thinking_level: str | None = DEFAULT_THINKING_LEVEL,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._operation = operation
        self._record = record
        self._transport = transport
        self._sleep = sleep
        self._url = f"{base_url}/models/{model}:generateContent"
        self._thinking_level = thinking_level or None

    async def generate_json(self, prompt: str, response_schema: dict[str, Any]) -> object:
        """Gọi `generateContent` một lần (thử lại tối đa một lần khi lỗi tạm thời) và trả JSON phản hồi."""
        deadline = time.monotonic() + self._timeout
        body = self._body(prompt, response_schema)
        thinking_on = self._thinking_level is not None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LlmUnavailableError(REASON_TIMEOUT, "Hết thời gian chờ LLM")
            started = time.monotonic()
            try:
                response = await self._post(body, remaining)
            except httpx.TimeoutException as exc:
                await self._log("timeout", started, "TIMEOUT")
                raise LlmUnavailableError(REASON_TIMEOUT, "Gemini quá thời gian") from exc
            except httpx.HTTPError as exc:
                await self._log("error", started, "NETWORK")
                raise LlmUnavailableError(REASON_NETWORK, "Lỗi mạng khi gọi Gemini") from exc
            if response.status_code == 200:
                return await self._parse(response, started)
            await self._log("error", started, f"HTTP_{response.status_code}")
            if response.status_code == 400 and thinking_on and attempt < MAX_ATTEMPTS:
                # Model không nhận thinkingConfig: bỏ trường này rồi thử lại.
                body["generationConfig"].pop("thinkingConfig", None)
                thinking_on = False
                continue
            retry = response.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS
            if retry and deadline - time.monotonic() > RETRY_BACKOFF_SECONDS:
                await self._sleep(RETRY_BACKOFF_SECONDS)
                continue
            raise LlmUnavailableError(REASON_NETWORK, f"Gemini trả mã {response.status_code}")
        raise LlmUnavailableError(REASON_NETWORK, "Gemini không phản hồi")

    def _body(self, prompt: str, response_schema: dict[str, Any]) -> dict[str, Any]:
        config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
            "temperature": TEMPERATURE,
        }
        if self._thinking_level:
            config["thinkingConfig"] = {"thinkingLevel": self._thinking_level}
        return {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}

    async def _post(self, body: dict[str, Any], timeout: float) -> httpx.Response:
        async with httpx.AsyncClient(transport=self._transport, timeout=timeout) as client:
            return await client.post(
                self._url,
                json=body,
                headers={API_KEY_HEADER: self._api_key.get_secret_value()},
            )

    async def _parse(self, response: httpx.Response, started: float) -> object:
        try:
            data = response.json()
            if data.get("promptFeedback", {}).get("blockReason"):
                return await self._invalid(started, "BLOCKED")
            candidate = data["candidates"][0]
            if candidate.get("finishReason", FINISH_OK) != FINISH_OK:
                return await self._invalid(started, f"FINISH_{candidate['finishReason']}")
            text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
            payload = json.loads(text)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            return await self._invalid(started, "BAD_JSON")
        await self._log("ok", started, None)
        return payload

    async def _invalid(self, started: float, code: str) -> object:
        await self._log("invalid", started, code)
        return None

    async def _log(self, status: str, started: float, error_code: str | None) -> None:
        latency = int((time.monotonic() - started) * 1000)
        await self._record(LlmCall(PROVIDER, self._operation, status, latency, error_code))
        logger.info("Gọi %s %s: %s trong %d ms", PROVIDER, self._operation, status, latency)
