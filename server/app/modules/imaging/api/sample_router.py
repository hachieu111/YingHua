from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.container import Container, get_container
from app.core.uploads import file_url
from app.modules.auth.api.public import Identity, get_identity
from app.modules.imaging.application.use_cases.get_sample_page import GetSamplePageUseCase, SamplePage
from app.modules.imaging.infrastructure.uow import SqlImagingUnitOfWork
from app.modules.library.application.public import LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork

router = APIRouter(tags=["M04 Xử lý ảnh"])


class SampleToken(BaseModel):
    word: str
    pinyin: str | None
    entry_id: int | None


class SampleBubble(BaseModel):
    id: int
    idx: int
    class_name: str
    x: int
    y: int
    w: int
    h: int
    x_pct: float | None
    y_pct: float | None
    w_pct: float | None
    h_pct: float | None
    text_zh: str
    pinyin: str | None
    text_vi: str | None
    tokens: list[SampleToken]
    lines: list[Any]
    style: Any | None


class SampleVariants(BaseModel):
    original: str | None
    inpainted: str | None
    rendered: str | None


class SamplePageResponse(BaseModel):
    page_id: int = Field(description="Dùng cho Hover & Dịch: GET /bubbles/{id}/lookup như trang thật")
    width: int | None
    height: int | None
    variants: SampleVariants
    bubbles: list[SampleBubble]

    @classmethod
    def from_sample(cls, s: SamplePage) -> SamplePageResponse:
        a, t = s.access, s.translation

        def pct(value: int, total: int | None) -> float | None:
            return round(value / total * 100, 4) if total else None

        def tokens(raw: list[Any]) -> list[SampleToken]:
            out: list[SampleToken] = []
            for item in raw:
                word = item.get("word") or item.get("text") if isinstance(item, dict) else None
                if isinstance(word, str) and word:
                    pinyin, entry_id = item.get("pinyin"), item.get("entry_id")
                    out.append(
                        SampleToken(
                            word=word,
                            pinyin=pinyin if isinstance(pinyin, str) else None,
                            entry_id=entry_id if isinstance(entry_id, int) else None,
                        )
                    )
            return out

        return cls(
            page_id=a.page_id,
            width=a.width,
            height=a.height,
            variants=SampleVariants(
                original=file_url(a.original_file_id),
                inpainted=file_url(t.inpainted_file_id),
                rendered=file_url(t.rendered_file_id),
            ),
            bubbles=[
                SampleBubble(
                    id=b.id,
                    idx=b.idx,
                    class_name=b.class_name,
                    x=b.x,
                    y=b.y,
                    w=b.w,
                    h=b.h,
                    x_pct=pct(b.x, a.width),
                    y_pct=pct(b.y, a.height),
                    w_pct=pct(b.w, a.width),
                    h_pct=pct(b.h, a.height),
                    text_zh=b.text_zh,
                    pinyin=b.pinyin,
                    text_vi=b.text_vi,
                    tokens=tokens(b.tokens),
                    lines=list(b.lines),
                    style=b.style,
                )
                for b in s.bubbles
            ],
        )


def _use_case(container: Container) -> GetSamplePageUseCase:
    pages = LibraryPageAccess(lambda: SqlLibraryUnitOfWork(container.session_factory), container.clock)
    return GetSamplePageUseCase(
        lambda: SqlImagingUnitOfWork(container.session_factory), pages, container.system_settings
    )


@router.get(
    "/sample-page",
    response_model=SamplePageResponse,
    summary="Trang mẫu đã xử lý thật để thử Hover & Dịch (F04.16)",
    description="Cần đăng nhập. Chưa cấu hình trang mẫu → 404 `SAMPLE_PAGE_NOT_CONFIGURED`.",
)
async def get_sample_page(
    identity: Identity = Depends(get_identity), container: Container = Depends(get_container)
) -> SamplePageResponse:
    return SamplePageResponse.from_sample(await _use_case(container).execute(identity))
