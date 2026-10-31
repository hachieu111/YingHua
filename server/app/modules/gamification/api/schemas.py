"""Schema request/response của M16 (chỉ ở tầng api). Không có email hay mã người dùng của người khác."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.core.uploads import file_url
from app.modules.gamification.application import dto
from app.modules.gamification.domain.blade_rules import MAX_BAND, MAX_EVENTS, MAX_TYPOS, MIN_BAND
from app.modules.gamification.domain.entities import BladeBest
from app.modules.gamification.domain.season_rules import HIDDEN_NOTE

CharText = Annotated[str, StringConstraints(min_length=1, max_length=4)]


class BadgeResponse(BaseModel):
    code: str
    name: str
    tier: int
    style_key: str

    @classmethod
    def of(cls, b: dto.BadgeView) -> BadgeResponse:
        return cls(code=b.code, name=b.name, tier=b.tier, style_key=b.style_key)


class FrameResponse(BaseModel):
    code: str
    name: str
    style_key: str


class MilestoneResponse(BaseModel):
    days: int
    days_left: int = Field(description="Số ngày còn thiếu để chạm mốc")


class MeResponse(BaseModel):
    xp_today: int
    xp_season: int
    xp_total: int
    season_rank: int | None = Field(description="Hạng XP trong mùa hiện hành; null nếu chưa có XP")
    streak_current: int
    next_streak_milestone: MilestoneResponse | None
    equipped_badge: BadgeResponse | None

    @classmethod
    def of(cls, v: dto.MeView) -> MeResponse:
        milestone = v.next_streak_milestone
        return cls(
            xp_today=v.xp_today,
            xp_season=v.xp_season,
            xp_total=v.xp_total,
            season_rank=v.season_rank,
            streak_current=v.streak_current,
            next_streak_milestone=MilestoneResponse(days=milestone.days, days_left=milestone.days_left)
            if milestone
            else None,
            equipped_badge=BadgeResponse.of(v.equipped_badge) if v.equipped_badge else None,
        )


class ActivityDayResponse(BaseModel):
    date: date
    xp: int


class WeeklyActivityResponse(BaseModel):
    week_start: date
    days: list[ActivityDayResponse]
    total: int

    @classmethod
    def of(cls, v: dto.WeeklyActivity) -> WeeklyActivityResponse:
        return cls(
            week_start=v.week_start,
            days=[ActivityDayResponse(date=d.day, xp=d.xp) for d in v.days],
            total=v.total,
        )


class QuestResponse(BaseModel):
    code: str
    name: str
    progress: int
    target: int
    xp: int
    completed: bool
    rewarded_at: datetime | None


class QuestsTodayResponse(BaseModel):
    date: date
    quests: list[QuestResponse]
    completed_count: int
    total: int
    bonus_coins: int = Field(description="Xu thưởng khi đủ cả nhiệm vụ trong ngày")
    bonus_granted: bool

    @classmethod
    def of(cls, v: dto.QuestsToday) -> QuestsTodayResponse:
        return cls(
            date=v.day,
            quests=[_quest(q) for q in v.quests],
            completed_count=v.completed_count,
            total=len(v.quests),
            bonus_coins=v.bonus_coins,
            bonus_granted=v.bonus_granted,
        )


def _quest(q: dto.QuestView) -> QuestResponse:
    return QuestResponse(
        code=q.code,
        name=q.name,
        progress=q.progress,
        target=q.target,
        xp=q.xp,
        completed=q.completed,
        rewarded_at=q.rewarded_at,
    )


class WeeklyGoalResponse(BaseModel):
    week_start: date
    goal: int
    rewarded_goal: int = Field(description="Mục tiêu dùng để thưởng (không thấp hơn 10 trang)")
    pages_read: int
    pages_left: int
    percent: int
    reward_xp: int
    reward_frame_code: str
    reward_frame_days: int
    rewarded_at: datetime | None

    @classmethod
    def of(cls, v: dto.WeeklyGoalView) -> WeeklyGoalResponse:
        return cls(**asdict(v))


class BoardRowResponse(BaseModel):
    rank: int | None
    display_name: str
    avatar_url: str | None
    avatar_preset: str | None
    hsk_level: int | None
    score: int
    unit: str
    badge: BadgeResponse | None
    frame: FrameResponse | None
    is_vip: bool
    is_me: bool
    anonymous: bool

    @classmethod
    def of(cls, r: dto.BoardRow) -> BoardRowResponse:
        return cls(
            rank=r.rank,
            display_name=r.display_name,
            avatar_url=file_url(r.avatar_file_id),
            avatar_preset=r.avatar_preset,
            hsk_level=r.hsk_level,
            score=r.score,
            unit=r.unit,
            badge=BadgeResponse.of(r.badge) if r.badge else None,
            frame=FrameResponse(code=r.frame.code, name=r.frame.name, style_key=r.frame.style_key)
            if r.frame
            else None,
            is_vip=r.is_vip,
            is_me=r.is_me,
            anonymous=r.anonymous,
        )


class NextMilestoneResponse(BaseModel):
    rank: int = Field(description="Hạng của mốc thưởng kế tiếp (50, 10, 3, 1)")
    xp_missing: int
    ratio: float = Field(description="Tỉ lệ cho thanh tiến độ, 0..1")


class SummaryResponse(BaseModel):
    learners: int
    pages_in_period: int
    season_xp: int


class LeaderboardResponse(BaseModel):
    items: list[BoardRowResponse]
    total: int
    page: int
    size: int
    me: BoardRowResponse
    me_hidden: bool = Field(description="Bạn đang ẩn danh trên bảng xếp hạng (F16.08)")
    me_hidden_note: str | None
    next_milestone: NextMilestoneResponse | None
    summary: SummaryResponse

    @classmethod
    def of(cls, v: dto.LeaderboardView) -> LeaderboardResponse:
        milestone = v.next_milestone
        return cls(
            items=[BoardRowResponse.of(r) for r in v.items],
            total=v.total,
            page=v.page,
            size=v.size,
            me=BoardRowResponse.of(v.me),
            me_hidden=v.me_hidden,
            me_hidden_note=HIDDEN_NOTE if v.me_hidden else None,
            next_milestone=NextMilestoneResponse(
                rank=milestone.rank, xp_missing=milestone.xp_missing, ratio=milestone.ratio
            )
            if milestone
            else None,
            summary=SummaryResponse(
                learners=v.summary.learners,
                pages_in_period=v.summary.pages_in_period,
                season_xp=v.summary.season_xp,
            ),
        )


class TierResponse(BaseModel):
    tier: str = Field(description="top3 | top10 | top50")
    rank_from: int
    rank_to: int
    coins: int
    tickets: int
    vip_days: int
    frame_code: str | None
    badge_code: str | None


class CurrentSeasonResponse(BaseModel):
    id: int
    number: int
    starts_at: datetime
    ends_at: datetime
    server_now: datetime = Field(
        description="Giờ máy chủ, để đếm ngược không phụ thuộc đồng hồ máy người dùng"
    )
    seconds_left: int
    status: str = Field(description="active | finalizing | finalized")
    finalizing_previous: bool = Field(description='Có mùa đã hết giờ chưa chốt ("Đang tổng kết mùa")')
    tiers: list[TierResponse]
    min_xp: int
    my_rank: int | None
    my_xp: int
    my_tier: str | None = Field(description="Bậc thưởng sẽ nhận nếu mùa chốt lúc này")

    @classmethod
    def of(cls, v: dto.CurrentSeasonView) -> CurrentSeasonResponse:
        return cls(
            id=v.id,
            number=v.number,
            starts_at=v.starts_at,
            ends_at=v.ends_at,
            server_now=v.server_now,
            seconds_left=v.seconds_left,
            status=v.status,
            finalizing_previous=v.finalizing_previous,
            tiers=[TierResponse(**{**asdict(t), "tier": t.tier.value}) for t in v.tiers],
            min_xp=v.min_xp,
            my_rank=v.my_rank,
            my_xp=v.my_xp,
            my_tier=v.my_tier.value if v.my_tier else None,
        )


class SeasonResultResponse(BaseModel):
    season_number: int
    starts_at: datetime
    ends_at: datetime
    rank: int
    xp: int
    tier: str = Field(description="top3 | top10 | top50")
    reward_granted_at: datetime | None


class SeasonHistoryResponse(BaseModel):
    items: list[SeasonResultResponse]
    total: int
    page: int
    size: int

    @classmethod
    def of(cls, v: dto.SeasonHistory, page: int, size: int) -> SeasonHistoryResponse:
        items = [
            SeasonResultResponse(
                season_number=i.season_number,
                starts_at=i.starts_at,
                ends_at=i.ends_at,
                rank=i.rank,
                xp=i.xp,
                tier=i.tier.value,
                reward_granted_at=i.reward_granted_at,
            )
            for i in v.items
        ]
        return cls(items=items, total=v.total, page=page, size=size)


class AchievementResponse(BaseModel):
    code: str
    name: str
    description: str
    style_key: str
    tier: int = Field(description="Cấp đã đạt (0 = chưa mở khóa)")
    max_tier: int
    progress: int
    next_threshold: int | None = Field(description="Ngưỡng của cấp kế tiếp; null khi đã đạt cấp cao nhất")
    thresholds: list[int]
    unlocked_at: datetime | None
    equipped: bool

    @classmethod
    def of(cls, a: dto.AchievementProgress) -> AchievementResponse:
        return cls(**{**asdict(a), "thresholds": list(a.thresholds)})


class EquipRequest(BaseModel):
    achievement_code: str | None = Field(default=None, max_length=32, description="null để tháo huy hiệu")


class EquippedResponse(BaseModel):
    achievement_code: str | None
    name: str | None
    tier: int | None
    style_key: str | None

    @classmethod
    def of(cls, e: dto.EquippedBadge) -> EquippedResponse:
        return cls(achievement_code=e.code, name=e.name, tier=e.tier, style_key=e.style_key)


class WeakRadicalResponse(BaseModel):
    radical: str
    count: int


class WeakRadicalsResponse(BaseModel):
    radicals: list[WeakRadicalResponse]
    fallback: bool = Field(
        description="True: chưa có dữ liệu ôn tập, đây là bộ thủ phổ biến của cấp HSK hiện tại"
    )
    message: str | None

    @classmethod
    def of(cls, v: dto.WeakRadicalsView) -> WeakRadicalsResponse:
        return cls(
            radicals=[WeakRadicalResponse(radical=r.radical, count=r.count) for r in v.radicals],
            fallback=v.fallback,
            message=v.message,
        )


class RoundRequest(BaseModel):
    """Chế độ `hsk` cần `hsk_band` (1-7, 7 = HSK 7-9); chế độ `weak_radical` cần `radical`."""

    mode: Literal["hsk", "weak_radical"]
    hsk_band: int | None = Field(default=None, ge=MIN_BAND, le=MAX_BAND)
    radical: CharText | None = None


class BladeItemResponse(BaseModel):
    index: int
    text: str
    pinyin: str = Field(description="Pinyin có dấu để hiển thị")
    answers: list[str] = Field(description="Mọi đáp án chấp nhận: a-z, không dấu, không cách")
    han_viet: str | None
    hsk_level: int | None
    is_boss: bool


class RoundResponse(BaseModel):
    round_id: uuid.UUID = Field(description="Mã lượt do máy chủ giữ; gửi lại khi nộp kết quả")
    mode: str
    hsk_band: int | None
    radical: str | None
    seconds: int
    lives: int
    items: list[BladeItemResponse]

    @classmethod
    def of(cls, v: dto.RoundView) -> RoundResponse:
        return cls(
            round_id=v.round_id,
            mode=v.mode,
            hsk_band=v.hsk_band,
            radical=v.radical,
            seconds=v.seconds,
            lives=v.lives,
            items=[
                BladeItemResponse(
                    index=i.index,
                    text=i.text,
                    pinyin=i.pinyin,
                    answers=list(i.answers),
                    han_viet=i.han_viet,
                    hsk_level=i.hsk_level,
                    is_boss=i.is_boss,
                )
                for i in v.items
            ],
        )


class BladeEventRequest(BaseModel):
    index: int = Field(ge=0)
    result: Literal["hit", "miss"]
    ms: int = Field(ge=0, description="Mốc từ đầu ván, mili giây")


class SubmitSessionRequest(BaseModel):
    """Kết quả ván: mã lượt, chuỗi sự kiện, số lần gõ sai, thời gian chơi. Máy chủ tự chấm điểm."""

    round_id: uuid.UUID
    events: list[BladeEventRequest] = Field(max_length=MAX_EVENTS)
    typos: int = Field(ge=0, le=MAX_TYPOS)
    duration_ms: int = Field(ge=0, le=10 * 60 * 1000)


class MissedItemResponse(BaseModel):
    text: str
    pinyin: str
    han_viet: str | None


class SessionResponse(BaseModel):
    id: int
    mode: str
    hsk_band: int | None
    radical: str | None
    score: int
    correct: int = Field(description="Số mục chém đúng")
    wrong: int = Field(description="Số mục bị rơi (mất mạng)")
    typos: int
    max_combo: int
    accuracy: float = Field(description="Phím đúng / (phím đúng + gõ sai), từ 0 đến 1")
    rank: str = Field(description="S, A, B hoặc C")
    duration_ms: int
    xp_awarded: int = Field(description="XP được cộng cho ván (có thể 0 khi chạm trần ngày)")
    is_best: bool = Field(description="Vượt kỷ lục cũ của cùng cấp/chế độ")
    missed: list[MissedItemResponse]

    @classmethod
    def of(cls, r: dto.SessionResult) -> SessionResponse:
        return cls(**{**asdict(r), "missed": [MissedItemResponse(**asdict(m)) for m in r.missed]})


class BladeBestResponse(BaseModel):
    mode: str
    hsk_band: int | None
    best_score: int
    best_combo: int
    plays: int

    @classmethod
    def of(cls, b: BladeBest) -> BladeBestResponse:
        return cls(**asdict(b))
