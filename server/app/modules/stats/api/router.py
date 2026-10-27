from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.modules.auth.api.public import Identity, get_identity
from app.modules.stats.api.dependencies import StatsServices, get_stats_services
from app.modules.stats.api.schemas import (
    ActivityResponse,
    LearningOverviewResponse,
    StreakResponse,
    TodayResponse,
)

router = APIRouter(prefix="/stats", tags=["M12 Thống kê"])


@router.get(
    "/overview",
    response_model=LearningOverviewResponse,
    summary="Thống kê học tập cá nhân: số từ, thẻ đến hạn, tỉ lệ nhớ (F12.01)",
)
async def get_overview(
    identity: Identity = Depends(get_identity),
    services: StatsServices = Depends(get_stats_services),
) -> LearningOverviewResponse:
    return LearningOverviewResponse.from_overview(await services.overview.execute(identity))


@router.get(
    "/activity",
    response_model=ActivityResponse,
    summary="Biểu đồ hoạt động theo ngày/tuần/tháng, so với tuần trước (F12.01)",
)
async def get_activity(
    granularity: str = Query(default="day", max_length=8, description="day | week | month"),
    count: int = Query(default=14, ge=1, le=90, description="Số mốc (ngày ≤ 90, tuần ≤ 52, tháng ≤ 24)"),
    identity: Identity = Depends(get_identity),
    services: StatsServices = Depends(get_stats_services),
) -> ActivityResponse:
    return ActivityResponse.from_report(await services.activity.execute(identity, granularity, count))


@router.get(
    "/streak",
    response_model=StreakResponse,
    summary="Chuỗi ngày học, lịch 7 ngày và tiến độ đọc từng truyện (F12.02)",
)
async def get_streak(
    identity: Identity = Depends(get_identity),
    services: StatsServices = Depends(get_stats_services),
) -> StreakResponse:
    return StreakResponse.from_report(await services.streak.execute(identity))


@router.get(
    "/today",
    response_model=TodayResponse,
    summary='Trang chủ "Hôm nay nên học gì": các việc nên làm theo thứ tự cố định (F12.04)',
)
async def get_today(
    identity: Identity = Depends(get_identity),
    services: StatsServices = Depends(get_stats_services),
) -> TodayResponse:
    return TodayResponse.from_plan(await services.today.execute(identity))
