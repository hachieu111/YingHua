from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.review.application.ports import FsrsParameterOptimizer, ReviewUnitOfWork
from app.modules.review.domain.fsrs_profile import (
    DEFAULT_DESIRED_RETENTION,
    MAX_OPTIMIZER_LOGS,
    MIN_NEW_REVIEWS_BEFORE_REOPTIMIZE,
    FsrsOptimizerUnavailableError,
    FsrsProfile,
    InvalidFsrsParametersError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OptimizeConfig:
    min_reviews: int
    interval_days: int
    max_users_per_run: int


@dataclass(frozen=True, slots=True)
class OptimizeReport:
    candidates: int
    optimized: int
    kept: int  # tham số mới không hợp lệ/bất thường: giữ tham số cũ
    failed: int
    unavailable: bool = False  # môi trường worker thiếu bộ tối ưu

    def as_summary(self) -> dict[str, int | bool]:
        return {
            "candidates": self.candidates,
            "optimized": self.optimized,
            "kept": self.kept,
            "failed": self.failed,
            "unavailable": self.unavailable,
        }


class OptimizeFsrsParametersUseCase:
    """F08.08 — Tối ưu tham số FSRS riêng cho từng người học (US-HG-03).

    Chạy theo chu kỳ dài do F15.03 kích hoạt. Chỉ chọn người học đủ số lượt ôn tối thiểu (người ít lượt ôn
    giữ tham số mặc định chung) và, nếu đã từng tối ưu, phải có thêm lượt ôn mới. Tham số mới phải hợp lệ và
    cho lịch ôn mô phỏng bình thường, nếu không thì giữ tham số cũ và ghi nhật ký. Lỗi một người không chặn
    người kế tiếp. Tham số mới chỉ áp dụng cho lượt chấm sau đó; lịch các thẻ đã xếp không bị tính lại.
    """

    def __init__(
        self,
        uow_factory: Callable[[], ReviewUnitOfWork],
        optimizer: FsrsParameterOptimizer,
        config: OptimizeConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._optimizer = optimizer
        self._config = config

    async def execute(self, now: datetime) -> OptimizeReport:
        stale_before = now - timedelta(days=self._config.interval_days)
        async with self._uow_factory() as uow:
            user_ids = await uow.fsrs_profiles.users_to_optimize(
                self._config.min_reviews,
                MIN_NEW_REVIEWS_BEFORE_REOPTIMIZE,
                stale_before,
                self._config.max_users_per_run,
            )
        optimized = kept = failed = 0
        for user_id in user_ids:
            try:
                await self._optimize_one(user_id, now)
            except FsrsOptimizerUnavailableError:
                logger.warning("Bộ tối ưu FSRS không dùng được trong môi trường này, bỏ qua lượt chạy")
                return OptimizeReport(len(user_ids), optimized, kept, failed, unavailable=True)
            except InvalidFsrsParametersError as exc:
                logger.warning("Giữ tham số FSRS cũ của người dùng %s: %s", user_id, exc)
                kept += 1
            except Exception:  # cô lập lỗi từng người (F08.08): ghi log rồi tiếp tục người kế tiếp
                logger.exception("Tối ưu FSRS lỗi cho người dùng %s", user_id)
                failed += 1
            else:
                optimized += 1
        return OptimizeReport(len(user_ids), optimized, kept, failed)

    async def _optimize_one(self, user_id: int, now: datetime) -> None:
        async with self._uow_factory() as uow:
            logs = await uow.logs.list_for_optimizer(user_id, MAX_OPTIMIZER_LOGS)
            current = await uow.fsrs_profiles.get(user_id)
        weights = await self._optimizer.optimize(logs)
        retention = current.desired_retention if current else DEFAULT_DESIRED_RETENTION
        async with self._uow_factory() as uow:
            await uow.fsrs_profiles.save(user_id, FsrsProfile(weights, retention), len(logs), now)
            await uow.commit()
        logger.info("Đã tối ưu tham số FSRS cho người dùng %s từ %d lượt ôn", user_id, len(logs))
