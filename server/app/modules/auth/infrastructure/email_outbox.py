"""Gửi email giả cho môi trường phát triển: ghi nội dung ra file thay vì gửi thật.

Thay bằng adapter SMTP khi triển khai thật (cùng port `EmailSender`).
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


class FileOutboxEmailSender:
    def __init__(self, outbox_dir: Path) -> None:
        self._dir = outbox_dir

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        body = (
            f"Đến: {to_email}\n"
            "Chủ đề: Đặt lại mật khẩu YingHua\n\n"
            f"Nhấn vào liên kết sau để đặt lại mật khẩu (hiệu lực 30 phút, dùng một lần):\n{reset_link}\n"
        )
        safe = re.sub(r"[^a-z0-9]+", "_", to_email.lower())[:40]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self._dir / f"{stamp}_{safe}_{uuid.uuid4().hex[:6]}.txt"
        await asyncio.to_thread(self._write, path, body)

    def _write(self, path: Path, body: str) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
