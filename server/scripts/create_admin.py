"""Tạo tài khoản Quản trị viên đầu tiên, hoặc nâng một tài khoản có sẵn lên Quản trị viên.

SRS (F01.01) không cho tự đăng ký thành Quản trị viên, nên cần một lối vào cho người vận hành hệ thống.

Chạy trong thư mục server/:
    python scripts/create_admin.py admin@example.com
Mật khẩu (khi tạo mới) lấy từ biến môi trường ADMIN_PASSWORD hoặc nhập khi được hỏi; không truyền qua tham số.
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.container import build_container
from app.core.config import get_settings
from app.core.security import hash_password
from app.modules.auth.domain.entities import NewUser, Role
from app.modules.auth.domain.rules import default_display_name, normalize_email, validate_password
from app.modules.auth.infrastructure.uow import SqlAuthUnitOfWork


async def main(email_arg: str) -> None:
    email = normalize_email(email_arg)
    container = build_container(get_settings())
    try:
        async with SqlAuthUnitOfWork(container.session_factory) as uow:
            user = await uow.users.get_by_email(email)
            if user is None:
                password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Mật khẩu cho tài khoản mới: ")
                validate_password(password)
                user = await uow.users.add(
                    NewUser(
                        email, hash_password(password), default_display_name(email), container.clock.now()
                    )
                )
                print(f"Đã tạo tài khoản {email}")
            if user.role is Role.ADMIN:
                print(f"{email} đã là Quản trị viên")
                return
            user.role = Role.ADMIN
            await uow.users.update(user)
            await uow.commit()
            print(f"Đã nâng {email} lên Quản trị viên")
    finally:
        await container.engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Cách dùng: python scripts/create_admin.py <email>")
    asyncio.run(main(sys.argv[1]))
