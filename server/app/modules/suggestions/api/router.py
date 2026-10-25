from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.auth.api.public import Identity, get_identity
from app.modules.suggestions.api.dependencies import SuggestionServices, get_suggestion_services
from app.modules.suggestions.api.schemas import (
    AcceptSuggestionRequest,
    ChapterCoverageResponse,
    DismissedPageResponse,
    SeriesRecommendationsResponse,
    SuggestionListResponse,
)
from app.modules.suggestions.domain.rules import DEFAULT_LIMIT, MAX_LIMIT, RECOMMEND_DEFAULT, RECOMMEND_MAX
from app.modules.vocab.api.public import SaveWordResponse

router = APIRouter(tags=["M10 Gợi ý từ"])


@router.get(
    "/chapters/{chapter_id}/suggestions",
    response_model=SuggestionListResponse,
    summary="Từ nên học trong chương, xếp theo mức phù hợp (F10.01)",
    description=(
        "`status=processing` khi còn trang chưa dịch xong (vẫn trả gợi ý từ các trang đã xong). "
        "`hsk_level=null` nghĩa là người học chưa khai báo trình độ: xếp theo tần suất và số lần tra."
    ),
)
async def list_suggestions(
    chapter_id: int,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    identity: Identity = Depends(get_identity),
    services: SuggestionServices = Depends(get_suggestion_services),
) -> SuggestionListResponse:
    return SuggestionListResponse.from_list(
        await services.list_suggestions.execute(identity, chapter_id, limit)
    )


@router.post(
    "/chapters/{chapter_id}/suggestions/accept",
    response_model=SaveWordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Nhận gợi ý vào sổ tay như thao tác lưu từ thông thường (F10.02)",
    description="Từ mới → 201; từ đã có → 200 (thêm ngữ cảnh, F07.02); đã có đúng ngữ cảnh → 409.",
)
async def accept_suggestion(
    chapter_id: int,
    body: AcceptSuggestionRequest,
    response: Response,
    identity: Identity = Depends(get_identity),
    services: SuggestionServices = Depends(get_suggestion_services),
) -> SaveWordResponse:
    result = await services.accept.execute(identity, chapter_id, body.term)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return SaveWordResponse.from_result(result)


@router.get(
    "/suggestions/dismissed",
    response_model=DismissedPageResponse,
    summary="Danh sách từ gợi ý đã bỏ qua, mục Đã bỏ qua (F10.03)",
)
async def list_dismissed(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: SuggestionServices = Depends(get_suggestion_services),
) -> DismissedPageResponse:
    result = await services.list_dismissed.execute(identity, page, size)
    return DismissedPageResponse.from_page(result, page, size)


@router.put(
    "/suggestions/dismissed/{term}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bỏ qua một từ gợi ý ở mọi chương (F10.03)",
)
async def dismiss_suggestion(
    term: str,
    identity: Identity = Depends(get_identity),
    services: SuggestionServices = Depends(get_suggestion_services),
) -> Response:
    await services.dismiss.execute(identity, term)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/suggestions/dismissed/{term}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Khôi phục từ đã bỏ qua; không có trong danh sách cũng 204 (F10.03)",
)
async def restore_suggestion(
    term: str,
    identity: Identity = Depends(get_identity),
    services: SuggestionServices = Depends(get_suggestion_services),
) -> Response:
    await services.restore.execute(identity, term)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/series/recommendations",
    response_model=SeriesRecommendationsResponse,
    summary="Gợi ý 1–3 truyện công khai theo trình độ HSK của người học (F10.04)",
    description=(
        "Truyện có cấp HSK ước tính bằng trình độ hoặc cao hơn 1 cấp; truyện đã có trong Thư viện hay đã đọc "
        "xong xếp sau; sắp theo điểm đánh giá. `needs_level=true` khi chưa khai báo trình độ (kèm truyện phổ "
        "biến cấp thấp). `items` rỗng nghĩa là chưa có truyện phù hợp."
    ),
)
async def recommend_series(
    limit: int = Query(default=RECOMMEND_DEFAULT, ge=1, le=RECOMMEND_MAX),
    identity: Identity = Depends(get_identity),
    services: SuggestionServices = Depends(get_suggestion_services),
) -> SeriesRecommendationsResponse:
    return SeriesRecommendationsResponse.from_result(await services.recommend_series.execute(identity, limit))


@router.get(
    "/chapters/{chapter_id}/vocab-coverage",
    response_model=ChapterCoverageResponse,
    summary="Độ phủ từ vựng của chương: đã nắm X/Y từ HSK n (F10.05)",
    description=(
        "Y = số từ khác nhau trong chương có cấp HSK 1..n; X = số từ đã có trong sổ tay (mọi trạng thái). "
        "`status`: ready | processing (còn trang chưa xong, tạm tính) | empty (không có từ để tính, "
        "đừng hiện 0/0). `needs_level=true`: chưa khai báo trình độ, tính trên mọi từ có cấp HSK."
    ),
)
async def chapter_vocab_coverage(
    chapter_id: int,
    identity: Identity = Depends(get_identity),
    services: SuggestionServices = Depends(get_suggestion_services),
) -> ChapterCoverageResponse:
    return ChapterCoverageResponse.from_coverage(await services.coverage.execute(identity, chapter_id))
