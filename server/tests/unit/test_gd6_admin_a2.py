"""GĐ6 đợt A2 — luật thuần và use case của cấu hình hệ thống, kiểm duyệt, ghi nhớ đăng nhập, bảo trì.

Mã: F13.04, F13.05, F13.06, F01.11, F01.10 (US-QT-12, US-QT-13, US-NH-76, US-NH-65).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import TracebackType
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.security import TokenService
from app.core.stored_files import FileKind, StoredFile
from app.modules.admin.api.maintenance import maintenance_middleware
from app.modules.admin.application.dto import ModerationTarget, SamplePageCandidate
from app.modules.admin.application.public import grammar_ai_policy, mistake_review_ai_policy
from app.modules.admin.application.system_settings import (
    CachedSystemSettings,
    defaults_from_settings,
    merge_settings,
)
from app.modules.admin.application.use_cases.list_sample_page_candidates import (
    MAX_SAMPLE_PAGE_CANDIDATES,
    ListSamplePageCandidatesUseCase,
)
from app.modules.admin.application.use_cases.remove_content import RemoveContentUseCase
from app.modules.admin.application.use_cases.update_system_settings import UpdateSystemSettingsUseCase
from app.modules.admin.domain.errors import (
    AlreadyRemovedError,
    EmptySettingsChangeError,
    InvalidSettingValueError,
    RemovalReasonRequiredError,
    RemovalTargetInvalidError,
    SamplePageInvalidError,
    UnknownSettingError,
)
from app.modules.admin.domain.moderation import ModerationFlag, moderation_flags
from app.modules.admin.domain.system_settings import validate_setting
from app.modules.auth.application.dto import Identity
from app.modules.auth.domain.entities import Role
from app.modules.auth.domain.rules import AVATAR_PRESETS, is_remembered_session
from app.modules.imaging.application.use_cases.get_sample_page import GetSamplePageUseCase
from app.modules.imaging.domain.entities import Bubble, Translation, TranslationStatus
from app.modules.imaging.domain.errors import SamplePageNotConfiguredError
from app.modules.library.application.public import PageAccess

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)
ADMIN = Identity(1, Role.ADMIN, "s")
LEARNER = Identity(2, Role.USER, "s")


class FixedClock:
    def __init__(self) -> None:
        self.at = NOW

    def now(self) -> datetime:
        return self.at


def _defaults() -> Any:
    return defaults_from_settings(get_settings())


# ---- Luật thuần -------------------------------------------------------------------------------


def test_validate_setting_accepts_valid_values_and_null_sample_page() -> None:
    """US-QT-13 TC4: giá trị hợp lệ được chấp nhận."""
    assert validate_setting("maintenance_mode", True) is True
    assert validate_setting("quiz_daily_llm_limit", 0) == 0
    assert validate_setting("sample_page_id", None) is None
    assert validate_setting("sample_page_id", 12) == 12


@pytest.mark.parametrize(
    ("key", "raw"),
    [
        ("quiz_daily_llm_limit", -1),
        ("quiz_daily_llm_limit", "5"),
        ("quiz_daily_llm_limit", True),
        ("quiz_daily_llm_limit", 5000),
        ("llm_enabled", 1),
        ("tts_enabled", "true"),
        ("sample_page_id", 0),
        ("grammar_daily_limit", 2.5),
    ],
)
def test_validate_setting_rejects_bad_values_with_specific_message(key: str, raw: Any) -> None:
    """US-QT-13 TC4: giá trị âm, không phải số hoặc sai kiểu bị từ chối."""
    with pytest.raises(InvalidSettingValueError) as info:
        validate_setting(key, raw)
    assert "«" in info.value.message


def test_validate_setting_rejects_unknown_key() -> None:
    with pytest.raises(UnknownSettingError):
        validate_setting("khong_co_khoa_nay", 1)


def test_merge_settings_uses_defaults_and_ignores_corrupt_stored_values() -> None:
    merged, overridden = merge_settings(_defaults(), {"grammar_daily_limit": 3, "tts_enabled": "sai-kieu"})
    assert merged.grammar_daily_limit == 3
    assert merged.tts_enabled == _defaults().tts_enabled
    assert overridden == ["grammar_daily_limit"]


def test_moderation_flags_follow_simple_rules() -> None:
    """F13.05: luật kích thước, ảnh trùng, xử lý lỗi; không dùng AI."""
    assert moderation_flags(800, 1200, 0, False) == []
    assert moderation_flags(50, 1200, 0, False) == [ModerationFlag.TINY_IMAGE]
    assert moderation_flags(800, 13000, 1, True) == [
        ModerationFlag.OVERSIZED_IMAGE,
        ModerationFlag.DUPLICATE_IMAGE,
        ModerationFlag.PROCESSING_FAILED,
    ]
    assert moderation_flags(None, None, 0, False) == []


def test_remembered_session_is_decided_by_lifetime() -> None:
    """US-NH-76 TC4: phiên mới kế thừa chế độ của phiên cũ qua thời hạn."""
    short = timedelta(hours=24)
    assert is_remembered_session(NOW, NOW + timedelta(days=30), short) is True
    assert is_remembered_session(NOW, NOW + short, short) is False


def test_avatar_presets_match_frontend_codes() -> None:
    assert set(AVATAR_PRESETS) == {
        "original",
        "sakura_flower",
        "bach_thien",
        "tieu_vu_tru",
        "mac_van",
        "lac_ly",
    }


# ---- Bộ đệm cấu hình --------------------------------------------------------------------------


class _Source:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.calls = 0

    async def load_all(self) -> dict[str, Any]:
        self.calls += 1
        return dict(self.data)


async def test_cached_settings_reads_once_within_ttl_and_refreshes_after_invalidate() -> None:
    source = _Source({"maintenance_mode": True})
    cache = CachedSystemSettings(lambda: source, _defaults(), FixedClock())
    assert (await cache.snapshot()).maintenance_mode is True
    source.data = {"maintenance_mode": False}
    assert (await cache.snapshot()).maintenance_mode is True  # còn trong hạn đệm
    assert source.calls == 1
    cache.invalidate()
    assert (await cache.snapshot()).maintenance_mode is False


# ---- Fake UoW ---------------------------------------------------------------------------------


class _Audit:
    def __init__(self) -> None:
        self.rows: list[tuple[Any, ...]] = []

    async def add(self, *args: Any) -> None:
        self.rows.append(args)


class _SettingsRepo:
    def __init__(self, valid_sample: bool = True) -> None:
        self.stored: dict[str, Any] = {}
        self.valid_sample = valid_sample

    async def load_all(self) -> dict[str, Any]:
        return dict(self.stored)

    async def upsert_many(self, values: dict[str, Any], admin_id: int, at: datetime) -> None:
        self.stored.update(values)

    async def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.stored.pop(key, None)

    async def is_valid_sample_page(self, page_id: int) -> bool:
        return self.valid_sample

    async def list_sample_page_candidates(self, limit: int) -> list[SamplePageCandidate]:
        self.candidate_limit = limit
        return [SamplePageCandidate(4, "Truyện công khai", 1, None, 1, 3)] if self.valid_sample else []


class _Moderation:
    def __init__(self, target: ModerationTarget | None, removable: list[int]) -> None:
        self.target = target
        self.removable = removable
        self.removals: list[tuple[Any, ...]] = []

    async def resolve_target(self, page_id: int | None, file_id: int | None) -> ModerationTarget | None:
        return self.target

    async def mark_removed(self, file_ids: list[int], at: datetime) -> list[int]:
        return self.removable

    async def add_removal(self, *args: Any) -> int:
        self.removals.append(args)
        return 99

    async def get_removal(self, removal_id: int) -> Any:
        return {"id": removal_id}


class _Uow:
    def __init__(self, settings: _SettingsRepo | None = None, moderation: _Moderation | None = None) -> None:
        self.audit = _Audit()
        self.system_settings = settings or _SettingsRepo()
        self.moderation = moderation or _Moderation(None, [])
        self.committed = False

    async def __aenter__(self) -> _Uow:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _update_use_case(uow: _Uow) -> tuple[UpdateSystemSettingsUseCase, CachedSystemSettings]:
    settings = CachedSystemSettings(lambda: uow.system_settings, _defaults(), FixedClock())
    return UpdateSystemSettingsUseCase(lambda: uow, FixedClock(), settings), settings  # type: ignore[arg-type,return-value]


async def test_update_settings_writes_audit_and_takes_effect_immediately() -> None:
    """US-QT-13 TC10: đổi công tắc có hiệu lực ngay và có nhật ký."""
    uow = _Uow()
    use_case, settings = _update_use_case(uow)
    assert (await settings.snapshot()).maintenance_mode is False
    view = await use_case.execute(ADMIN, {"maintenance_mode": True, "grammar_daily_limit": 4})
    assert view.values.maintenance_mode is True and (await settings.snapshot()).grammar_daily_limit == 4
    assert uow.committed
    action, details = uow.audit.rows[0][1], uow.audit.rows[0][4]
    assert action == "settings.updated"
    assert details["changes"]["maintenance_mode"] == {"from": False, "to": True}


async def test_update_settings_null_resets_key_to_default_and_audits() -> None:
    """F13.05: null đưa khóa về mặc định (xóa dòng), nhật ký ghi giá trị cũ -> mặc định."""
    uow = _Uow()
    use_case, settings = _update_use_case(uow)
    default_limit = settings.defaults.grammar_daily_limit
    await use_case.execute(ADMIN, {"grammar_daily_limit": 4, "maintenance_mode": True})
    view = await use_case.execute(ADMIN, {"grammar_daily_limit": None, "maintenance_mode": None})
    assert view.values.grammar_daily_limit == default_limit and view.values.maintenance_mode is False
    assert uow.system_settings.stored == {} and view.overridden == []
    assert uow.audit.rows[-1][4]["changes"] == {
        "grammar_daily_limit": {"from": 4, "to": default_limit},
        "maintenance_mode": {"from": True, "to": False},
    }
    with pytest.raises(UnknownSettingError):
        await use_case.execute(ADMIN, {"khong_co": None})


async def test_update_settings_rejects_learner_empty_bad_value_and_invalid_sample_page() -> None:
    uow = _Uow(_SettingsRepo(valid_sample=False))
    use_case, _ = _update_use_case(uow)
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(LEARNER, {"tts_enabled": False})
    with pytest.raises(EmptySettingsChangeError):
        await use_case.execute(ADMIN, {})
    with pytest.raises(InvalidSettingValueError):
        await use_case.execute(ADMIN, {"grammar_daily_limit": -3, "tts_enabled": False})
    with pytest.raises(SamplePageInvalidError):
        await use_case.execute(ADMIN, {"sample_page_id": 5})
    assert uow.system_settings.stored == {} and not uow.committed


async def test_sample_page_candidates_admin_only_and_capped() -> None:
    """US-QT-13 TC13: quản trị chọn trang mẫu từ danh sách trang hợp lệ thay vì gõ mã."""
    uow = _Uow()
    use_case = ListSamplePageCandidatesUseCase(lambda: uow)  # type: ignore[arg-type,return-value]
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(LEARNER)
    items = await use_case.execute(ADMIN)
    assert [item.page_id for item in items] == [4]
    assert uow.system_settings.candidate_limit == MAX_SAMPLE_PAGE_CANDIDATES


# ---- Chính sách AI đọc cấu hình hệ thống ------------------------------------------------------


async def test_ai_policy_reads_current_system_settings() -> None:
    """F13.05: hạn mức và công tắc LLM của ngữ pháp / lỗi sai lấy từ cấu hình hệ thống, không từ Settings."""
    source = _Source({"grammar_daily_limit": 4, "mistake_review_daily_limit": 9, "llm_enabled": True})
    settings = CachedSystemSettings(lambda: source, _defaults(), FixedClock())
    grammar, mistakes = grammar_ai_policy(settings), mistake_review_ai_policy(settings)
    assert (await grammar.daily_limit(7), await mistakes.daily_limit(7)) == (4, 9)
    assert await grammar.llm_enabled() is True
    source.data = {"grammar_daily_limit": 1, "llm_enabled": False}
    settings.invalidate()
    assert await grammar.daily_limit(7) == 1 and await grammar.llm_enabled() is False


def test_default_limits_come_from_settings_single_source() -> None:
    config = get_settings()
    snapshot = _defaults()
    assert (snapshot.grammar_daily_limit, snapshot.mistake_review_daily_limit) == (
        config.grammar_daily_limit,
        config.mistake_review_daily_limit,
    )


# ---- Gỡ nội dung ------------------------------------------------------------------------------


class _Notifier:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[tuple[int, int | None, str]] = []

    async def content_removed(self, owner_id: int, page_id: int | None, reason: str) -> None:
        if self.fail:
            raise RuntimeError("hỏng")
        self.sent.append((owner_id, page_id, reason))


def _remove_use_case(uow: _Uow, notifier: _Notifier | None = None) -> RemoveContentUseCase:
    return RemoveContentUseCase(lambda: uow, FixedClock(), notifier or _Notifier())  # type: ignore[arg-type,return-value]


async def test_remove_content_requires_reason_exactly_one_target_and_admin() -> None:
    """US-QT-12 TC2, F13.04: lý do bắt buộc."""
    uow = _Uow()
    use_case = _remove_use_case(uow)
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(LEARNER, 1, None, "vi phạm")
    with pytest.raises(RemovalTargetInvalidError):
        await use_case.execute(ADMIN, 1, 2, "vi phạm")
    with pytest.raises(RemovalReasonRequiredError):
        await use_case.execute(ADMIN, 1, None, "   ")
    assert not uow.committed


async def test_remove_content_marks_files_logs_removal_and_audit() -> None:
    target = ModerationTarget(root_file_id=7, page_id=3, owner_id=2, file_ids=[7, 8, 9])
    uow = _Uow(moderation=_Moderation(target, [7, 8]))
    await _remove_use_case(uow).execute(ADMIN, 3, None, "  Ảnh vi phạm  ")
    assert uow.moderation.removals[0][:3] == (7, 3, "Ảnh vi phạm")
    row = uow.audit.rows[0]
    assert row[1:4] == ("content.removed", "page", 3)
    assert row[4] == {"reason": "Ảnh vi phạm", "file_count": 2, "owner_id": 2}
    assert uow.committed


async def test_remove_content_notifies_owner_with_reason_and_page() -> None:
    """F13.04 bước 4, F14.05: chủ ảnh được báo kèm lý do và mã trang."""
    target = ModerationTarget(root_file_id=7, page_id=3, owner_id=2, file_ids=[7])
    notifier = _Notifier()
    await _remove_use_case(_Uow(moderation=_Moderation(target, [7])), notifier).execute(
        ADMIN, 3, None, "Vi phạm"
    )
    assert notifier.sent == [(2, 3, "Vi phạm")]


async def test_remove_content_skips_notice_for_unknown_owner_or_self_removal() -> None:
    notifier = _Notifier()
    for owner in (None, ADMIN.user_id):
        target = ModerationTarget(root_file_id=7, page_id=None, owner_id=owner, file_ids=[7])
        await _remove_use_case(_Uow(moderation=_Moderation(target, [7])), notifier).execute(
            ADMIN, None, 7, "Vi phạm"
        )
    assert notifier.sent == []


async def test_remove_content_still_succeeds_when_notification_fails() -> None:
    target = ModerationTarget(root_file_id=7, page_id=3, owner_id=2, file_ids=[7])
    uow = _Uow(moderation=_Moderation(target, [7]))
    await _remove_use_case(uow, _Notifier(fail=True)).execute(ADMIN, 3, None, "Vi phạm")
    assert uow.committed


async def test_remove_content_twice_is_conflict() -> None:
    target = ModerationTarget(root_file_id=7, page_id=None, owner_id=2, file_ids=[7])
    uow = _Uow(moderation=_Moderation(target, []))
    with pytest.raises(AlreadyRemovedError):
        await _remove_use_case(uow).execute(ADMIN, None, 7, "vi phạm")
    assert not uow.committed


# ---- Middleware bảo trì -----------------------------------------------------------------------


class _FakeSettingsCache:
    def __init__(self, maintenance: bool) -> None:
        self.maintenance = maintenance

    async def snapshot(self) -> Any:
        return _defaults().__class__(**{**_defaults().as_dict(), "maintenance_mode": self.maintenance})


class _FakeContainer:
    def __init__(self, maintenance: bool) -> None:
        self.system_settings = _FakeSettingsCache(maintenance)
        self.tokens = TokenService("x" * 40, "HS256", 15, FixedClock())


def _maintenance_app(maintenance: bool) -> tuple[TestClient, _FakeContainer]:
    app = FastAPI()
    app.state.container = _FakeContainer(maintenance)
    app.middleware("http")(maintenance_middleware)

    @app.get("/api/v1/anything")
    async def anything() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/api/v1/health")
    async def health() -> JSONResponse:
        return JSONResponse({"ok": True})

    return TestClient(app), app.state.container


def test_maintenance_blocks_guests_and_learners_but_not_admin_or_health() -> None:
    """US-QT-13 TC5."""
    client, container = _maintenance_app(True)
    blocked = client.get("/api/v1/anything")
    assert blocked.status_code == 503 and blocked.json()["error"]["code"] == "MAINTENANCE_MODE"
    learner = container.tokens.issue_access_token(2, "user", "s")
    assert client.get("/api/v1/anything", headers={"Authorization": f"Bearer {learner}"}).status_code == 503
    admin = container.tokens.issue_access_token(1, "admin", "s")
    assert client.get("/api/v1/anything", headers={"Authorization": f"Bearer {admin}"}).status_code == 200
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/anything", headers={"Authorization": "Bearer hong"}).status_code == 503


def test_maintenance_off_lets_everything_through() -> None:
    client, _ = _maintenance_app(False)
    assert client.get("/api/v1/anything").status_code == 200


# ---- F04.16 trang mẫu -------------------------------------------------------------------------


class _SamplePages:
    def __init__(self, access: Any) -> None:
        self.access = access

    async def get_page(self, identity: Identity | None, page_id: int, *, require_edit: bool = False) -> Any:
        if self.access is None:
            raise NotFoundError()
        return self.access


class _SampleUow:
    def __init__(self, status: TranslationStatus, removed: bool) -> None:
        self.translations = self
        self.files = self
        self.bubbles = self
        self._status, self._removed = status, removed

    async def get(self, key: int) -> Any:
        if key == 20:  # bản dịch
            return Translation(20, 10, "h", self._status, "v", 0, NOW)
        return StoredFile(
            10, FileKind.ORIGINAL, "k", "h", "image/png", 1, NOW, removed_at=NOW if self._removed else None
        )

    async def list_by_translation(self, translation_id: int) -> list[Bubble]:
        return [Bubble(1, translation_id, 0, "speech_bubble", 0, 0, 5, 5, "你好")]

    async def __aenter__(self) -> _SampleUow:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


def _sample_case(
    sample_id: int | None, status: TranslationStatus, removed: bool, readable: bool = True
) -> Any:
    access = PageAccess(7, 1, 20, 10, 100, 200, False) if readable else None
    snapshot = _defaults().__class__(**{**_defaults().as_dict(), "sample_page_id": sample_id})

    class _Port:
        async def snapshot(self) -> Any:
            return snapshot

    return GetSamplePageUseCase(lambda: _SampleUow(status, removed), _SamplePages(access), _Port())  # type: ignore[arg-type,return-value]


async def test_sample_page_returns_real_result_when_configured_and_done() -> None:
    """US-NH-77 TC1: trang mẫu đã dịch xong trả ảnh và bong bóng."""
    sample = await _sample_case(7, TranslationStatus.DONE, False).execute(LEARNER)
    assert sample.access.page_id == 7 and [b.text_zh for b in sample.bubbles] == ["你好"]


@pytest.mark.parametrize(
    ("sample_id", "status", "removed", "readable"),
    [
        (None, TranslationStatus.DONE, False, True),
        (7, TranslationStatus.QUEUED, False, True),
        (7, TranslationStatus.DONE, True, True),
        (7, TranslationStatus.DONE, False, False),
    ],
)
async def test_sample_page_unavailable_cases_are_not_found(
    sample_id: int | None, status: TranslationStatus, removed: bool, readable: bool
) -> None:
    """US-NH-77 TC5: chưa có trang mẫu (chưa cấu hình, chưa dịch, đã gỡ, không đọc được) → 404."""
    with pytest.raises(SamplePageNotConfiguredError):
        await _sample_case(sample_id, status, removed, readable).execute(LEARNER)
