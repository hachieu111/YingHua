"""Gói các kho của M16 trên một phiên SQLAlchemy và Unit of Work độc lập của M16."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.gamification.infrastructure.achievement_repository import SqlAchievementRepository
from app.modules.gamification.infrastructure.character_source import SqlCharacterSource
from app.modules.gamification.infrastructure.leaderboard_repository import SqlLeaderboardRepository
from app.modules.gamification.infrastructure.metric_reader import SqlMetricReader
from app.modules.gamification.infrastructure.minigame_repository import SqlMinigameRepository
from app.modules.gamification.infrastructure.readers import SqlActivityReader, SqlUserDirectory
from app.modules.gamification.infrastructure.reward_gateway import SessionRewardGateway
from app.modules.gamification.infrastructure.season_repository import SqlSeasonRepository
from app.modules.gamification.infrastructure.xp_repository import SqlXpRepository


class SqlGamificationStore:
    """Mọi kho của M16 dùng chung một phiên, nên chạy được trong giao dịch của module khác (F16.02)."""

    def __init__(self, session: AsyncSession) -> None:
        self.xp = SqlXpRepository(session)
        self.activity = SqlActivityReader(session)
        self.users = SqlUserDirectory(session)
        self.seasons = SqlSeasonRepository(session)
        self.leaderboard = SqlLeaderboardRepository(session)
        self.achievements = SqlAchievementRepository(session)
        self.metrics = SqlMetricReader(session)
        self.minigames = SqlMinigameRepository(session)
        self.chars = SqlCharacterSource(session)
        self.rewards = SessionRewardGateway(session)


class SqlGamificationUnitOfWork(SqlAlchemyUnitOfWork):
    xp: SqlXpRepository
    activity: SqlActivityReader
    users: SqlUserDirectory
    seasons: SqlSeasonRepository
    leaderboard: SqlLeaderboardRepository
    achievements: SqlAchievementRepository
    metrics: SqlMetricReader
    minigames: SqlMinigameRepository
    chars: SqlCharacterSource
    rewards: SessionRewardGateway

    def _init_repositories(self) -> None:
        store = SqlGamificationStore(self.session)
        self.xp = store.xp
        self.activity = store.activity
        self.users = store.users
        self.seasons = store.seasons
        self.leaderboard = store.leaderboard
        self.achievements = store.achievements
        self.metrics = store.metrics
        self.minigames = store.minigames
        self.chars = store.chars
        self.rewards = store.rewards
