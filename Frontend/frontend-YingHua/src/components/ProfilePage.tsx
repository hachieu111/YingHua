import React, { useEffect, useState } from 'react';
import { countVocab } from '../api/vocab';
import { ReaderTarget, UserProfileData } from '../types';
import { AVAILABLE_BADGES } from '../data/achievements';
import { ProfileAvatar } from './ProfileAvatar';
import { ProfileReadingList } from './ProfileReadingList';
import { ProfileRecommendations } from './ProfileRecommendations';
import { SavedSentencesTab } from './SavedSentencesTab';
import { SeriesDetailModal } from './SeriesDetailModal';

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
  onNavigateToFlashcards,
  userProfile,
  onOpenAccountSettings,
  onOpenEditProfile,
  onNavigateToCatalog,
  onOpenReader,
  onRequireLogin,
  showToast,
  onOpenLearningSettings
}) => {
  const [openSeriesId, setOpenSeriesId] = useState<number | null>(null);
  const [activeProfileTab, setActiveProfileTab] = useState<'reading' | 'flashcards' | 'badges' | 'saved_bubbles'>('reading');

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

  const equippedBadge = AVAILABLE_BADGES.find((badge) => badge.title === userProfile.badge) ?? AVAILABLE_BADGES[0];
  const EquippedBadgeIcon = equippedBadge.icon;

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-8">
      
      {/* PROFILE HERO BANNER & IDENTITY CARD */}
      <div className="relative w-full rounded-3xl bg-white shadow-soft overflow-hidden p-6 md:p-10 border border-pink-100">
        
        {/* Decorative Atmospheric Header Pattern */}
        <div className="absolute top-0 inset-x-0 h-40 bg-gradient-to-r from-pink-200/60 via-[#eff4ff] to-blue-200/50 -z-0">
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
              <div className="relative w-28 h-28 sm:w-36 sm:h-36 rounded-full p-1 bg-white">
                <ProfileAvatar
                  serverUrl={userProfile.avatarUrl}
                  fallbackSrc={userProfile.avatar}
                  alt={`${userProfile.name} Avatar`}
                  className="w-full h-full rounded-full object-cover shadow-inner"
                />
              </div>
              <span className="absolute bottom-1 right-2 w-7 h-7 rounded-full bg-white p-0.5 shadow-md flex items-center justify-center">
                <span className="w-full h-full rounded-full bg-emerald-500 flex items-center justify-center text-white">
                  <span className="material-symbols-outlined text-[14px]">bolt</span>
                </span>
              </span>
            </div>

            {/* Name & Badges */}
            <div className="flex flex-col gap-1.5">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans']">
                  {userProfile.name}
                </h1>
                <span className="text-xl font-bold text-[#a43073] font-['Noto_Serif_SC']">
                  ({userProfile.chineseName})
                </span>
                
                {/* Equipped Achievement Badge */}
                <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full shadow-xs ${equippedBadge.color}`}>
                  <EquippedBadgeIcon className="w-3.5 h-3.5" strokeWidth={2.2} aria-hidden="true" />
                  <span className="text-[11px] font-bold tracking-wide uppercase">
                    {userProfile.badge}
                  </span>
                </div>
              </div>

              {/* HSK Rank Tag & ID */}
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 text-xs font-semibold">
                <span className="text-[#0060ac]">{userProfile.hskLevel}</span>
                <span className="text-slate-300">•</span>
                <span className="text-slate-500 font-mono">ID: {userProfile.id}</span>
                <span className="text-slate-300">•</span>
                <span className="text-slate-500">Hạn VIP: {userProfile.vipExpiry}</span>
              </div>

              {/* Metadata chips */}
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-4 text-slate-500 text-xs pt-1">
                {userProfile.showJoinDate !== false && (
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px] text-[#a43073]">calendar_today</span>
                    Tham gia: {userProfile.joinDate}
                  </span>
                )}
                {userProfile.showEmail !== false && (
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px] text-[#0060ac]">mail</span>
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
              className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-all shadow-xs"
            >
              <span className="material-symbols-outlined text-[18px]">tune</span>
              <span>Cài đặt tài khoản</span>
            </button>
            <button
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
        <div className="p-5 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-bold">Chuỗi ngày đọc</span>
            <span className="p-2 rounded-full bg-[#ffd8e7] text-[#a43073] flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">local_fire_department</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-extrabold text-slate-800 leading-none">
                {userProfile.streak}
              </span>
              <span className="text-sm font-bold text-[#a43073]">Ngày liên tục 🔥</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Đã giữ lửa liên tục 1 tuần lễ!</p>
          </div>

          {/* Weekly mini calendar check-in */}
          <div className="pt-2 flex items-center justify-between">
            {['T2', 'T3', 'T4', 'T5', 'T6', 'T7'].map((d, i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <span className="text-[10px] text-slate-400">{d}</span>
                <span className="w-6 h-6 rounded-full bg-[#ffd8e7] text-[#a43073] flex items-center justify-center text-[10px] font-bold">
                  ✓
                </span>
              </div>
            ))}
            <div className="flex flex-col items-center gap-1">
              <span className="text-[10px] text-[#a43073] font-bold">CN</span>
              <span className="w-6 h-6 rounded-full bg-[#a43073] text-white flex items-center justify-center text-[10px] font-bold animate-pulse">
                ★
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Total Vocab */}
        <div className="p-5 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-bold">Từ vựng tích lũy</span>
            <span className="p-2 rounded-full bg-blue-100 text-[#0060ac] flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">translate</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl font-extrabold text-slate-800 leading-none">
                {vocabTotal ?? userProfile.totalVocab}
              </span>
              <span className="text-sm font-semibold text-[#0060ac]">từ trong Sổ tay</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-slate-100 overflow-hidden flex">
              <div className="bg-[#0060ac] h-full" style={{ width: '65%' }}></div>
              <div className="bg-pink-400 h-full" style={{ width: '25%' }}></div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between text-xs font-semibold">
            <span className="text-[#0060ac]">128 đã thuộc</span>
            <span className="text-[#a43073]">58 cần ôn lại</span>
          </div>
        </div>

        {/* Card 3: Pages Read */}
        <div className="p-5 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-bold">Trang truyện đã đọc</span>
            <span className="p-2 rounded-full bg-amber-100 text-amber-900 flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">auto_stories</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl font-extrabold text-slate-800 leading-none">
                {userProfile.pagesRead}
              </span>
              <span className="text-sm font-semibold text-amber-800">trang manhua</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">+18 trang so với tuần trước</p>
          </div>

          <div className="pt-2 flex items-center gap-2 text-xs text-slate-500">
            <span className="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
            <span>Khoảng 24 chương truyện gốc</span>
          </div>
        </div>

        {/* Card 4: Learning Time */}
        <div className="p-5 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-bold">Thời gian học tập</span>
            <span className="p-2 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">timer</span>
            </span>
          </div>

          <div className="my-3">
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl font-extrabold text-slate-800 leading-none">
                {userProfile.hoursLearned}
              </span>
              <span className="text-sm font-semibold text-slate-500">giờ</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Trung bình 45 phút mỗi ngày</p>
          </div>

          <div className="pt-2 flex items-center gap-1 text-xs font-bold text-emerald-600">
            <span className="material-symbols-outlined text-[16px]">trending_up</span>
            <span>Đạt 112% mục tiêu tháng</span>
          </div>
        </div>

      </div>

      {/* MAIN TWO-COLUMN DASHBOARD (8 cols Left, 4 cols Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT TABS & VIEWS (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {/* Tab Navigation Bar */}
          <div className="bg-white p-1.5 rounded-full shadow-xs border border-pink-100 flex items-center overflow-x-auto gap-1 custom-scrollbar">
            <button
              onClick={() => setActiveProfileTab('reading')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'reading'
                  ? 'bg-[#f472b6] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">menu_book</span>
              <span>Truyện đang đọc dở</span>
            </button>
            <button
              onClick={() => setActiveProfileTab('flashcards')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'flashcards'
                  ? 'bg-[#f472b6] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">style</span>
              <span>Flashcard theo truyện</span>
            </button>
            <button
              onClick={() => setActiveProfileTab('badges')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'badges'
                  ? 'bg-[#f472b6] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">military_tech</span>
              <span>Huy hiệu & Thành tựu</span>
            </button>
            <button
              onClick={() => setActiveProfileTab('saved_bubbles')}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeProfileTab === 'saved_bubbles'
                  ? 'bg-[#f472b6] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">bookmarks</span>
              <span>Ô thoại đã lưu</span>
            </button>
          </div>

          {/* TAB 1: TRUYỆN ĐANG ĐỌC DỞ */}
          {activeProfileTab === 'reading' && (
              <ProfileReadingList
                onOpenReader={onOpenReader}
                onBrowse={onNavigateToCatalog}
                onOpenLearningSettings={onOpenLearningSettings}
              />
          )}

          {/* TAB 2: FLASHCARD THEO TRUYỆN */}
          {activeProfileTab === 'flashcards' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-5 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-xs font-bold">
                      Đấu La Đại Lục IV
                    </span>
                    <span className="text-xs text-slate-400">32 Từ vựng</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-800 mt-2">
                    Chương 12: Long Thần Huyết Mạch
                  </h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Từ trọng tâm: 血脉 (Huyết mạch), 觉醒 (Thức tỉnh), 精神力 (Tinh thần lực)
                  </p>
                  <div className="mt-3 flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-500">Thuộc: 20/32</span>
                    <span className="text-[#a43073]">Cần ôn: 12 từ</span>
                  </div>
                  <div className="w-full bg-slate-100 h-1.5 rounded-full mt-1.5 overflow-hidden">
                    <div className="bg-[#a43073] h-full rounded-full" style={{ width: '62.5%' }}></div>
                  </div>
                </div>
                <button
                  onClick={onNavigateToFlashcards}
                  className="mt-4 w-full py-2.5 rounded-full bg-[#f472b6] text-white text-xs font-bold shadow-xs hover:opacity-95 transition-all flex items-center justify-center gap-1"
                >
                  <span className="material-symbols-outlined text-[16px]">psychology</span>
                  <span>Ôn tập ngay</span>
                </button>
              </div>

              <div className="p-5 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-900 text-xs font-bold">
                      Toàn Chức Cao Thủ
                    </span>
                    <span className="text-xs text-slate-400">26 Từ vựng</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-800 mt-2">
                    Chương 34: Quân Mạc Tiếu Xuất Kích
                  </h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Từ khẩu ngữ: 账号 (Tài khoản), 战术 (Chiến thuật), 破绽 (Sơ hở)
                  </p>
                  <div className="mt-3 flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-500">Thuộc: 26/26</span>
                    <span className="text-emerald-600">Đã hoàn thành 100%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-1.5 rounded-full mt-1.5 overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '100%' }}></div>
                  </div>
                </div>
                <button
                  onClick={onNavigateToFlashcards}
                  className="mt-4 w-full py-2.5 rounded-full bg-slate-100 text-slate-700 text-xs font-bold hover:bg-slate-200 transition-all flex items-center justify-center gap-1"
                >
                  <span className="material-symbols-outlined text-[16px]">replay</span>
                  <span>Luyện lại lần nữa</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: HUY HIỆU & THÀNH TỰU */}
          {activeProfileTab === 'badges' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white p-5 rounded-3xl shadow-soft border border-pink-100 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-pink-100 text-[#a43073] flex items-center justify-center shadow-inner mb-3">
                  <span className="material-symbols-outlined text-[32px]">dark_mode</span>
                </div>
                <h4 className="font-bold text-sm text-slate-800">Cú đêm cày truyện</h4>
                <p className="text-xs text-slate-500 mt-1">Đọc hơn 50 trang manhua sau 23:00</p>
                <span className="mt-3 px-3 py-0.5 rounded-full bg-[#a43073] text-white text-[10px] font-bold">
                  Đạt Cấp III
                </span>
              </div>

              <div className="bg-white p-5 rounded-3xl shadow-soft border border-pink-100 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-blue-100 text-[#0060ac] flex items-center justify-center shadow-inner mb-3">
                  <span className="material-symbols-outlined text-[32px]">workspace_premium</span>
                </div>
                <h4 className="font-bold text-sm text-slate-800">Vua từ vựng HSK 3</h4>
                <p className="text-xs text-slate-500 mt-1">Hoàn thành 300 thẻ từ vựng cấp độ 3</p>
                <span className="mt-3 px-3 py-0.5 rounded-full bg-[#0060ac] text-white text-[10px] font-bold">
                  Hoàn Thành
                </span>
              </div>

              <div className="bg-white p-5 rounded-3xl shadow-soft border border-pink-100 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center shadow-inner mb-3">
                  <span className="material-symbols-outlined text-[32px]">translate</span>
                </div>
                <h4 className="font-bold text-sm text-slate-800">Dịch giả tập sự</h4>
                <p className="text-xs text-slate-500 mt-1">Tra cứu hơn 200 bong bóng thoại</p>
                <span className="mt-3 px-3 py-0.5 rounded-full bg-amber-400 text-amber-950 text-[10px] font-bold">
                  Tiến độ 182/200
                </span>
              </div>
            </div>
          )}

          {/* TAB 4: Ô THOẠI ĐÃ LƯU */}
          {activeProfileTab === 'saved_bubbles' && (
            <SavedSentencesTab onOpenReader={onOpenReader} showToast={showToast} />
          )}

        </div>

        {/* RIGHT SIDEBAR (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Target Weekly Card */}
          <div className="p-6 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#a43073] text-[20px]">flag</span>
                <span>Mục tiêu tuần này</span>
              </h3>
              <span className="text-xs font-bold text-[#0060ac]">70%</span>
            </div>

            <p className="text-xs text-slate-500">
              Đọc 20 trang manhua để duy trì đà ghi nhớ từ vựng tự nhiên.
            </p>

            <div className="flex flex-col gap-1.5 mt-1">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-slate-800">14 / 20 trang</span>
                <span className="text-slate-400">Còn 6 trang nữa</span>
              </div>
              <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                <div className="bg-gradient-to-r from-pink-400 to-[#a43073] h-full rounded-full" style={{ width: '70%' }}></div>
              </div>
            </div>

            <div className="p-3 rounded-2xl bg-[#eff4ff] flex items-center gap-3 mt-1">
              <span className="material-symbols-outlined text-[#a43073] text-[24px]">emoji_events</span>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-slate-800">Phần thưởng khi hoàn thành</span>
                <span className="text-[11px] text-slate-500">+150 XP và Khung Avatar Hoa Anh Đào Vàng</span>
              </div>
            </div>
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
