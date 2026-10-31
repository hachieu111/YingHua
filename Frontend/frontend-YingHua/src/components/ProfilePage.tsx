import React, { useEffect, useState } from 'react';
import { countVocab } from '../api/vocab';
import { ReaderTarget, UserProfileData } from '../types';
import { useLearningStats } from '../utils/useLearningStats';
import { useRewards } from '../utils/useRewards';
import { useStreak } from '../utils/useStreak';
import { ProfileBadgesTab } from './AchievementViews';
import { AvatarFrame, VipPill } from './AvatarFrame';
import { BadgeChip } from './BadgeChip';
import { formatVipUntil } from './WalletSummary';
import { WeeklyGoalCard } from './WeeklyGoalCard';
import { ProfileWalletCard } from './ProfileWalletCard';
import { ProfileActivityChart } from './ProfileActivityChart';
import { ProfileAvatar } from './ProfileAvatar';
import { ProfileErrorReports } from './ProfileErrorReports';
import { ProfileReadingList } from './ProfileReadingList';
import { ProfileRecommendations } from './ProfileRecommendations';
import { ProfileSeriesDecks } from './ProfileSeriesDecks';
import { SavedSentencesTab } from './SavedSentencesTab';
import { SeriesDetailModal } from './SeriesDetailModal';
import { useTourPage } from '../tour/TourProvider';

interface ProfilePageProps {
  onNavigateToReader: () => void;
  onNavigateToFlashcards: () => void;
  userProfile: UserProfileData;
  onOpenAccountSettings: () => void;
  onOpenEditProfile: () => void;
  onNavigateToCatalog: () => void;
  onOpenReader: (target: ReaderTarget) => void;
  onRequireLogin: (message: string) => void;
  showToast: (message: string) => void;
  /** Mở mục Học tập của cài đặt tài khoản để khai báo trình độ. */
  onOpenLearningSettings: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  onNavigateToReader,
  userProfile,
  onOpenAccountSettings,
  onOpenEditProfile,
  onNavigateToCatalog,
  onOpenReader,
  onRequireLogin,
  showToast,
  onOpenLearningSettings
}) => {
  useTourPage('profile');
  const [openSeriesId, setOpenSeriesId] = useState<number | null>(null);
  const [activeProfileTab, setActiveProfileTab] = useState<'reading' | 'flashcards' | 'badges' | 'saved_bubbles' | 'error_reports'>('reading');
  const { streak } = useStreak();
  const stats = useLearningStats();
  const { overview, activity } = stats;

  // Số từ tích lũy là số mục trong Sổ tay trên máy chủ; chưa tải được thì dùng số trong hồ sơ.
  const [vocabTotal, setVocabTotal] = useState<number | null>(null);
  useEffect(() => {
    let cancelled = false;
    countVocab()
      .then(total => {
        if (!cancelled) setVocabTotal(total);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const wordsTotal = overview?.words_total ?? 0;
  const knownPercent = wordsTotal > 0 && overview ? (overview.words_known / wordsTotal) * 100 : 0;
  const learningPercent = wordsTotal > 0 && overview ? (overview.words_learning / wordsTotal) * 100 : 0;
  const pagesDelta = activity?.delta.pages_read ?? 0;
  const studyHours = overview ? Math.round((overview.study_seconds_total / 3600) * 10) / 10 : userProfile.hoursLearned;
  const weekStudyMinutes = activity ? Math.round(activity.current_week.study_seconds / 60) : 0;
  const weekdayOf = (iso: string): string => ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'][new Date(`${iso}T00:00:00`).getDay()];

  // Huy hiệu, VIP và khung avatar lấy từ máy chủ (M16, M17); chưa đeo huy hiệu thì không hiện viên huy hiệu.
  const { wallet, me } = useRewards();
  const equippedBadge = me?.equipped_badge ?? null;
  const isVip = wallet?.vip.is_active ?? false;

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-8">
      
      {/* PROFILE HERO BANNER & IDENTITY CARD */}
      <div className="relative w-full rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none overflow-hidden p-6 md:p-10 border border-pink-100 dark:border-slate-800 transition-colors duration-300">
        
        {/* Decorative Atmospheric Header Pattern */}
        <div className="absolute top-0 inset-x-0 h-40 bg-gradient-to-r from-pink-200/60 via-[#eff4ff] to-blue-200/50 dark:from-pink-900/30 dark:via-[#1e293b] dark:to-blue-900/30 -z-0">
          <svg className="w-full h-full opacity-30 object-cover" preserveAspectRatio="none" viewBox="0 0 800 200">
            <path className="text-pink-300" d="M0,80 C150,140 350,10 500,70 C650,130 750,40 800,90 L800,0 L0,0 Z" fill="currentColor"></path>
            <circle className="text-[#a43073]/30" cx="120" cy="50" fill="currentColor" r="14"></circle>
            <circle className="text-[#0060ac]/20" cx="280" cy="30" fill="currentColor" r="8"></circle>
            <circle className="text-pink-400/30" cx="640" cy="45" fill="currentColor" r="20"></circle>
          </svg>
        </div>

        {/* Identity Meta Layout */}
        <div className="relative z-10 pt-16 sm:pt-12 flex flex-col lg:flex-row items-start lg:items-end justify-between gap-6">
          
          {/* Avatar & Main Info */}
          <div className="flex flex-col sm:flex-row items-center sm:items-end gap-6 text-center sm:text-left">
            
            {/* Avatar with Pink Bloom Shadow */}
            <div className="relative group">
              <div className="absolute -inset-1 rounded-full bg-gradient-to-tr from-[#a43073] via-pink-400 to-[#64a8fe] opacity-80 blur-md group-hover:opacity-100 transition duration-300"></div>
              <AvatarFrame styleKey={wallet?.equipped_frame?.style_key} isVip={isVip} className="relative">
                <div className="relative w-28 h-28 sm:w-36 sm:h-36 rounded-full p-1 bg-white dark:bg-[#0f172a]">
                  <ProfileAvatar
                    serverUrl={userProfile.avatarUrl}
                    fallbackSrc={userProfile.avatar}
                    alt={`${userProfile.name} Avatar`}
                    className="w-full h-full rounded-full object-cover shadow-inner"
                  />
                </div>
              </AvatarFrame>
              <span className="absolute bottom-1 right-2 w-7 h-7 rounded-full bg-white dark:bg-[#0f172a] p-0.5 shadow-md dark:shadow-none flex items-center justify-center">
                <span className="w-full h-full rounded-full bg-emerald-500 flex items-center justify-center text-white">
                  <span className="material-symbols-outlined text-[14px]">bolt</span>
                </span>
              </span>
            </div>

            {/* Name & Badges */}
            <div className="flex flex-col gap-1.5">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-800 dark:text-white tracking-tight font-['Plus_Jakarta_Sans']">
                  {userProfile.name}
                </h1>
                {userProfile.chineseName.trim() && (
                  <span className="text-xl font-bold text-[#a43073] dark:text-pink-400 font-['Noto_Serif_SC']">
                    ({userProfile.chineseName})
                  </span>
                )}

                {/* Equipped Achievement Badge */}
                {equippedBadge && <BadgeChip badge={equippedBadge} showTier />}
                {isVip && <VipPill />}
              </div>

              {/* HSK Rank Tag & ID */}
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 text-xs font-semibold">
                <span className="text-[#0060ac] dark:text-blue-300">{userProfile.hskLevel}</span>
                <span className="text-slate-300 dark:text-slate-600">•</span>
                <span className="text-slate-500 dark:text-slate-400 font-mono">ID: {userProfile.id}</span>
                <span className="text-slate-300 dark:text-slate-600">•</span>
                <span className="text-slate-500 dark:text-slate-400">
                  {wallet ? (isVip ? `VIP đến ${formatVipUntil(wallet.vip.vip_until)}` : 'Chưa kích hoạt VIP') : 'VIP: —'}
                </span>
              </div>

              {/* Metadata chips */}
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-4 text-slate-500 dark:text-slate-400 text-xs pt-1">
                {userProfile.showJoinDate !== false && (
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px] text-[#a43073] dark:text-pink-400">calendar_today</span>
                    Tham gia: {userProfile.joinDate}
                  </span>
                )}
                {userProfile.showEmail !== false && (
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px] text-[#0060ac] dark:text-blue-300">mail</span>
                    {userProfile.email}
                  </span>
                )}
              </div>
            </div>

          </div>

          {/* Action CTAs */}
          <div className="flex items-center gap-3 w-full lg:w-auto justify-center sm:justify-end">
            <button
              onClick={onOpenAccountSettings}
              className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold transition-all shadow-xs dark:shadow-none"
            >
              <span className="material-symbols-outlined text-[18px]">tune</span>
              <span>Cài đặt tài khoản</span>
            </button>
            <button data-tour="profile-edit"
              onClick={onOpenEditProfile}
              className="flex items-center gap-1.5 px-5 py-2 rounded-full bg-gradient-to-r from-pink-500 to-rose-400 text-white text-xs font-bold hover:opacity-95 transition-all shadow-md shadow-pink-300/30"
            >
              <span className="material-symbols-outlined text-[18px]">edit_note</span>
              <span>Chỉnh sửa hồ sơ</span>
            </button>
          </div>

        </div>

      </div>

      {/* OVERVIEW STATS BENTO (4-Column) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Streak */}
        <div className="p-5 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 flex flex-col justify-between transition-colors duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400 font-bold">Chuỗi ngày đọc</span>
            <span className="p-2 rounded-full bg-[#ffd8e7] dark:bg-pink-900/30 text-[#a43073] dark:text-pink-400 flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">local_fire_department</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-extrabold text-slate-800 dark:text-white leading-none">
                {streak?.current_streak ?? 0}
              </span>
              <span className="text-sm font-bold text-[#a43073] dark:text-pink-400">Ngày liên tục 🔥</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {streak
                ? streak.studied_today
                  ? `Hôm nay bạn đã học rồi! Chuỗi dài nhất: ${streak.longest_streak} ngày.`
                  : `Học hôm nay để giữ lửa! Chuỗi dài nhất: ${streak.longest_streak} ngày.`
                : 'Chưa tải được chuỗi ngày học.'}
            </p>
          </div>

          {/* Weekly mini calendar check-in */}
          <div className="pt-2 flex items-center justify-between">
            {(streak?.week ?? []).map((day, index, days) => {
              const isToday = index === days.length - 1;
              return (
                <div key={day.date} className="flex flex-col items-center gap-1" title={`${day.date}: ${day.reviews_count} lượt ôn, ${day.pages_read} trang`}>
                  <span className={`text-[10px] ${isToday ? 'text-[#a43073] dark:text-pink-400 font-bold' : 'text-slate-400 dark:text-slate-500'}`}>{weekdayOf(day.date)}</span>
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      day.studied
                        ? isToday ? 'bg-[#a43073] text-white' : 'bg-[#ffd8e7] dark:bg-pink-900/30 text-[#a43073] dark:text-pink-400'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-300 dark:text-slate-600'
                    }`}
                  >
                    {day.studied ? (isToday ? '★' : '✓') : '·'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Card 2: Total Vocab */}
        <div className="p-5 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 flex flex-col justify-between transition-colors duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400 font-bold">Từ vựng tích lũy</span>
            <span className="p-2 rounded-full bg-blue-100 dark:bg-blue-900/30 text-[#0060ac] dark:text-blue-300 flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">translate</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl font-extrabold text-slate-800 dark:text-white leading-none">
                {vocabTotal ?? userProfile.totalVocab}
              </span>
              <span className="text-sm font-semibold text-[#0060ac] dark:text-blue-300">từ trong Sổ tay</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden flex">
              <div className="bg-[#0060ac] h-full" style={{ width: `${knownPercent}%` }}></div>
              <div className="bg-pink-400 h-full" style={{ width: `${learningPercent}%` }}></div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between text-xs font-semibold">
            <span className="text-[#0060ac] dark:text-blue-300">{overview ? `${overview.words_known} đã thuộc` : '— đã thuộc'}</span>
            <span className="text-[#a43073] dark:text-pink-400">{overview ? `${overview.cards_due} thẻ cần ôn lại` : '— cần ôn lại'}</span>
          </div>
        </div>

        {/* Card 3: Pages Read */}
        <div className="p-5 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 flex flex-col justify-between transition-colors duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400 font-bold">Trang truyện đã đọc</span>
            <span className="p-2 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-400 flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">auto_stories</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl font-extrabold text-slate-800 dark:text-white leading-none">
                {overview?.pages_read_total ?? userProfile.pagesRead}
              </span>
              <span className="text-sm font-semibold text-amber-800 dark:text-amber-400">trang manhua</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {activity
                ? pagesDelta === 0
                  ? 'Bằng tuần trước'
                  : `${pagesDelta > 0 ? '+' : ''}${pagesDelta} trang so với tuần trước`
                : 'Chưa tải được so sánh tuần'}
            </p>
          </div>

          <div className="pt-2 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span className="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
            <span>{activity ? `7 ngày qua: ${activity.current_week.pages_read} trang` : '7 ngày qua: —'}</span>
          </div>
        </div>

        {/* Card 4: Learning Time */}
        <div className="p-5 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 flex flex-col justify-between transition-colors duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400 font-bold">Thời gian học tập</span>
            <span className="p-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">timer</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl font-extrabold text-slate-800 dark:text-white leading-none">
                {studyHours}
              </span>
              <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">giờ</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{activity ? `Trung bình ${Math.round(weekStudyMinutes / 7)} phút mỗi ngày (7 ngày qua)` : 'Chưa tải được thời gian học'}</p>
          </div>

          <div className="pt-2 flex items-center gap-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
            <span className="material-symbols-outlined text-[16px]">trending_up</span>
            <span>{activity ? `${weekStudyMinutes} phút trong 7 ngày qua` : '—'}</span>
          </div>
        </div>

      </div>

      <div data-tour="profile-activity">
      <ProfileActivityChart
        activity={activity}
        overview={overview}
        loading={stats.loading}
        error={stats.error}
        onRetry={stats.reload}
      />
      </div>

      {/* MAIN TWO-COLUMN DASHBOARD (8 cols Left, 4 cols Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT TABS & VIEWS (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {/* Tab Navigation Bar */}
          <div className="bg-white dark:bg-[#0f172a] p-1.5 rounded-full shadow-xs dark:shadow-none border border-pink-100 dark:border-slate-800 flex items-center overflow-x-auto gap-1 custom-scrollbar">
            <button
              onClick={() => setActiveProfileTab('reading')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'reading'
                  ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">menu_book</span>
              <span>Truyện đang đọc dở</span>
            </button>
            <button
              onClick={() => setActiveProfileTab('flashcards')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'flashcards'
                  ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">style</span>
              <span>Flashcard theo truyện</span>
            </button>
            <button data-tour="profile-badges"
              onClick={() => setActiveProfileTab('badges')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'badges'
                  ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">military_tech</span>
              <span>Huy hiệu & Thành tựu</span>
            </button>
            <button
              onClick={() => setActiveProfileTab('saved_bubbles')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'saved_bubbles'
                  ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">bookmarks</span>
              <span>Ô thoại đã lưu</span>
            </button>
            <button
              onClick={() => setActiveProfileTab('error_reports')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'error_reports'
                  ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">flag</span>
              <span>Báo lỗi của tôi</span>
            </button>
          </div>

          {activeProfileTab === 'error_reports' && <ProfileErrorReports />}

          {/* TAB 1: TRUYỆN ĐANG ĐỌC DỞ */}
          {activeProfileTab === 'reading' && (
              <ProfileReadingList
                onOpenReader={onOpenReader}
                onBrowse={onNavigateToCatalog}
                onOpenLearningSettings={onOpenLearningSettings}
              />
          )}

          {/* TAB 2: FLASHCARD THEO TRUYỆN */}
          {activeProfileTab === 'flashcards' && <ProfileSeriesDecks onBrowse={onNavigateToCatalog} />}

          {/* TAB 3: HUY HIỆU & THÀNH TỰU */}
          {activeProfileTab === 'badges' && <ProfileBadgesTab showToast={showToast} />}

          {/* TAB 4: Ô THOẠI ĐÃ LƯU */}
          {activeProfileTab === 'saved_bubbles' && (
            <SavedSentencesTab onOpenReader={onOpenReader} showToast={showToast} />
          )}

        </div>

        {/* RIGHT SIDEBAR (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Target Weekly Card */}
          <WeeklyGoalCard onOpenLearningSettings={onOpenLearningSettings} />

          <div data-tour="profile-wallet">
          <ProfileWalletCard />
          </div>

          {/* Recommended Manhua HSK 4 */}
          <ProfileRecommendations
            onOpenSeries={setOpenSeriesId}
            onBrowse={onNavigateToCatalog}
            onOpenLearningSettings={onOpenLearningSettings}
          />

        </div>

      </div>

      <SeriesDetailModal
        seriesId={openSeriesId}
        isLoggedIn
        onClose={() => setOpenSeriesId(null)}
        onOpenReader={onOpenReader}
        onRequireLogin={onRequireLogin}
        showToast={showToast}
      />

    </div>
  );
};
