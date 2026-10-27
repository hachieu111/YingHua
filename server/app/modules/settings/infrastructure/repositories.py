from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.domain.entities import LearningGoal, ReadingMode, UserSettings
from app.modules.settings.infrastructure.orm_models import UserSettingsModel


def _entity(m: UserSettingsModel) -> UserSettings:
    return UserSettings(
        user_id=m.user_id,
        hsk_level=m.hsk_level,
        default_mode=ReadingMode(m.default_mode),
        tts_voice=m.tts_voice,
        learning_goal=LearningGoal(m.learning_goal) if m.learning_goal else None,
        weekly_page_goal=m.weekly_page_goal,
        timezone=m.timezone,
        show_xianxia=m.show_xianxia,
        bubble_font_scale=m.bubble_font_scale,
        reminder_enabled=m.reminder_enabled,
        reminder_time=m.reminder_time,
    )


class SqlSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: int) -> UserSettings:
        model = await self._session.get(UserSettingsModel, user_id, with_for_update=True)
        if model is None:
            model = UserSettingsModel(
                user_id=user_id,
                default_mode="read",
                timezone="Asia/Ho_Chi_Minh",
                show_xianxia=True,
                bubble_font_scale=100,
                reminder_enabled=False,
            )
            self._session.add(model)
            await self._session.flush()
        return _entity(model)

    async def save(self, settings: UserSettings) -> None:
        model = await self._session.get(UserSettingsModel, settings.user_id)
        if model is None:
            return
        model.hsk_level = settings.hsk_level
        model.default_mode = settings.default_mode.value
        model.tts_voice = settings.tts_voice
        model.learning_goal = settings.learning_goal.value if settings.learning_goal else None
        model.weekly_page_goal = settings.weekly_page_goal
        model.timezone = settings.timezone
        model.show_xianxia = settings.show_xianxia
        model.bubble_font_scale = settings.bubble_font_scale
        model.reminder_enabled = settings.reminder_enabled
        model.reminder_time = settings.reminder_time
        await self._session.flush()
