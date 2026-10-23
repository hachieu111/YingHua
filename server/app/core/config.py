"""Cấu hình ứng dụng, đọc từ biến môi trường / server/.env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = SERVER_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVER_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "YingHua API"

    # CSDL
    database_url: str
    test_database_url: str | None = None
    db_pool_size: int = 10
    db_echo: bool = False

    # Xác thực
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    password_min_length: int = 8
    password_reset_minutes: int = 30
    admin_emails: list[str] = Field(default_factory=list)

    # HTTP
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Lưu trữ
    storage_dir: Path = Path("storage")
    max_upload_mb: int = 10
    upload_retention_days: int = 7
    cleanup_interval_minutes: int = 60

    # Giới hạn nghiệp vụ (docs/modules-functions.md §1.2)
    guest_lookup_limit: int = 5
    note_max_chars: int = 1000
    quiz_size: int = 10
    quiz_min_words: int = 10
    llm_timeout_seconds: float = 20.0
    tts_timeout_seconds: float = 10.0

    # Log
    log_level: str = "INFO"
    log_json: bool = False

    @field_validator("storage_dir")
    @classmethod
    def _resolve_storage_dir(cls, value: Path) -> Path:
        # Đường dẫn tương đối tính từ thư mục server/, không phụ thuộc thư mục đang chạy lệnh.
        return value if value.is_absolute() else SERVER_DIR / value

    @field_validator("jwt_secret")
    @classmethod
    def _check_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET phải dài tối thiểu 32 ký tự")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # các trường bắt buộc đọc từ biến môi trường / .env
