from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
MODULE_DIR = REPO_DIR / "module xử lí ảnh"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ptud_db"

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    admin_emails: list[str] = []

    # Lưu trữ
    storage_root: Path = BACKEND_DIR / "storage"
    upload_retention_days: int = 7          # ảnh user tự upload giữ 7 ngày
    max_upload_mb: int = 20
    cleanup_interval_minutes: int = 60

    # Pipeline OCR + dịch (module xử lí ảnh)
    pipeline_enabled: bool = True
    pipeline_dir: Path = MODULE_DIR / "mudule xu ly anh"
    yolo_model_path: Path = MODULE_DIR / "mudule xu ly anh" / "models bong bóng" / "model.pt"
    font_dir: Path = MODULE_DIR / "font chữ" / "Font-chu-truyen-tranh-Comic" / "Font chữ truyện tranh Comic"
    xianxia_dict_dir: Path = MODULE_DIR / "từ điển tu tiên"
    pipeline_version: str = "yolo-seg+ppocr4+dict4"
    phash_max_distance: int = 4

    # TTS
    tts_default_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_max_chars: int = 300

    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
