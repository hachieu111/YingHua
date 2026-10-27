from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.container import Container, get_container
from app.modules.auth.infrastructure.public import SqlUserCountsSource
from app.modules.imaging.infrastructure.public import SqlImagingCountsSource
from app.modules.library.infrastructure.public import SqlContentCountsSource, SqlReadingProgressSource
from app.modules.review.api.dependencies import build_learning_facts_source
from app.modules.stats.application.ports import StatsUnitOfWork
from app.modules.stats.application.use_cases.get_activity_series import GetActivitySeriesUseCase
from app.modules.stats.application.use_cases.get_learning_overview import GetLearningOverviewUseCase
from app.modules.stats.application.use_cases.get_streak import GetStreakUseCase
from app.modules.stats.application.use_cases.get_system_stats import GetSystemStatsUseCase
from app.modules.stats.application.use_cases.get_today_plan import GetTodayPlanUseCase
from app.modules.stats.domain.today import TodayRules
from app.modules.stats.infrastructure.public import SqlStatsUnitOfWork
from app.modules.stats.infrastructure.timezone_source import SettingsTimezoneSource
from app.modules.stats.infrastructure.today_sources import (
    ReviewWeakWordsSource,
    SettingsWeeklyGoalSource,
    SuggestionsChapterSource,
)
from app.modules.suggestions.api.dependencies import build_suggestion_services
from app.modules.vocab.infrastructure.public import SqlVocabCountsSource


@dataclass(slots=True)
class StatsServices:
    overview: GetLearningOverviewUseCase
    activity: GetActivitySeriesUseCase
    streak: GetStreakUseCase
    system: GetSystemStatsUseCase
    today: GetTodayPlanUseCase


def build_stats_services(container: Container) -> StatsServices:
    factory = container.session_factory

    def uow_factory() -> StatsUnitOfWork:
        return SqlStatsUnitOfWork(factory)

    timezones = SettingsTimezoneSource(factory)
    settings = container.settings
    rules = TodayRules(
        due_priority_threshold=settings.today_due_priority_threshold,
        quiz_low_words=settings.today_quiz_low_words,
        quiz_low_retrievability=settings.today_quiz_low_retrievability,
        max_items=settings.today_max_items,
        quiz_min_words=settings.quiz_min_words,
    )
    return StatsServices(
        overview=GetLearningOverviewUseCase(uow_factory, build_learning_facts_source(container), timezones),
        activity=GetActivitySeriesUseCase(uow_factory, timezones, container.clock),
        streak=GetStreakUseCase(uow_factory, timezones, SqlReadingProgressSource(factory), container.clock),
        system=GetSystemStatsUseCase(
            uow_factory,
            SqlUserCountsSource(factory),
            SqlContentCountsSource(factory),
            SqlImagingCountsSource(factory),
            SqlVocabCountsSource(factory),
            container.clock,
        ),
        today=GetTodayPlanUseCase(
            uow_factory,
            build_learning_facts_source(container),
            SqlReadingProgressSource(factory),
            ReviewWeakWordsSource(factory),
            SettingsWeeklyGoalSource(factory),
            SuggestionsChapterSource(build_suggestion_services(container).list_suggestions),
            timezones,
            rules,
            container.clock,
        ),
    )


def get_stats_services(container: Container = Depends(get_container)) -> StatsServices:
    return build_stats_services(container)
