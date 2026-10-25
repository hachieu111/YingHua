from __future__ import annotations

from enum import Enum


class CallStatus(str, Enum):
    """Kết quả một lần gọi dịch vụ ngoài; khớp CHECK của `external_call_logs.status`."""

    OK = "ok"
    TIMEOUT = "timeout"
    INVALID = "invalid"
    ERROR = "error"
