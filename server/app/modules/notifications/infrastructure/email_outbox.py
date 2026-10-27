"""Gửi email giả cho môi trường phát triển: ghi nội dung ra file thay vì gửi thật (F14.05).

Thay bằng adapter SMTP khi triển khai thật (cùng port `EmailSender`).
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.modules.notifications.domain.errors import EmailDeliveryError


class FileOutboxEmailSender:
    def __init__(self, outbox_dir: Path) -> None:
        self._dir = outbox_dir

    async def send(self, to_email: str, subject: str, body: str) -> None:
        safe = re.sub(r"[^a-z0-9]+", "_", to_email.lower())[:40]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Tên file do hệ thống tạo (không dùng dữ liệu người dùng làm đường dẫn).
        path = self._dir / f"{stamp}_notify_{safe}_{uuid.uuid4().hex[:6]}.txt"
        content = f"Đến: {to_email}\nChủ đề: {subject}\n\n{body}\n"
        try:
            await asyncio.to_thread(self._write, path, content)
        except OSError as exc:
            raise EmailDeliveryError(str(exc)) from exc

    def _write(self, path: Path, content: str) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
