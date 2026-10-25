"""Cấu hình ứng dụng, đọc từ biến môi trường / server/.env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = SERVER_DIR.parent

# Mặc định trỏ vào thư mục `module xử lí ảnh/` ở gốc repo (ghi đè bằng PIPELINE_DIR... trong .env).
MODULE_DIR = REPO_DIR / "module xử lí ảnh"
DEFAULT_PIPELINE_DIR = MODULE_DIR / "mudule xu ly anh"
DEFAULT_FONT_DIR = MODULE_DIR / "font chữ" / "Font-chu-truyen-tranh-Comic" / "Font chữ truyện tranh Comic"
DEFAULT_XIANXIA_DICT_DIR = MODULE_DIR / "từ điển tu tiên"


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
    password_reset_minutes: int = 30
    login_max_attempts_per_email: int = 5
    login_max_attempts_per_ip: int = 30
    login_attempt_window_minutes: int = 15

    # HTTP
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Lưu trữ
    storage_dir: Path = Path("storage")
    max_upload_mb: int = 10
    upload_retention_days: int = 7
    cleanup_interval_minutes: int = 60

    # Giới hạn nghiệp vụ (docs/modules-functions.md §1.2)
    guest_lookup_limit: int = 5
    guest_session_hours: int = 24
    note_max_chars: int = 1000
    quiz_question_count: int = 10
    quiz_min_words: int = 10
    quiz_daily_llm_limit: int = 5  # số đề LLM mỗi người mỗi ngày; vượt thì dùng đề dự phòng (F13.05)
    llm_enabled: bool = False  # công tắc tạm; quản trị bật/tắt trong CSDL thuộc F13.05 (giai đoạn 6)
    llm_timeout_seconds: float = 20.0
    llm_provider: str = "gemini"
    llm_api_key: SecretStr | None = None  # chỉ ở .env; không bao giờ log hay đưa vào URL
    llm_model: str = "gemini-flash-lite-latest"
    # Mức "suy nghĩ" của Gemini; "low" giữ đề 10 câu trong khoảng 6–12 s (đo 25/10/2026). Rỗng = không gửi.
    llm_thinking_level: str = "low"
    ai_note_daily_limit: int = 20  # số lần gọi LLM tạo Thẻ mở rộng AI mỗi người mỗi ngày (F08.11)
    ai_note_regenerate_limit: int = 3  # số lần "Tạo lại" Thẻ mở rộng AI cho mỗi mục từ (F08.11)
    tts_timeout_seconds: float = 10.0
    tts_enabled: bool = True  # công tắc tạm; quản trị bật/tắt trong CSDL thuộc F13.05 (giai đoạn 6)
    guest_tts_max_requests: int = 20  # lượt Khách gọi dịch vụ TTS (không tính cache) mỗi cửa sổ
    guest_tts_window_minutes: int = 10

    # Pipeline xử lý ảnh (M04) và tác vụ nền (M15)
    pipeline_enabled: bool = False
    pipeline_dir: Path = DEFAULT_PIPELINE_DIR
    yolo_model_path: Path = DEFAULT_PIPELINE_DIR / "models bong bóng" / "model.pt"
    font_dir: Path = DEFAULT_FONT_DIR
    xianxia_dict_dir: Path = DEFAULT_XIANXIA_DICT_DIR
    worker_poll_seconds: float = Field(default=3.0, gt=0)
    job_max_attempts: int = 2
    job_stale_minutes: int = 15

    # Log
    log_level: str = "INFO"
    log_json: bool = False

    @field_validator("storage_dir", "pipeline_dir", "yolo_model_path", "font_dir", "xianxia_dict_dir")
    @classmethod
    def _resolve_path(cls, value: Path) -> Path:
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
