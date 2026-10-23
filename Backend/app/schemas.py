from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ auth
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu tối đa 72 byte")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int          # giây, của access token


class UserOut(ORM):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class AuthOut(TokenOut):
    user: UserOut


class UpdateMeIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=72)


class SettingsOut(ORM):
    hsk_level: int
    daily_new_cards: int
    daily_review_cap: int
    default_mode: str
    show_pinyin: bool
    tts_voice: str | None


class SettingsIn(BaseModel):
    hsk_level: int | None = Field(None, ge=0, le=9)
    daily_new_cards: int | None = Field(None, ge=0, le=200)
    daily_review_cap: int | None = Field(None, ge=0, le=1000)
    default_mode: Literal["read", "learn"] | None = None
    show_pinyin: bool | None = None
    tts_voice: str | None = None


# ------------------------------------------------------------------ library
class SeriesIn(BaseModel):
    title_vi: str = Field(min_length=1, max_length=255)
    title_zh: str | None = Field(None, max_length=255)
    description: str | None = None
    status: Literal["ongoing", "completed"] = "ongoing"
    public: bool = False          # chỉ admin được tạo truyện thư viện chung


class SeriesPatch(BaseModel):
    title_vi: str | None = Field(None, min_length=1, max_length=255)
    title_zh: str | None = None
    description: str | None = None
    status: Literal["ongoing", "completed"] | None = None


class SeriesOut(ORM):
    id: int
    owner_id: int | None
    visibility: str
    title_zh: str | None
    title_vi: str
    description: str | None
    status: str
    created_at: datetime
    chapter_count: int = 0


class ChapterIn(BaseModel):
    number: Decimal = Field(ge=0, le=99999)
    title: str | None = Field(None, max_length=255)


class ChapterPatch(BaseModel):
    number: Decimal | None = Field(None, ge=0, le=99999)
    title: str | None = Field(None, max_length=255)


class ChapterOut(ORM):
    id: int
    series_id: int
    number: Decimal
    title: str | None
    created_at: datetime
    page_count: int = 0


class ProgressIn(BaseModel):
    last_page_no: int = Field(ge=1)
    mode: Literal["read", "learn"] = "read"
    completed: bool = False


class BubbleEditIn(BaseModel):
    text_vi: str = Field(min_length=1, max_length=2000)


# ------------------------------------------------------------------ dictionary
class SegmentIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class EventIn(BaseModel):
    term: str = Field(min_length=1, max_length=32)
    action: Literal["hover", "lookup", "decompose", "tts"]
    bubble_id: int | None = None


# ------------------------------------------------------------------ vocab
CardType = Literal["recognition", "recall", "listening"]


class VocabIn(BaseModel):
    term: str = Field(min_length=1, max_length=32)
    bubble_id: int | None = None          # bong bóng chứa từ -> lưu ngữ cảnh + ảnh cắt
    custom_meaning: str | None = None
    note: str | None = None
    source: Literal["highlight", "lookup", "suggestion", "manual"] = "highlight"
    card_types: list[CardType] = ["recognition", "recall"]


class VocabPatch(BaseModel):
    custom_meaning: str | None = None
    note: str | None = None
    status: Literal["learning", "known", "ignored"] | None = None


class ContextIn(BaseModel):
    bubble_id: int


# ------------------------------------------------------------------ review
class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=4, description="1=Again, 2=Hard, 3=Good, 4=Easy")
    duration_ms: int | None = Field(None, ge=0)


class FlashcardPatch(BaseModel):
    suspended: bool


# ------------------------------------------------------------------ admin
class AdminUserPatch(BaseModel):
    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None
