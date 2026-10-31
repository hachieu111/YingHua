"""M03 — use case với repository giả (không cần CSDL): F03.04, F03.05, F03.10, F03.14."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity, Role
from app.modules.library.application.access import load_editable_series
from app.modules.library.application.dto import SeriesInput
from app.modules.library.application.use_cases.create_series import CreateSeriesUseCase
from app.modules.library.application.use_cases.get_series import GetSeriesUseCase
from app.modules.library.application.use_cases.rate_series import RateSeriesUseCase
from app.modules.library.domain.entities import (
    Actor,
    NewSeries,
    RatingSummary,
    Series,
    SeriesStatus,
    SeriesView,
    Visibility,
)
from app.modules.library.domain.errors import (
    InvalidRatingError,
    PublishRequiresAdminError,
    SeriesNotFoundError,
    SeriesTitleDuplicateError,
)
from tests.conftest import FixedClock


class FakeSeriesRepo:
    def __init__(self) -> None:
        self.items: dict[int, Series] = {}

    async def get(self, series_id: int) -> Series | None:
        return self.items.get(series_id)

    async def add(self, new: NewSeries) -> Series:
        series = Series(
            id=len(self.items) + 1,
            owner_id=new.owner_id,
            visibility=new.visibility,
            title_vi=new.title_vi,
            status=new.status,
            created_at=new.created_at,
            updated_at=new.created_at,
            created_by=new.created_by,
            genres=list(new.genres),
        )
        self.items[series.id] = series
        return series

    async def owner_has_title(self, owner_id: int, title_vi: str, exclude_id: int | None = None) -> bool:
        return any(
            s.owner_id == owner_id and s.title_vi.lower() == title_vi.lower() for s in self.items.values()
        )

    async def get_view(self, series_id: int, viewer_id: int | None, trial_only: bool) -> SeriesView | None:
        series = self.items.get(series_id)
        return SeriesView(series, 0, None, 0, False, False) if series else None


class FakeAudit:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    async def add(self, *args: Any) -> None:
        self.calls.append(args)


class FakeRatings:
    def __init__(self) -> None:
        self.stars: dict[int, int] = {}

    async def upsert(self, user_id: int, series_id: int, stars: int, now: datetime) -> None:
        self.stars[user_id] = stars

    async def summary(self, series_id: int) -> RatingSummary:
        values = list(self.stars.values())
        return RatingSummary(sum(values) / len(values) if values else None, len(values))


class FakeUow:
    def __init__(self) -> None:
        self.series = FakeSeriesRepo()
        self.audit = FakeAudit()
        self.ratings = FakeRatings()
        self.committed = False

    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _identity(user_id: int, role: Role = Role.USER) -> Identity:
    return Identity(user_id=user_id, role=role, session_id="s")


@pytest.fixture
def uow() -> FakeUow:
    return FakeUow()


async def test_create_private_series_sets_owner_and_blocks_duplicate_until_confirmed(
    uow: FakeUow, fixed_clock: FixedClock
) -> None:
    """US-NH-10: truyện mới luôn riêng tư; trùng tên chỉ tạo khi xác nhận."""
    use_case = CreateSeriesUseCase(lambda: uow, fixed_clock)  # type: ignore[arg-type,return-value]
    first = await use_case.execute(_identity(5), SeriesInput(title_vi="  Hoa  Hồng "))
    assert (first.series.owner_id, first.series.visibility, first.series.title_vi) == (
        5,
        Visibility.PRIVATE,
        "Hoa Hồng",
    )
    assert first.can_edit and uow.committed
    with pytest.raises(SeriesTitleDuplicateError):
        await use_case.execute(_identity(5), SeriesInput(title_vi="hoa hồng"))
    again = await use_case.execute(_identity(5), SeriesInput(title_vi="hoa hồng", confirm_duplicate=True))
    assert again.series.id != first.series.id


async def test_learner_cannot_publish_but_admin_publish_is_audited(
    uow: FakeUow, fixed_clock: FixedClock
) -> None:
    """US-QT-04: chỉ quản trị viên đăng truyện công khai; thao tác được ghi nhật ký (F13.06)."""
    use_case = CreateSeriesUseCase(lambda: uow, fixed_clock)  # type: ignore[arg-type,return-value]
    with pytest.raises(PublishRequiresAdminError):
        await use_case.execute(_identity(5), SeriesInput(title_vi="X", visibility="public"))
    view = await use_case.execute(
        _identity(1, Role.ADMIN), SeriesInput(title_vi="Chung", visibility="public")
    )
    assert view.series.owner_id is None and view.series.visibility is Visibility.PUBLIC
    assert [c[1] for c in uow.audit.calls] == ["series.create"]


async def test_private_series_of_another_user_is_not_found(uow: FakeUow, fixed_clock: FixedClock) -> None:
    """US-NH-15: không lộ sự tồn tại của truyện riêng tư."""
    created = await CreateSeriesUseCase(lambda: uow, fixed_clock).execute(  # type: ignore[arg-type,return-value]
        _identity(5), SeriesInput(title_vi="Riêng")
    )
    get = GetSeriesUseCase(lambda: uow, fixed_clock)  # type: ignore[arg-type,return-value]
    with pytest.raises(SeriesNotFoundError):
        await get.execute(_identity(6), created.series.id)
    with pytest.raises(SeriesNotFoundError):
        await get.execute(None, created.series.id)


async def test_rating_validates_range_and_rejects_hidden_series(
    uow: FakeUow, fixed_clock: FixedClock
) -> None:
    """US-NH-62: 1–5 sao; truyện riêng tư của người khác như không tồn tại."""
    owner = _identity(5)
    created = await CreateSeriesUseCase(lambda: uow, fixed_clock).execute(  # type: ignore[arg-type,return-value]
        owner, SeriesInput(title_vi="Riêng")
    )
    rate = RateSeriesUseCase(lambda: uow, fixed_clock)  # type: ignore[arg-type,return-value]
    with pytest.raises(InvalidRatingError):
        await rate.execute(owner, created.series.id, 6)
    with pytest.raises(SeriesNotFoundError):
        await rate.execute(_identity(6), created.series.id, 3)
    result = await rate.execute(owner, created.series.id, 4)
    assert (result.my_stars, result.average, result.count) == (4, 4.0, 1)
    again = await rate.execute(owner, created.series.id, 2)
    assert (again.average, again.count) == (2.0, 1)  # chấm lại là sửa, không thêm lượt


async def test_learner_cannot_edit_public_series_error_is_permission_denied() -> None:
    uow = SimpleNamespace(series=FakeSeriesRepo())
    created = await uow.series.add(
        NewSeries(None, Visibility.PUBLIC, "Chung", SeriesStatus.ONGOING, 1, datetime(2026, 1, 1))
    )
    with pytest.raises(PermissionDeniedError):
        await load_editable_series(uow, created.id, Actor(user_id=7))  # type: ignore[arg-type]
