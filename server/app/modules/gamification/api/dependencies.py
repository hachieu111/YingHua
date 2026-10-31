from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.container import Container, get_container
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.application.use_cases.build_round import BuildRoundUseCase
from app.modules.gamification.application.use_cases.equip_achievement import EquipAchievementUseCase
from app.modules.gamification.application.use_cases.get_blade_best import GetBladeBestUseCase
from app.modules.gamification.application.use_cases.get_current_season import GetCurrentSeasonUseCase
from app.modules.gamification.application.use_cases.get_leaderboard import GetLeaderboardUseCase
from app.modules.gamification.application.use_cases.get_me import GetMyGamificationUseCase
from app.modules.gamification.application.use_cases.get_quests_today import GetQuestsTodayUseCase
from app.modules.gamification.application.use_cases.get_weak_radicals import GetWeakRadicalsUseCase
from app.modules.gamification.application.use_cases.get_weekly_activity import GetWeeklyActivityUseCase
from app.modules.gamification.application.use_cases.get_weekly_goal import GetWeeklyGoalUseCase
from app.modules.gamification.application.use_cases.list_achievements import ListAchievementsUseCase
from app.modules.gamification.application.use_cases.list_my_seasons import ListMySeasonsUseCase
from app.modules.gamification.application.use_cases.submit_round import SubmitRoundUseCase
from app.modules.gamification.infrastructure.public import SqlGamificationUnitOfWork


@dataclass(slots=True)
class GamificationServices:
    me: GetMyGamificationUseCase
    weekly_activity: GetWeeklyActivityUseCase
    quests: GetQuestsTodayUseCase
    weekly_goal: GetWeeklyGoalUseCase
    leaderboard: GetLeaderboardUseCase
    current_season: GetCurrentSeasonUseCase
    my_seasons: ListMySeasonsUseCase
    achievements: ListAchievementsUseCase
    equip: EquipAchievementUseCase
    weak_radicals: GetWeakRadicalsUseCase
    build_round: BuildRoundUseCase
    submit_round: SubmitRoundUseCase
    blade_best: GetBladeBestUseCase


def build_gamification_services(container: Container) -> GamificationServices:
    def uow_factory() -> GamificationUnitOfWork:
        return SqlGamificationUnitOfWork(container.session_factory)

    clock = container.clock
    return GamificationServices(
        me=GetMyGamificationUseCase(uow_factory, clock),
        weekly_activity=GetWeeklyActivityUseCase(uow_factory, clock),
        quests=GetQuestsTodayUseCase(uow_factory, clock),
        weekly_goal=GetWeeklyGoalUseCase(uow_factory, clock),
        leaderboard=GetLeaderboardUseCase(uow_factory, clock),
        current_season=GetCurrentSeasonUseCase(uow_factory, clock),
        my_seasons=ListMySeasonsUseCase(uow_factory),
        achievements=ListAchievementsUseCase(uow_factory),
        equip=EquipAchievementUseCase(uow_factory),
        weak_radicals=GetWeakRadicalsUseCase(uow_factory, clock),
        build_round=BuildRoundUseCase(uow_factory, clock),
        submit_round=SubmitRoundUseCase(uow_factory, container.notices, clock),
        blade_best=GetBladeBestUseCase(uow_factory),
    )


def get_gamification_services(container: Container = Depends(get_container)) -> GamificationServices:
    return build_gamification_services(container)
