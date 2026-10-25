"""Hàm dùng chung cho test API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import text

PASSWORD = "matkhau-dung-123"


@dataclass
class Account:
    id: int
    email: str
    password: str
    access: str
    refresh: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access}"}


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


async def register(
    client: httpx.AsyncClient,
    email: str | None = None,
    password: str = PASSWORD,
    display_name: str | None = None,
) -> Account:
    email = email or unique_email()
    body: dict[str, Any] = {"email": email, "password": password}
    if display_name:
        body["display_name"] = display_name
    res = await client.post("/api/v1/auth/register", json=body)
    assert res.status_code == 201, res.text
    data = res.json()
    return Account(
        data["user"]["id"],
        email.lower(),
        password,
        data["tokens"]["access_token"],
        data["tokens"]["refresh_token"],
    )


async def login(client: httpx.AsyncClient, account: Account) -> Account:
    res = await client.post("/api/v1/auth/login", json={"email": account.email, "password": account.password})
    assert res.status_code == 200, res.text
    tokens = res.json()["tokens"]
    return Account(
        account.id, account.email, account.password, tokens["access_token"], tokens["refresh_token"]
    )


async def make_admin(app: FastAPI, client: httpx.AsyncClient) -> Account:
    """Tạo tài khoản rồi nâng lên Quản trị viên trực tiếp trong CSDL kiểm thử (chỉ dùng để dựng dữ liệu)."""
    account = await register(client)
    factory = app.state.container.session_factory
    async with factory() as session:
        await session.execute(text("UPDATE users SET role = 'admin' WHERE id = :id"), {"id": account.id})
        await session.commit()
    return account


def error_code(res: httpx.Response) -> str:
    return str(res.json()["error"]["code"])


def png_bytes(color: tuple[int, int, int] = (200, 30, 30), size: tuple[int, int] = (24, 36)) -> bytes:
    """Ảnh PNG thật, nhỏ; mỗi màu cho một sha256 khác nhau."""
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()
