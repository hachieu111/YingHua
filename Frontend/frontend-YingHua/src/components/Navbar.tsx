import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { NavigationTab } from '../types';
import { SearchHit, hskLabel, searchWords } from '../api/dictionary';
import { ProfileAvatar } from './ProfileAvatar';
import { NotificationBell } from './NotificationBell';
import { useStreak } from '../utils/useStreak';
import { useRewards } from '../utils/useRewards';
import { REWARD_SHOP_PATH } from '../routes';
import { AvatarFrame } from './AvatarFrame';
import { rippleOriginOf, useTheme } from '../utils/useTheme';
import { useTour } from '../tour/TourProvider';
import { TourReplayButton } from '../tour/TourReplayButton';

interface NavbarProps {
  activeTab: NavigationTab | null;
  setActiveTab: (tab: NavigationTab) => void;
  onOpenUpload: () => void;
  onOpenAuth: (mode: 'login' | 'register') => void;
  isLoggedIn: boolean;
  isAdmin: boolean;
  onToggleLogin: () => void;
  onLookupWord: (term: string) => void;
  userAvatar?: string;
  /** Avatar đã tải lên máy chủ (ưu tiên hơn userAvatar). */
  userAvatarUrl?: string | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onOpenUpload,
  onOpenAuth,
  isLoggedIn,
  isAdmin,
  onLookupWord,
  userAvatar,
  userAvatarUrl
}) => {
  const { streak } = useStreak();
  const { wallet, me } = useRewards();
  const { theme, toggleTheme } = useTheme();
  const { replay } = useTour();
  const isDark = theme === 'dark';
  const themeLabel = isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối';
  const streakDays = isLoggedIn ? streak?.current_streak ?? 0 : 0;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SearchHit[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const searchBoxRef = useRef<HTMLDivElement>(null);

  // Tìm từ điển (F06.01) sau khi người dùng ngừng gõ ~300ms.
  useEffect(() => {
    const q = searchQuery.trim();
    if (q.length < 1) {
      setSuggestions([]);
      setSearchLoading(false);
      setSearchError(null);
      return;
    }
    let cancelled = false;
    setSearchLoading(true);
    const timer = window.setTimeout(() => {
      searchWords(q)
        .then(page => {
          if (cancelled) return;
          setSuggestions(page.items);
          setSearchError(null);
        })
        .catch(() => {
          if (cancelled) return;
          setSuggestions([]);
          setSearchError('Không thể tìm kiếm lúc này');
        })
        .finally(() => {
          if (!cancelled) setSearchLoading(false);
        });
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchQuery]);

  // Đóng gợi ý khi bấm ra ngoài hoặc nhấn Esc.
  useEffect(() => {
    const onPointerDown = (e: MouseEvent) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target as Node)) setSuggestOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSuggestOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, []);

  const openLookup = (term: string) => {
    setSuggestOpen(false);
    onLookupWord(term);
  };

  return (
    <header className="fixed top-0 inset-x-0 z-50 glass-nav border-b border-pink-100/70 dark:border-slate-800 shadow-[0_1px_8px_rgba(0,0,0,0.03)] dark:shadow-none transition-colors duration-300">
      <div className="h-20 max-w-[1440px] mx-auto px-4 md:px-6 lg:px-8 flex items-center justify-between gap-3">
        
        {/* Brand Logo */}
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button
            onClick={() => setActiveTab('catalog')}
            className="flex items-center gap-3 group text-left focus:outline-none"
          >
            <div className="w-9 h-9 rounded-full overflow-hidden shadow-sm dark:shadow-none border border-pink-200/80 dark:border-pink-900/40 bg-white dark:bg-slate-800 flex items-center justify-center group-hover:scale-105 transition-transform">
              <img
                src="/assets/imagetest/media_1792630135660_75497c66.png"
                alt="Yinghua Cherry Blossom Logo"
                className="w-full h-full object-contain rounded-full p-0.5"
              />
            </div>
            <div className="flex flex-col">
              <span className="whitespace-nowrap font-bold text-lg text-[#a43073] dark:text-pink-400 tracking-tight flex items-center gap-1.5 font-['Plus_Jakarta_Sans']">
                Yinghua <span className="hidden sm:inline whitespace-nowrap text-xs text-[#64a8fe] font-medium font-['Noto_Serif_SC']">(樱花)</span>
              </span>
            </div>
          </button>

          {/* Desktop Nav Pills */}
          <nav data-tour="nav-links" className="hidden 2xl:flex min-w-0 flex-1 items-center justify-center gap-0.5 p-1 rounded-full bg-[#eff4ff] dark:bg-[#1e293b] transition-colors duration-300">
            <button
              onClick={() => setActiveTab('catalog')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'catalog'
                  ? 'bg-[#f472b6] text-white shadow-sm dark:bg-[#a43073]'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              Trang Chủ
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'leaderboard'
                  ? 'bg-[#f472b6] text-white shadow-sm dark:bg-[#a43073]'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              Bảng Xếp Hạng
            </button>
            <button
              onClick={() => setActiveTab('reader')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'reader'
                  ? 'bg-[#f472b6] text-white shadow-sm dark:bg-[#a43073]'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              <span>Đọc Truyện</span>
            </button>
            {isLoggedIn && <button
              onClick={() => setActiveTab('library')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'library'
                  ? 'bg-[#f472b6] text-white shadow-sm dark:bg-[#a43073]'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              <span>Thư Viện</span>
            </button>}
            <button
              onClick={() => setActiveTab('flashcards')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'flashcards'
                  ? 'bg-[#f472b6] text-white shadow-sm dark:bg-[#a43073]'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              <span>Từ Vựng & Flashcard</span>
            </button>
            {isAdmin && <button
              onClick={() => setActiveTab('admin')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'admin'
                  ? 'bg-[#f472b6] text-white shadow-sm dark:bg-[#a43073]'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              Quản trị
            </button>}
          </nav>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3 sm:gap-4">
          
          {/* Quick Search */}
          <div ref={searchBoxRef} data-tour="nav-search" className="relative hidden md:flex items-center">
            <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px] pointer-events-none">
              search
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSuggestOpen(true);
              }}
              onFocus={() => setSuggestOpen(true)}
              onKeyDown={(e) => {
                if (e.key !== 'Enter') return;
                const q = searchQuery.trim();
                if (q) openLookup(suggestions[0]?.term ?? q);
              }}
              placeholder="Tìm manhua, từ vựng HSK..."
              className="w-44 lg:w-60 pl-9 pr-4 py-1.5 rounded-full bg-white dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 text-xs shadow-[0_1px_4px_rgba(0,0,0,0.04)] dark:shadow-none border border-pink-100/60 dark:border-slate-700 outline-none focus:ring-2 focus:ring-[#f472b6] transition-colors duration-300 placeholder:text-slate-400 dark:placeholder:text-slate-500"
            />
            {suggestOpen && searchQuery.trim() !== '' && (
              <div className="absolute top-full right-0 mt-2 w-72 lg:w-80 max-h-96 overflow-y-auto bg-white dark:bg-slate-800 rounded-2xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 py-1.5 z-50">
                {searchLoading && suggestions.length === 0 && (
                  <div className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">Đang tìm...</div>
                )}
                {!searchLoading && searchError && (
                  <div className="px-4 py-3 text-xs text-rose-600 dark:text-rose-400">{searchError}</div>
                )}
                {!searchLoading && !searchError && suggestions.length === 0 && (
                  <div className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">Không tìm thấy từ phù hợp</div>
                )}
                {suggestions.map(hit => (
                  <button
                    key={`${hit.term}-${hit.pinyin}`}
                    onClick={() => openLookup(hit.term)}
                    className="w-full text-left px-4 py-2 hover:bg-pink-50 dark:hover:bg-slate-700 flex flex-col gap-0.5"
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-base font-bold text-slate-800 dark:text-slate-100 font-['Noto_Serif_SC']">{hit.term}</span>
                      <span className="text-[11px] font-mono text-blue-600 dark:text-blue-400">{hit.pinyin}</span>
                      <span className="ml-auto px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-400 text-[10px] font-bold whitespace-nowrap">
                        {hskLabel(hit.hsk_level)}
                      </span>
                    </span>
                    {hit.preview && <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{hit.preview}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Upload Button */}
          <button
            data-tour="nav-upload"
            onClick={onOpenUpload}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-pink-500 to-rose-400 text-white text-xs font-semibold shadow-xs hover:shadow-md hover:scale-105 transition-all"
            title="Tải ảnh manhua cần dịch"
          >
            <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
            <span>Dịch ảnh</span>
          </button>

          {/* Nút sáng/tối: màn nhỏ dùng nút trong menu để thanh đầu không chật */}
                      <button
              data-tour="nav-theme"
              onClick={event => toggleTheme(rippleOriginOf(event))}
              className="hidden sm:flex w-9 h-9 shrink-0 rounded-full bg-white dark:bg-[#1e293b] border border-pink-100 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-[#a43073] dark:hover:text-pink-400 hover:border-pink-300 dark:hover:border-pink-900/60 items-center justify-center shadow-xs dark:shadow-none transition-colors duration-300"
              title={themeLabel}
              aria-label={themeLabel}
            >
              <span
                translate="no"
                className={`material-symbols-outlined text-[20px] transition-transform duration-500 ${isDark ? 'rotate-180' : 'rotate-0'}`}
              >
                {isDark ? 'light_mode' : 'dark_mode'}
              </span>
            </button>

          {/* Màn rộng không có menu ☰ nên cần lối riêng để xem lại hướng dẫn */}
          <TourReplayButton className="hidden 2xl:flex" />

          {/* Streak Indicator Pill */}
          <div data-tour="nav-streak" className={`${isLoggedIn ? 'inline-flex' : 'hidden sm:inline-flex'} items-center gap-1.5 px-2 sm:px-3 py-1 rounded-full bg-[#dce9ff] dark:bg-[#1e293b] shadow-xs dark:shadow-none whitespace-nowrap shrink-0 transition-colors duration-300`}>
            <span className="flex items-center gap-1 text-xs font-semibold text-slate-800 dark:text-slate-100 whitespace-nowrap shrink-0">
              {streakDays}<span className="hidden sm:inline"> ngày</span> <span className="text-[#a43073] text-[15px] leading-none dark:text-pink-400">🔥</span>
            </span>
            <span className="hidden sm:inline text-[11px] text-[#0060ac] dark:text-blue-400 font-bold whitespace-nowrap shrink-0" title="XP kiếm được hôm nay">
              {isLoggedIn && me ? `+${me.xp_today.toLocaleString('vi-VN')} XP` : '— XP'}
            </span>
          </div>

          {isLoggedIn && (
            <Link
              to={REWARD_SHOP_PATH}
              className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-400 text-xs font-bold shadow-xs dark:shadow-none whitespace-nowrap shrink-0 hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors"
              title="Cửa hàng đổi thưởng: xu và vé của bạn"
            >
              <span className="material-symbols-outlined text-[15px]">toll</span>
              {wallet ? wallet.coin_balance.toLocaleString('vi-VN') : '—'}
              {wallet?.vip.is_active && <span className="px-1.5 rounded-full bg-amber-400 text-amber-950 text-[9px] font-extrabold">VIP</span>}
            </Link>
          )}

          {isLoggedIn && <NotificationBell />}

          {/* User Profile / Auth Toggle */}
          {isLoggedIn ? (
            <button
              data-tour="nav-profile"
              onClick={() => setActiveTab('profile')}
              className={`flex items-center rounded-full p-0.5 transition-all ring-2 ${
                activeTab === 'profile' ? 'ring-[#a43073]' : 'ring-pink-200 dark:ring-pink-900/60 hover:ring-[#a43073] dark:hover:ring-pink-400'
              }`}
              title="Hồ sơ cá nhân"
            >
              <AvatarFrame styleKey={wallet?.equipped_frame?.style_key} isVip={wallet?.vip.is_active ?? false}>
                <ProfileAvatar
                  serverUrl={userAvatarUrl}
                  fallbackSrc={userAvatar || 'https://lh3.googleusercontent.com/aida-public/AB6AXuDouZjBIU9lI8mNPf-eu9v9WtamqAGj2p9GPjLNQt-W3hkLMoboWClFeN1wnO4reJTt623UqgtV7sJWTBZNtrFULAAXa_41CVt1ROrHqL64Mt0hCpqhgY5UTLxSAkXf-fdF7PnB-_CsuutWeSJYspalRkRCCKxE8AkIKcYGrOLBFHbjBFp6Ljll9-mSx90EzZUcRzR8Cj7_VM-vjsotklPmMQYldFasjlGLovnzMABNqni9r2ipQklp'}
                  alt="User Profile Avatar"
                  className="w-8 h-8 rounded-full object-cover"
                />
              </AvatarFrame>
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onOpenAuth('login')}
                className="px-3 py-1 rounded-full text-xs font-semibold text-[#a43073] dark:text-pink-400 hover:bg-pink-50 dark:hover:bg-pink-900/20 transition-colors"
              >
                Đăng nhập
              </button>
              <button
                data-tour="nav-register"
                onClick={() => onOpenAuth('register')}
                className="px-3.5 py-1.5 rounded-full text-xs font-bold text-white bg-[#a43073] hover:opacity-95 shadow-sm transition-all"
              >
                Đăng ký
              </button>
            </div>
          )}

          {/* Mobile hamburger */}
          <button
            data-tour="nav-menu"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="2xl:hidden p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <span className="material-symbols-outlined text-[24px]">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="2xl:hidden bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-xl border-b border-pink-100 dark:border-slate-800 px-6 py-4 flex flex-col gap-2">
          <button
            onClick={() => { setActiveTab('catalog'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'catalog' ? 'bg-[#f472b6] text-white dark:bg-[#a43073]' : 'text-slate-700 dark:text-slate-200'
            }`}
          >
            <span>Trang Chủ (Khám Phá)</span>
            <span className="material-symbols-outlined text-[18px]">explore</span>
          </button>
          <button
            onClick={() => { setActiveTab('leaderboard'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'leaderboard' ? 'bg-[#f472b6] text-white dark:bg-[#a43073]' : 'text-slate-700 dark:text-slate-200'
            }`}
          >
            <span>Bảng Vàng Danh Dự</span>
            <span className="material-symbols-outlined text-[18px]">military_tech</span>
          </button>
          <button
            onClick={() => { setActiveTab('reader'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'reader' ? 'bg-[#f472b6] text-white dark:bg-[#a43073]' : 'text-slate-700 dark:text-slate-200'
            }`}
          >
            <span>Đọc Truyện Tranh</span>
            <span className="material-symbols-outlined text-[18px]">menu_book</span>
          </button>
          {isLoggedIn && <button
            onClick={() => { setActiveTab('library'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'library' ? 'bg-[#f472b6] text-white dark:bg-[#a43073]' : 'text-slate-700 dark:text-slate-200'
            }`}
          >
            <span>Thư Viện Của Bạn</span>
            <span className="material-symbols-outlined text-[18px]">collections_bookmark</span>
          </button>}
          <button
            onClick={() => { setActiveTab('flashcards'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'flashcards' ? 'bg-[#f472b6] text-white dark:bg-[#a43073]' : 'text-slate-700 dark:text-slate-200'
            }`}
          >
            <span>Từ Vựng & Flashcard 3D</span>
            <span className="material-symbols-outlined text-[18px]">style</span>
          </button>
          <button
            onClick={() => { setActiveTab('profile'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'profile' ? 'bg-[#f472b6] text-white dark:bg-[#a43073]' : 'text-slate-700 dark:text-slate-200'
            }`}
          >
            <span>Hồ Sơ Cá Nhân</span>
            <span className="material-symbols-outlined text-[18px]">person</span>
          </button>
          {isLoggedIn && <Link
            to={REWARD_SHOP_PATH}
            onClick={() => setMobileMenuOpen(false)}
            className="px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between text-slate-700 dark:text-slate-200"
          >
            <span>Cửa Hàng Đổi Thưởng{wallet ? ` · ${wallet.coin_balance.toLocaleString('vi-VN')} xu` : ''}</span>
            <span className="material-symbols-outlined text-[18px]">storefront</span>
          </Link>}
                      <button
              onClick={event => toggleTheme(rippleOriginOf(event))}
              className="sm:hidden px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between text-slate-700 dark:text-slate-200"
            >
              <span>{isDark ? 'Giao diện sáng' : 'Giao diện tối'}</span>
              <span translate="no" className="material-symbols-outlined text-[18px]">{isDark ? 'light_mode' : 'dark_mode'}</span>
            </button>
          <button
            onClick={() => { replay(); setMobileMenuOpen(false); }}
            className="px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between text-slate-700 dark:text-slate-200"
          >
            <span>Xem lại hướng dẫn</span>
            <span translate="no" className="material-symbols-outlined text-[18px]">help</span>
          </button>
          {isAdmin && <button
            onClick={() => { setActiveTab('admin'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'admin' ? 'bg-[#f472b6] text-white dark:bg-[#a43073]' : 'text-slate-700 dark:text-slate-200'
            }`}
          >
            <span>Trung Tâm Quản Trị</span>
            <span className="material-symbols-outlined text-[18px]">admin_panel_settings</span>
          </button>}
        </div>
      )}
    </header>
  );
};
