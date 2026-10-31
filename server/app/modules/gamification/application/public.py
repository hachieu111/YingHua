"""Bề mặt công khai của M16 cho tác vụ nền và module khác.

- Tác vụ nền F16.10 `finalize_seasons` và F16.11 `evaluate_achievements`.
- Chiều ngược lại (module nguồn báo sự kiện học) đi qua `app.core.learning_events.LearningEventPort`.
"""

from __future__ import annotations

from app.modules.gamification.application.dto import EvaluateReport, FinalizeReport, Notice
from app.modules.gamification.application.ports import GamificationUnitOfWork, NoticeSender
from app.modules.gamification.application.use_cases.evaluate_achievements import (
    EvaluateAchievementsUseCase,
)
from app.modules.gamification.application.use_cases.finalize_seasons import FinalizeSeasonsUseCase
from app.modules.gamification.application.use_cases.purge_minigame_rounds import PurgeMinigameRoundsUseCase

__all__ = [
    "EvaluateAchievementsUseCase",
    "EvaluateReport",
    "FinalizeReport",
    "FinalizeSeasonsUseCase",
    "GamificationUnitOfWork",
    "Notice",
    "NoticeSender",
    "PurgeMinigameRoundsUseCase",
]
