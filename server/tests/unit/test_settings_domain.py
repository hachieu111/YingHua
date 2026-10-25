from __future__ import annotations

import pytest

from app.core.errors import InvalidInputError
from app.modules.settings.domain.entities import LearningGoal, ReadingMode, UserSettings, apply_changes


def _settings() -> UserSettings:
    return UserSettings(user_id=1)


def test_defaults_match_spec() -> None:
    s = _settings()
    assert (s.hsk_level, s.default_mode) == (None, ReadingMode.READ)


def test_apply_valid_changes() -> None:
    s = _settings()
    apply_changes(
        s, {"hsk_level": 9, "default_mode": "learn", "learning_goal": "study", "weekly_page_goal": 20}
    )
    assert (s.hsk_level, s.default_mode, s.learning_goal, s.weekly_page_goal) == (
        9,
        ReadingMode.LEARN,
        LearningGoal.STUDY,
        20,
    )


@pytest.mark.parametrize("value", [0, 10, -1, True, "5", 3.5])
def test_hsk_level_outside_1_to_9_is_rejected(value: object) -> None:
    with pytest.raises(InvalidInputError):
        apply_changes(_settings(), {"hsk_level": value})


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(InvalidInputError):
        apply_changes(_settings(), {"is_admin": True})


def test_failed_validation_leaves_settings_untouched() -> None:
    s = _settings()
    with pytest.raises(InvalidInputError):
        apply_changes(s, {"hsk_level": 3, "default_mode": "khac"})
    assert s.default_mode is ReadingMode.READ
