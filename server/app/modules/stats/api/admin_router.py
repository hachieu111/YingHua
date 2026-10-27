from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, require_admin
from app.modules.stats.api.dependencies import StatsServices, get_stats_services
from app.modules.stats.api.schemas import (
    ActivityResponse,
    LearningOverviewResponse,
    StreakResponse,
    SystemStatsResponse,
    TodayResponse,
)

admin_router = APIRouter(prefix="/admin", tags=["M13 Quản trị"])


@admin_router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="Quản trị: thống kê toàn hệ thống (F12.03)",
)
async def system_stats(
    admin: Identity = Depends(require_admin),
    services: StatsServices = Depends(get_stats_services),
) -> SystemStatsResponse:
    return SystemStatsResponse.from_stats(await services.system.execute(admin))


@admin_router.get(
    "/users/{user_id}/stats/overview",
    response_model=LearningOverviewResponse,
    summary="Quản trị: thống kê học tập của người dùng (F13.07)",
)
async def user_overview(
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: StatsServices = Depends(get_stats_services),
) -> LearningOverviewResponse:
    return LearningOverviewResponse.from_overview(await services.overview.execute(admin, user_id))


@admin_router.get(
    "/users/{user_id}/stats/activity",
    response_model=ActivityResponse,
    summary="Quản trị: biểu đồ hoạt động của người dùng (F13.07)",
)
async def user_activity(
    granularity: str = Query(default="day", max_length=8, description="day | week | month"),
    count: int = Query(default=14, ge=1, le=90),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: StatsServices = Depends(get_stats_services),
) -> ActivityResponse:
    return ActivityResponse.from_report(await services.activity.execute(admin, granularity, count, user_id))


@admin_router.get(
    "/users/{user_id}/stats/streak",
    response_model=StreakResponse,
    summary="Quản trị: chuỗi ngày học và tiến độ đọc của người dùng (F13.07)",
)
async def user_streak(
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: StatsServices = Depends(get_stats_services),
) -> StreakResponse:
    return StreakResponse.from_report(await services.streak.execute(admin, user_id))


@admin_router.get(
    "/users/{user_id}/stats/today",
    response_model=TodayResponse,
    summary='Quản trị: việc "Hôm nay nên học gì" của người dùng (F13.07, chỉ đọc)',
)
async def user_today(
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: StatsServices = Depends(get_stats_services),
) -> TodayResponse:
    return TodayResponse.from_plan(await services.today.execute(admin, user_id))
