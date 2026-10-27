"""Bộ tối ưu tham số FSRS: bọc `fsrs.Optimizer` (cần torch, pandas, tqdm trong môi trường worker)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone

from fsrs import Card as FsrsCard
from fsrs import Rating as FsrsRating
from fsrs import ReviewLog as FsrsReviewLog
from fsrs import Scheduler

from app.modules.review.domain.fsrs_profile import (
    SANITY_MAX_INTERVAL_DAYS,
    SANITY_MIN_INTERVAL_DAYS,
    SANITY_STEPS,
    FsrsOptimizerUnavailableError,
    InvalidFsrsParametersError,
    OptimizerLog,
)

_SECONDS_PER_DAY = 86400.0
_SIMULATION_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FsrsLibraryOptimizer:
    """Chạy bộ tối ưu của thư viện trong luồng riêng (việc nặng CPU, không chặn vòng lặp sự kiện)."""

    async def optimize(self, logs: Sequence[OptimizerLog]) -> tuple[float, ...]:
        return await asyncio.to_thread(self._optimize_blocking, tuple(logs))

    def _optimize_blocking(self, logs: tuple[OptimizerLog, ...]) -> tuple[float, ...]:
        try:
            from fsrs import Optimizer

            optimizer = Optimizer(
                [
                    FsrsReviewLog(g.card_id, FsrsRating(int(g.rating)), g.reviewed_at, g.duration_ms)
                    for g in logs
                ]
            )
        except ImportError as exc:
            raise FsrsOptimizerUnavailableError(
                "Thiếu torch/pandas/tqdm cho fsrs.Optimizer trong môi trường này"
            ) from exc
        weights = tuple(float(w) for w in optimizer.compute_optimal_parameters())
        ensure_sane(weights)
        return weights


def ensure_sane(weights: Sequence[float]) -> None:
    """Từ chối bộ trọng số ngoài miền cho phép hoặc cho khoảng ôn mô phỏng bất thường (F08.08, US-HG-03 TC3).

    Mô phỏng một thẻ mới được chấm "Được" liên tiếp: khoảng ôn cuối phải nằm trong [1, 3650] ngày và các
    khoảng tính theo ngày không được giảm dần.
    """
    try:
        scheduler = Scheduler(parameters=weights, enable_fuzzing=False)
    except ValueError as exc:
        raise InvalidFsrsParametersError("Tham số FSRS ngoài miền giá trị cho phép") from exc
    card = FsrsCard(card_id=0, due=_SIMULATION_START)
    now = _SIMULATION_START
    previous_days = 0.0
    for _ in range(SANITY_STEPS):
        card, _log = scheduler.review_card(card, FsrsRating.Good, review_datetime=now)
        days = (card.due - now).total_seconds() / _SECONDS_PER_DAY
        if days >= SANITY_MIN_INTERVAL_DAYS:
            if days < previous_days:
                raise InvalidFsrsParametersError("Khoảng ôn mô phỏng giảm dần bất thường")
            previous_days = days
        now = card.due
    if not SANITY_MIN_INTERVAL_DAYS <= previous_days <= SANITY_MAX_INTERVAL_DAYS:
        raise InvalidFsrsParametersError("Khoảng ôn mô phỏng nằm ngoài miền hợp lý")
