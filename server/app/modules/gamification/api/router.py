"""Router M16 Gamification: XP, nhiệm vụ, mục tiêu tuần, bảng xếp hạng, mùa thi đua, huy hiệu, mini-game.

Không có endpoint nào để trình trình duyệt gửi XP: XP chỉ do máy chủ ghi khi hoàn tất hành động học.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.public import Identity, get_identity
from app.modules.gamification.api.dependencies import GamificationServices, get_gamification_services
from app.modules.gamification.api.schemas import (
    AchievementResponse,
    BladeBestResponse,
    CurrentSeasonResponse,
    EquippedResponse,
    EquipRequest,
    LeaderboardResponse,
    MeResponse,
    QuestsTodayResponse,
    RoundRequest,
    RoundResponse,
    SeasonHistoryResponse,
    SessionResponse,
    SubmitSessionRequest,
    WeakRadicalsResponse,
    WeeklyActivityResponse,
    WeeklyGoalResponse,
)
from app.modules.gamification.application.dto import BuildRoundCommand, SubmitRoundCommand
from app.modules.gamification.domain.blade_rules import BladeEvent
from app.modules.gamification.domain.entities import LeaderboardMetric, LeaderboardPeriod
from app.modules.gamification.domain.season_rules import LEADERBOARD_DEFAULT_SIZE, LEADERBOARD_MAX_SIZE

router = APIRouter(prefix="/gamification", tags=["M16 Gamification"])


@router.get("/me", response_model=MeResponse, summary="XP hôm nay, XP mùa, tổng XP, hạng mùa (F16.03)")
async def get_me(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> MeResponse:
    return MeResponse.of(await services.me.execute(identity))


@router.get(
    "/me/weekly-activity",
    response_model=WeeklyActivityResponse,
    summary="Hoạt động tuần của bạn: XP từng ngày Thứ Hai đến Chủ Nhật (F16.03)",
)
async def get_weekly_activity(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> WeeklyActivityResponse:
    return WeeklyActivityResponse.of(await services.weekly_activity.execute(identity))


@router.get(
    "/quests/today",
    response_model=QuestsTodayResponse,
    summary="Nhiệm vụ ngày kèm tiến độ; thưởng được cộng tự động (F16.04)",
)
async def get_quests_today(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> QuestsTodayResponse:
    return QuestsTodayResponse.of(await services.quests.execute(identity))


@router.get(
    "/weekly-goal", response_model=WeeklyGoalResponse, summary="Mục tiêu tuần và phần thưởng (F16.05)"
)
async def get_weekly_goal(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> WeeklyGoalResponse:
    return WeeklyGoalResponse.of(await services.weekly_goal.execute(identity))


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Bảng xếp hạng theo chỉ số và khoảng thời gian; không lộ email (F16.07, F16.08)",
)
async def get_leaderboard(
    metric: Literal["exp", "vocab", "pages", "streak"] = Query(default="exp"),
    period: Literal["week", "month", "all"] = Query(default="week"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=LEADERBOARD_DEFAULT_SIZE, ge=1, le=LEADERBOARD_MAX_SIZE),
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> LeaderboardResponse:
    view = await services.leaderboard.execute(
        identity, LeaderboardMetric(metric), LeaderboardPeriod(period), page, size
    )
    return LeaderboardResponse.of(view)


@router.get(
    "/seasons/current",
    response_model=CurrentSeasonResponse,
    summary="Mùa thi đua hiện hành, đếm ngược, bậc thưởng và hạng của bạn (F16.09)",
)
async def get_current_season(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> CurrentSeasonResponse:
    return CurrentSeasonResponse.of(await services.current_season.execute(identity))


@router.get(
    "/seasons/me",
    response_model=SeasonHistoryResponse,
    summary="Kết quả các mùa đã chốt của bạn (F16.09)",
)
async def list_my_seasons(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> SeasonHistoryResponse:
    return SeasonHistoryResponse.of(await services.my_seasons.execute(identity, page, size), page, size)


@router.get(
    "/achievements",
    response_model=list[AchievementResponse],
    summary="Danh sách huy hiệu kèm cấp, tiến độ và trạng thái đang đeo (F16.11)",
)
async def list_achievements(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> list[AchievementResponse]:
    return [AchievementResponse.of(a) for a in await services.achievements.execute(identity)]


@router.put(
    "/achievements/equipped",
    response_model=EquippedResponse,
    summary="Đeo hoặc tháo huy hiệu đã mở khóa; mỗi người tối đa một (F16.12)",
)
async def equip_achievement(
    body: EquipRequest,
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> EquippedResponse:
    return EquippedResponse.of(await services.equip.execute(identity, body.achievement_code))


@router.get(
    "/minigames/radicals/weak",
    response_model=WeakRadicalsResponse,
    summary="Bộ thủ bạn hay quên, gợi ý cho mini-game Gõ pinyin chém chữ (F16.01)",
)
async def get_weak_radicals(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> WeakRadicalsResponse:
    return WeakRadicalsResponse.of(await services.weak_radicals.execute(identity))


@router.post(
    "/minigames/blade/rounds",
    response_model=RoundResponse,
    summary="Dựng 100 mục cho một ván Gõ pinyin chém chữ theo cấp HSK hoặc bộ thủ yếu (F16.01)",
)
async def build_round(
    body: RoundRequest,
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> RoundResponse:
    command = BuildRoundCommand(body.mode, body.hsk_band, body.radical)
    return RoundResponse.of(await services.build_round.execute(identity, command))


@router.post(
    "/minigames/blade/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Nộp kết quả ván; máy chủ chấm lại điểm, combo và cộng XP (F16.01)",
)
async def submit_session(
    body: SubmitSessionRequest,
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> SessionResponse:
    events = [BladeEvent(e.index, e.result == "hit", e.ms) for e in body.events]
    command = SubmitRoundCommand(body.round_id, events, body.typos, body.duration_ms)
    return SessionResponse.of(await services.submit_round.execute(identity, command))


@router.get(
    "/minigames/blade/best",
    response_model=list[BladeBestResponse],
    summary="Kỷ lục Gõ pinyin chém chữ của bạn theo cấp HSK / bộ thủ yếu (F16.01)",
)
async def get_blade_best(
    identity: Identity = Depends(get_identity),
    services: GamificationServices = Depends(get_gamification_services),
) -> list[BladeBestResponse]:
    return [BladeBestResponse.of(b) for b in await services.blade_best.execute(identity)]
