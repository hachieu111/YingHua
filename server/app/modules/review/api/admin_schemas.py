"""Schema API quản trị cho dữ liệu ôn tập và tổng quan người dùng (F13.07)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.admin.api.schemas import AdminUserResponse
from app.modules.admin.application.dto import UserOverview
from app.modules.review.api.schemas import CardStateResponse, StatusCountsResponse
from app.modules.review.application.dto import CardListItem, CardListPage


class UserOverviewResponse(BaseModel):
    """Hồ sơ cơ bản (không mật khẩu băm, không token) và số liệu của một người dùng."""

    user: AdminUserResponse
    vocab_counts: StatusCountsResponse = Field(description="Số mục từ theo trạng thái học")
    vocab_total: int
    cards_total: int
    cards_due: int = Field(description="Số thẻ đến hạn lúc này (cùng quy tắc với /cards/due)")
    reviews_today: int = Field(description="Số lượt ôn hôm nay theo múi giờ của người dùng")
    reviews_total: int
    private_series: int = Field(description="Số truyện riêng tư do người dùng sở hữu")
    quick_uploads: int = Field(description="Số ảnh tải nhanh còn lưu")
    last_active_at: datetime | None = Field(
        description="Lần đăng nhập gần nhất (ISO 8601, UTC); null nếu chưa từng đăng nhập"
    )

    @classmethod
    def from_overview(cls, o: UserOverview) -> UserOverviewResponse:
        a = o.activity
        counts = StatusCountsResponse(**a.status_counts)
        return cls(
            user=AdminUserResponse.from_entity(o.user),
            vocab_counts=counts,
            vocab_total=counts.learning + counts.known + counts.ignored,
            cards_total=a.total_cards,
            cards_due=a.due_now,
            reviews_today=a.reviewed_today,
            reviews_total=a.reviews_total,
            private_series=a.private_series,
            quick_uploads=a.quick_uploads,
            last_active_at=o.user.last_login_at,
        )


class AdminCardResponse(CardStateResponse):
    """Thẻ kèm từ để quản trị viên nhận ra thẻ nào là của từ nào."""

    term: str | None = Field(description="null nếu mục từ không còn")
    pinyin: str | None
    meaning_vi: str | None
    entry_status: str | None = Field(description="learning | known | ignored")

    @classmethod
    def from_item(cls, i: CardListItem) -> AdminCardResponse:
        face = i.face
        return cls(
            **CardStateResponse.from_card(i.card).model_dump(),
            term=face.term if face else None,
            pinyin=face.pinyin if face else None,
            meaning_vi=face.meaning_vi if face else None,
            entry_status=face.status if face else None,
        )


class AdminCardPageResponse(BaseModel):
    items: list[AdminCardResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, p: CardListPage, page: int, size: int) -> AdminCardPageResponse:
        return cls(
            items=[AdminCardResponse.from_item(i) for i in p.items], total=p.total, page=page, size=size
        )
