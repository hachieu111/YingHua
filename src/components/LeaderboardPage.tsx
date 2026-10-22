import React, { useState } from 'react';
import { BookOpen, Flame, Layers, Star } from 'lucide-react';
import { LEADERBOARD_USERS } from '../data/mockData';

export const LeaderboardPage: React.FC = () => {
  const [timeFilter, setTimeFilter] = useState<'week' | 'month' | 'all'>('week');
  const [metricFilter, setMetricFilter] = useState<'exp' | 'vocab' | 'pages' | 'streak'>('exp');
  const [showExtendedRanks, setShowExtendedRanks] = useState<boolean>(false);
  const [completedQuests, setCompletedQuests] = useState<number[]>([1, 2]);

  const metricConfig = {
    streak: { label: 'Chuỗi Streak', unit: 'ngày streak', getValue: (user: typeof LEADERBOARD_USERS[number]) => user.streakDays },
    exp: { label: 'Điểm EXP Học Tập', unit: 'EXP', getValue: (user: typeof LEADERBOARD_USERS[number]) => user.exp },
    vocab: { label: 'Từ vựng ghi nhớ', unit: 'từ', getValue: (user: typeof LEADERBOARD_USERS[number]) => user.vocabCount ?? 100 },
    pages: { label: 'Trang Manhua đã đọc', unit: 'trang', getValue: (user: typeof LEADERBOARD_USERS[number]) => user.pagesRead }
  };
  const timeConfig = {
    week: { label: 'Tuần này', multiplier: 0.12 },
    month: { label: 'Tháng này', multiplier: 0.4 },
    all: { label: 'Toàn thời gian', multiplier: 1 }
  };
  const activeMetric = metricConfig[metricFilter];
  const activeTime = timeConfig[timeFilter];
  const getScore = (user: typeof LEADERBOARD_USERS[number]) =>
    Math.max(1, Math.round(activeMetric.getValue(user) * activeTime.multiplier));
  const rankedUsers = [...LEADERBOARD_USERS]
    .sort((a, b) => getScore(b) - getScore(a))
    .map((user, index) => ({ ...user, rank: index + 1 }));
  const top1 = rankedUsers[0];
  const top2 = rankedUsers[1];
  const top3 = rankedUsers[2];
  const currentUser = rankedUsers.find((user) => user.isCurrentUser) || rankedUsers[rankedUsers.length - 1];
  const formatScore = (user: typeof currentUser) => getScore(user).toLocaleString();

  const handleDoQuest3 = () => {
    if (!completedQuests.includes(3)) {
      setCompletedQuests([...completedQuests, 3]);
      alert('Tuyệt vời! Bạn vừa hoàn thành bài kiểm tra và nhận được +30 EXP! Thứ hạng tăng lên #17!');
    }
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-10">
      
      {/* HEADER SECTION & SEASON INFO */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="flex flex-col gap-2 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] font-bold text-xs shadow-xs">
              <span>🌸</span> Mùa Đua Top Hoa Anh Đào • Kỳ 42
            </span>
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-bold text-xs">
              <span className="material-symbols-outlined text-[15px]">timer</span>
              <span>Còn 3 ngày 14 giờ</span>
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight flex items-center gap-3 font-['Plus_Jakarta_Sans']">
            <span>Bảng Vàng Danh Dự Yinghua</span>
            <span className="text-[#a43073] font-['Noto_Serif_SC'] italic text-2xl font-light">榜样</span>
          </h1>

          <p className="text-sm text-slate-600 leading-relaxed">
            Nỗ lực tích luỹ từng từ vựng trong trang manhua, mở rộng cánh cửa tri thức Hán ngữ. Đua top sôi nổi, rinh trọn huy hiệu mùa giải danh giá và đặc quyền đọc truyện không giới hạn!
          </p>
        </div>

        {/* Quick Summary Stats Pill */}
        <div className="flex items-center gap-4 p-3 rounded-2xl bg-white shadow-soft border border-pink-100">
          <div className="px-3 py-1 border-r border-slate-100 flex flex-col">
            <span className="text-[10px] text-slate-400 font-bold uppercase">Tổng học viên</span>
            <span className="text-xl font-bold text-[#0060ac]">1,420</span>
          </div>
          <div className="px-3 py-1 border-r border-slate-100 flex flex-col">
            <span className="text-[10px] text-slate-400 font-bold uppercase">Trang truyện đọc</span>
            <span className="text-xl font-bold text-[#a43073]">38,420</span>
          </div>
          <div className="px-3 py-1 flex flex-col">
            <span className="text-[10px] text-slate-400 font-bold uppercase">Điểm EXP mùa này</span>
            <span className="text-xl font-bold text-amber-600">142.5k</span>
          </div>
        </div>
      </div>

      {/* FILTER CONTROLS BAR */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 p-2 bg-[#eff4ff] rounded-2xl border border-blue-100">
        {/* Time filter */}
        <div role="group" aria-label="Lọc theo thời gian" className="flex items-center p-1 rounded-full bg-white shadow-xs gap-1 shrink-0">
          {([
            { id: 'week', label: 'Tuần này' },
            { id: 'month', label: 'Tháng này' },
            { id: 'all', label: 'Toàn thời gian' }
          ] as const).map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTimeFilter(id)}
              aria-pressed={timeFilter === id}
              className={`px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                timeFilter === id ? 'bg-[#f472b6] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Metric tabs: each selection displays its own ranking view */}
        <div role="tablist" aria-label="Chọn bảng xếp hạng" className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 custom-scrollbar">
          {([
            { id: 'streak', label: 'Chuỗi Streak', Icon: Flame },
            { id: 'exp', label: 'Điểm EXP Học Tập', Icon: Star },
            { id: 'vocab', label: 'Từ vựng ghi nhớ', Icon: Layers },
            { id: 'pages', label: 'Trang Manhua đã đọc', Icon: BookOpen }
          ] as const).map(({ id, label, Icon }) => (
            <button
              key={id}
              role="tab"
              aria-selected={metricFilter === id}
              onClick={() => setMetricFilter(id)}
              className={`inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                metricFilter === id
                  ? 'bg-[#0060ac] text-white shadow-xs'
                  : 'bg-white text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" strokeWidth={2} aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* MAIN TWO-COLUMN BODY (8 Cols Left, 4 Cols Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT COLUMN: Podium, User Sticky Card, Leaderboard List (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-8">
          
          {/* PODIUM: TOP 3 STAGE */}
          <div className="relative w-full rounded-3xl bg-gradient-to-b from-white via-white/80 to-[#eff4ff] p-6 sm:p-10 shadow-soft border border-pink-100 overflow-hidden">
            <div className="absolute -top-20 -left-20 w-64 h-64 bg-amber-100/40 rounded-full blur-3xl pointer-events-none"></div>
            <div className="absolute -bottom-10 right-0 w-72 h-72 bg-pink-100/40 rounded-full blur-3xl pointer-events-none"></div>

            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#a43073] text-[24px]">workspace_premium</span>
                <span className="text-xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
                  Top 3 · {activeMetric.label}
                </span>
              </div>
              <span className="text-xs text-slate-500 flex items-center gap-1.5 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                <span>Cập nhật theo thời gian thực</span>
              </span>
            </div>

            {/* Podium Visual Grid */}
            <div className="grid grid-cols-3 items-end gap-2 sm:gap-4 md:gap-6 pt-4">
              
              {/* TOP 2 (Bạc) */}
              <div className="flex flex-col items-center order-1 group">
                <div className="relative flex flex-col items-center mb-3 transition-transform duration-300 group-hover:-translate-y-1">
                  <span className="px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-700 text-xs font-bold shadow-xs mb-1">
                    🥈 #2
                  </span>
                  <div className="relative w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 rounded-full p-1 bg-gradient-to-tr from-slate-300 via-white to-slate-400 shadow-md">
                    <img
                      src={top2.avatar}
                      alt={top2.name}
                      className="w-full h-full object-cover rounded-full"
                    />
                    <span className="absolute bottom-0 right-0 px-2 py-0.5 bg-white text-[#0060ac] text-[10px] font-bold rounded-full shadow-xs">
                      {top2.hskLevel}
                    </span>
                  </div>
                </div>
                <div className="text-center mb-2">
                  <h4 className="font-bold text-xs sm:text-sm text-slate-800 truncate max-w-[90px] sm:max-w-[120px]">
                    {top2.name}
                  </h4>
                  <span className="text-[11px] text-slate-400 block font-medium">
                    Đọc {top2.pagesRead} trang
                  </span>
                </div>
                {/* Pedestal Box 2 */}
                <div className="w-full h-32 sm:h-36 md:h-44 rounded-2xl bg-gradient-to-t from-slate-200 via-slate-100 to-white p-3 flex flex-col items-center justify-between shadow-xs border-t-2 border-slate-300">
                  <span className="text-lg sm:text-xl font-extrabold text-slate-700">
                    {formatScore(top2)}
                  </span>
                  <div className="w-full flex flex-col items-center gap-1">
                    <span className="text-[10px] text-slate-500 font-bold uppercase">{activeMetric.unit}</span>
                    <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-900 text-[10px] font-bold">
                      🔥 {top2.streakDays} ngày
                    </span>
                  </div>
                </div>
              </div>

              {/* TOP 1 (Vàng - Quán Quân) */}
              <div className="flex flex-col items-center order-2 group">
                <div className="relative flex flex-col items-center mb-3 transition-transform duration-300 group-hover:-translate-y-2">
                  <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-gradient-to-r from-amber-300 via-amber-200 to-amber-300 text-amber-900 text-xs font-extrabold shadow-md mb-1.5 animate-bounce">
                    <span className="material-symbols-outlined text-[16px]">military_tech</span>
                    <span>#1 Quán Quân</span>
                  </div>
                  <div className="relative w-20 h-20 sm:w-28 sm:h-28 md:w-32 md:h-32 rounded-full p-1.5 bg-gradient-to-tr from-amber-400 via-pink-300 to-rose-300 shadow-xl ring-4 ring-amber-200">
                    <img
                      src={top1.avatar}
                      alt={top1.name}
                      className="w-full h-full object-cover rounded-full"
                    />
                    <span className="absolute -top-3 -right-1 text-2xl transform rotate-12 drop-shadow-md">👑</span>
                    <span className="absolute bottom-0 right-1 px-2.5 py-0.5 bg-amber-400 text-amber-950 text-[11px] font-extrabold rounded-full shadow-xs">
                      {top1.hskLevel}
                    </span>
                  </div>
                </div>
                <div className="text-center mb-2">
                  <h3 className="font-extrabold text-sm sm:text-base text-slate-900 truncate max-w-[110px] sm:max-w-[150px]">
                    {top1.name}
                  </h3>
                  <span className="inline-flex items-center gap-1 text-[11px] text-[#a43073] font-bold">
                    <span className="material-symbols-outlined text-[14px]">auto_stories</span>
                    Đọc {top1.pagesRead} trang
                  </span>
                </div>
                {/* Pedestal Box 1 */}
                <div className="w-full h-44 sm:h-52 md:h-60 rounded-3xl bg-gradient-to-t from-amber-100 via-amber-50 to-white p-4 flex flex-col items-center justify-between shadow-lg border-t-4 border-amber-300 relative overflow-hidden">
                  <div className="flex flex-col items-center">
                    <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-['Plus_Jakarta_Sans']">
                      {formatScore(top1)}
                    </span>
                    <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider">
                      {activeMetric.label}
                    </span>
                  </div>
                  <div className="w-full flex flex-col items-center gap-1.5">
                    <span className="px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] text-[10px] font-bold flex items-center gap-1">
                      <span>🌸</span> {top1.tag}
                    </span>
                    <span className="text-[10px] text-slate-500 font-medium">
                      {top1.vocabCount} từ vựng mới
                    </span>
                  </div>
                </div>
              </div>

              {/* TOP 3 (Đồng) */}
              <div className="flex flex-col items-center order-3 group">
                <div className="relative flex flex-col items-center mb-3 transition-transform duration-300 group-hover:-translate-y-1">
                  <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 text-xs font-bold shadow-xs mb-1">
                    🥉 #3
                  </span>
                  <div className="relative w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 rounded-full p-1 bg-gradient-to-tr from-amber-600 via-amber-200 to-amber-500 shadow-md">
                    <img
                      src={top3.avatar}
                      alt={top3.name}
                      className="w-full h-full object-cover rounded-full"
                    />
                    <span className="absolute bottom-0 right-0 px-2 py-0.5 bg-white text-[#0060ac] text-[10px] font-bold rounded-full shadow-xs">
                      {top3.hskLevel}
                    </span>
                  </div>
                </div>
                <div className="text-center mb-2">
                  <h4 className="font-bold text-xs sm:text-sm text-slate-800 truncate max-w-[90px] sm:max-w-[120px]">
                    {top3.name}
                  </h4>
                  <span className="text-[11px] text-slate-400 block font-medium">
                    Đọc {top3.pagesRead} trang
                  </span>
                </div>
                {/* Pedestal Box 3 */}
                <div className="w-full h-28 sm:h-32 md:h-40 rounded-2xl bg-gradient-to-t from-amber-200/50 via-amber-100/50 to-white p-3 flex flex-col items-center justify-between shadow-xs border-t-2 border-amber-400">
                  <span className="text-lg sm:text-xl font-extrabold text-amber-900">
                    {formatScore(top3)}
                  </span>
                  <div className="w-full flex flex-col items-center gap-1">
                    <span className="text-[10px] text-slate-500 font-bold uppercase">{activeMetric.unit}</span>
                    <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-900 text-[10px] font-bold">
                      🔥 {top3.streakDays} ngày
                    </span>
                  </div>
                </div>
              </div>

            </div>
          </div>

          {/* STICKY USER RANK CARD (Vị trí của bạn) */}
          <div className="sticky top-24 z-30 w-full p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-pink-100/90 via-white to-blue-100/80 backdrop-blur-xl shadow-md border border-pink-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex flex-col items-center justify-center w-12 h-12 rounded-2xl bg-[#a43073] text-white shadow-xs shrink-0">
                <span className="text-[10px] uppercase font-bold">Hạng</span>
                <span className="text-base font-extrabold leading-tight">#{currentUser.rank}</span>
              </div>

              <div className="relative shrink-0">
                <img
                  src={currentUser.avatar}
                  alt={currentUser.name}
                  className="w-12 h-12 rounded-full object-cover ring-2 ring-[#a43073]"
                />
                <span className="absolute -bottom-1 -right-1 px-1.5 py-0.2 bg-[#0060ac] text-white text-[9px] font-bold rounded-full">
                  HSK 4
                </span>
              </div>

              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-sm text-slate-800">{currentUser.name}</h3>
                  <span className="px-2 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[10px] font-bold">
                    Bạn
                  </span>
                </div>
                <div className="flex items-center gap-2 text-slate-500 text-xs mt-0.5">
                  <span className="font-bold text-[#a43073]">{formatScore(currentUser)} {activeMetric.unit}</span>
                  <span>•</span>
                  <span>{activeTime.label}</span>
                </div>
              </div>
            </div>

            {/* Next Rank Push CTA */}
            <div className="w-full sm:w-auto flex flex-col sm:items-end gap-1.5 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-200/60">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  Chỉ cần thêm <strong className="text-[#a43073]">80 EXP</strong> để lọt
                </span>
                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-900 text-xs font-bold">
                  Top 15
                </span>
              </div>
              <div className="w-full sm:w-48 h-2 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-pink-400 to-[#a43073] rounded-full" style={{ width: '78%' }}></div>
              </div>
            </div>
          </div>

          {/* DETAILED LEADERBOARD LIST (Ranks #4 to #10 and expandable) */}
          <div className="flex flex-col rounded-3xl bg-white shadow-soft border border-pink-100 p-4 sm:p-6">
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100 text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Xếp hạng</span>
              <div className="hidden sm:flex items-center gap-10">
                <span className="w-24 text-center">Tiến độ HSK</span>
                <span className="w-24 text-center">Trang Manhua</span>
                <span className="w-24 text-right">{activeMetric.unit}</span>
              </div>
              <span className="sm:hidden">{activeMetric.unit}</span>
            </div>

            <div className="divide-y divide-slate-100">
              {rankedUsers.slice(3, showExtendedRanks ? 15 : 10).map((user) => (
                <div
                  key={user.rank}
                  className="flex items-center justify-between p-3.5 hover:bg-slate-50/70 transition-colors rounded-2xl"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <span className="w-6 text-center text-sm font-bold text-slate-400">
                      {user.rank}
                    </span>
                    <img
                      src={user.avatar}
                      alt={user.name}
                      className="w-10 h-10 rounded-full object-cover shrink-0"
                    />
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs sm:text-sm text-slate-800 truncate">
                          {user.name}
                        </span>
                        {user.tag && (
                          <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] font-bold">
                            {user.tag}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-400">
                        {user.vocabCount || 100} từ vựng • Streak {user.streakDays} ngày
                      </span>
                    </div>
                  </div>

                  <div className="hidden sm:flex items-center gap-10">
                    <div className="w-24 text-center">
                      <span className="px-2.5 py-1 rounded-full bg-[#eff4ff] text-[#0060ac] text-xs font-bold">
                        {user.hskLevel}
                      </span>
                    </div>
                    <span className="w-24 text-center text-xs text-slate-600 font-medium">
                      {user.pagesRead} trang
                    </span>
                    <span className="w-24 text-right text-sm font-bold text-[#a43073]">
                      {formatScore(user)}
                    </span>
                  </div>

                  <span className="sm:hidden text-xs font-bold text-[#a43073]">
                    {formatScore(user)}
                  </span>
                </div>
              ))}
            </div>

            {/* Expand / Collapse Button */}
            <button
              onClick={() => setShowExtendedRanks(!showExtendedRanks)}
              className="w-full mt-3 py-2 rounded-2xl bg-slate-50 hover:bg-slate-100 text-[#a43073] font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>{showExtendedRanks ? 'Thu gọn bảng xếp hạng' : 'Xem thêm Hạng 11 - 15'}</span>
              <span className="material-symbols-outlined text-[18px]">
                {showExtendedRanks ? 'expand_less' : 'expand_more'}
              </span>
            </button>
          </div>

        </div>

        {/* RIGHT COLUMN: Season Rewards & Daily Quests (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* SEASON REWARDS CARD */}
          <div className="rounded-3xl bg-white p-6 shadow-soft border border-pink-100 relative overflow-hidden">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#a43073] text-[22px]">card_giftcard</span>
                <h3 className="text-base font-bold text-slate-800">Phần Thưởng Mùa Giải</h3>
              </div>
              <span className="px-2.5 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[11px] font-bold">
                Tháng 10
              </span>
            </div>

            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              Giữ vững thứ hạng trước 23:59 Chủ Nhật tuần này để nhận trọn bộ quà tặng giới hạn:
            </p>

            <div className="flex flex-col gap-3">
              {/* Tier 1: Top 1-3 */}
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-[#eff4ff]">
                <div className="w-10 h-10 rounded-xl bg-amber-200 flex items-center justify-center text-amber-950 text-lg shrink-0">
                  🥇
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-slate-800">Top 1 ~ 3</span>
                    <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-900 text-[10px] font-bold">Đặc sắc</span>
                  </div>
                  <ul className="text-[11px] text-slate-600 mt-1 space-y-0.5">
                    <li className="flex items-center gap-1">
                      <span className="text-[#a43073]">✓</span> Khung Avatar VIP "Hoa Anh Đào Vàng"
                    </li>
                    <li className="flex items-center gap-1">
                      <span className="text-[#a43073]">✓</span> Mở khoá toàn bộ Manhua VIP 1 tháng
                    </li>
                    <li className="flex items-center gap-1">
                      <span className="text-[#a43073]">✓</span> Danh hiệu: "Đệ Nhất Học Giả"
                    </li>
                  </ul>
                </div>
              </div>

              {/* Tier 2: Top 4-10 */}
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-[#eff4ff]">
                <div className="w-10 h-10 rounded-xl bg-slate-200 flex items-center justify-center text-slate-700 text-lg shrink-0">
                  🥈
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-slate-800">Top 4 ~ 10</span>
                  <ul className="text-[11px] text-slate-600 mt-1 space-y-0.5">
                    <li className="flex items-center gap-1">
                      <span className="text-blue-600">✓</span> Khung Avatar "Cánh Hoa Mùa Xuân"
                    </li>
                    <li className="flex items-center gap-1">
                      <span className="text-blue-600">✓</span> 3 Vé Đọc Truyện VIP tuỳ chọn
                    </li>
                  </ul>
                </div>
              </div>

              {/* Tier 3: Top 11-50 */}
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-[#eff4ff]">
                <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-800 text-lg shrink-0">
                  🎖️
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-slate-800">Top 11 ~ 50 (Có bạn!)</span>
                  <ul className="text-[11px] text-slate-600 mt-1 space-y-0.5">
                    <li className="flex items-center gap-1">
                      <span className="text-[#a43073]">✓</span> 500 Xu Sakura mua giáo trình Flashcard
                    </li>
                    <li className="flex items-center gap-1">
                      <span className="text-[#a43073]">✓</span> Huy hiệu tích lũy: "Người Gieo Hạt"
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* DAILY EXP QUESTS CARD */}
          <div className="rounded-3xl bg-white p-6 shadow-soft border border-pink-100">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#0060ac] text-[22px]">task_alt</span>
                <h3 className="text-base font-bold text-slate-800">Nhiệm Vụ Kiếm EXP</h3>
              </div>
              <span className="text-xs font-bold text-[#a43073]">
                {completedQuests.length}/3 hoàn thành
              </span>
            </div>

            <p className="text-xs text-slate-500 mb-4">
              Hoàn thành các thử thách học tập hàng ngày để tăng bậc xếp hạng nhanh chóng!
            </p>

            <div className="flex flex-col gap-2.5">
              {/* Quest 1 */}
              <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-50">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-[#a43073] flex items-center justify-center text-white text-xs">
                    <span className="material-symbols-outlined text-[14px]">check</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-slate-600 line-through">
                      Đọc 2 trang truyện Manhua mới
                    </span>
                    <span className="text-[10px] text-slate-400">Đã đọc 2/2 trang</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[10px] font-bold">
                  +20 XP ✓
                </span>
              </div>

              {/* Quest 2 */}
              <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-50">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-[#a43073] flex items-center justify-center text-white text-xs">
                    <span className="material-symbols-outlined text-[14px]">check</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-slate-600 line-through">
                      Lật 15 thẻ từ vựng Flashcard
                    </span>
                    <span className="text-[10px] text-slate-400">Đã lật 15/15 thẻ</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[10px] font-bold">
                  +15 XP ✓
                </span>
              </div>

              {/* Quest 3 */}
              <div className="flex items-center justify-between p-3 rounded-2xl bg-[#eff4ff]">
                <div className="flex items-center gap-2.5">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs ${
                    completedQuests.includes(3) ? 'bg-[#a43073] text-white' : 'bg-white text-blue-700 shadow-xs'
                  }`}>
                    <span className="material-symbols-outlined text-[14px]">
                      {completedQuests.includes(3) ? 'check' : 'quiz'}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className={`text-xs font-bold ${completedQuests.includes(3) ? 'line-through text-slate-500' : 'text-slate-800'}`}>
                      Làm 1 bài kiểm tra từ HSK
                    </span>
                    <span className="text-[10px] text-blue-600 font-medium">
                      {completedQuests.includes(3) ? 'Đã hoàn thành' : 'Chưa hoàn thành'}
                    </span>
                  </div>
                </div>
                {completedQuests.includes(3) ? (
                  <span className="px-2 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[10px] font-bold">
                    +30 XP ✓
                  </span>
                ) : (
                  <button
                    onClick={handleDoQuest3}
                    className="px-3 py-1 rounded-full bg-[#0060ac] text-white text-[11px] font-bold hover:bg-[#004883] transition-colors"
                  >
                    Làm ngay (+30 XP)
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* WEEKLY ACTIVITY GRAPH */}
          <div className="rounded-3xl bg-white p-6 shadow-soft border border-pink-100">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-bold text-slate-800">Hoạt Động Tuần Của Bạn</h4>
              <span className="text-xs text-slate-500 font-semibold">Tổng: 1,250 XP</span>
            </div>

            <div className="flex items-end justify-between h-28 pt-4 px-2 gap-2">
              {[
                { day: 'T2', val: 120, height: '35%' },
                { day: 'T3', val: 180, height: '52%' },
                { day: 'T4', val: 140, height: '42%' },
                { day: 'T5', val: 260, height: '75%' },
                { day: 'T6', val: 310, height: '90%', active: true },
                { day: 'T7', val: 240, height: '68%' },
                { day: 'CN', val: '-', height: '20%', dashed: true }
              ].map((item, i) => (
                <div key={i} className="flex flex-col items-center gap-1 flex-1">
                  <span className="text-[10px] text-slate-400">{item.val}</span>
                  <div
                    className={`w-full rounded-t-lg transition-all ${
                      item.active
                        ? 'bg-[#f472b6]'
                        : item.dashed
                        ? 'bg-slate-100 border-2 border-dashed border-slate-300'
                        : 'bg-slate-200 hover:bg-[#a43073]'
                    }`}
                    style={{ height: item.height }}
                  ></div>
                  <span className={`text-[11px] font-bold ${item.active ? 'text-[#a43073]' : 'text-slate-500'}`}>
                    {item.day}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">Tốc độ học hiện tại:</span>
              <span className="font-bold text-[#0060ac]">+18% so với tuần trước 📈</span>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};
