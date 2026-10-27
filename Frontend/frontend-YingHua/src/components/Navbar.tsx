import React, { useEffect, useRef, useState } from 'react';
import { NavigationTab } from '../types';
import { SearchHit, hskLabel, searchWords } from '../api/dictionary';
import { ProfileAvatar } from './ProfileAvatar';
import { NotificationBell } from './NotificationBell';
import { useStreak } from '../utils/useStreak';

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
    <header className="fixed top-0 inset-x-0 z-50 glass-nav border-b border-pink-100/70 shadow-[0_1px_8px_rgba(0,0,0,0.03)] transition-all">
      <div className="h-20 max-w-[1440px] mx-auto px-4 md:px-6 lg:px-8 flex items-center justify-between gap-3">
        
        {/* Brand Logo */}
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button
            onClick={() => setActiveTab('catalog')}
            className="flex items-center gap-3 group text-left focus:outline-none"
          >
            <div className="w-9 h-9 rounded-full overflow-hidden shadow-sm border border-pink-200/80 bg-white flex items-center justify-center group-hover:scale-105 transition-transform">
              <img
                src="/assets/imagetest/media_1792630135660_75497c66.png"
                alt="Yinghua Cherry Blossom Logo"
                className="w-full h-full object-contain rounded-full p-0.5"
              />
            </div>
            <div className="flex flex-col">
              <span className="whitespace-nowrap font-bold text-lg text-[#a43073] tracking-tight flex items-center gap-1.5 font-['Plus_Jakarta_Sans']">
                Yinghua <span className="whitespace-nowrap text-xs text-[#64a8fe] font-medium font-['Noto_Serif_SC']">(樱花)</span>
              </span>
            </div>
          </button>

          {/* Desktop Nav Pills */}
          <nav className="hidden 2xl:flex min-w-0 flex-1 items-center justify-center gap-0.5 p-1 rounded-full bg-[#eff4ff]">
            <button
              onClick={() => setActiveTab('catalog')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'catalog'
                  ? 'bg-[#f472b6] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Trang Chủ
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'leaderboard'
                  ? 'bg-[#f472b6] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Bảng Xếp Hạng
            </button>
            <button
              onClick={() => setActiveTab('reader')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'reader'
                  ? 'bg-[#f472b6] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>Đọc Truyện</span>
            </button>
            {isLoggedIn && <button
              onClick={() => setActiveTab('library')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'library'
                  ? 'bg-[#f472b6] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>Thư Viện</span>
            </button>}
            <button
              onClick={() => setActiveTab('flashcards')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'flashcards'
                  ? 'bg-[#f472b6] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>Từ Vựng & Flashcard</span>
            </button>
            {isAdmin && <button
              onClick={() => setActiveTab('admin')}
              className={`shrink-0 whitespace-nowrap px-3 py-2 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'admin'
                  ? 'bg-[#f472b6] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Quản trị
            </button>}
          </nav>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3 sm:gap-4">
          
          {/* Quick Search */}
          <div ref={searchBoxRef} className="relative hidden md:flex items-center">
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
              className="w-44 lg:w-60 pl-9 pr-4 py-1.5 rounded-full bg-white text-slate-800 text-xs shadow-[0_1px_4px_rgba(0,0,0,0.04)] border border-pink-100/60 outline-none focus:ring-2 focus:ring-[#f472b6] transition-all placeholder:text-slate-400"
            />
            {suggestOpen && searchQuery.trim() !== '' && (
              <div className="absolute top-full right-0 mt-2 w-72 lg:w-80 max-h-96 overflow-y-auto bg-white rounded-2xl shadow-floating border border-pink-100 py-1.5 z-50">
                {searchLoading && suggestions.length === 0 && (
                  <div className="px-4 py-3 text-xs text-slate-500">Đang tìm...</div>
                )}
                {!searchLoading && searchError && (
                  <div className="px-4 py-3 text-xs text-rose-600">{searchError}</div>
                )}
                {!searchLoading && !searchError && suggestions.length === 0 && (
                  <div className="px-4 py-3 text-xs text-slate-500">Không tìm thấy từ phù hợp</div>
                )}
                {suggestions.map(hit => (
                  <button
                    key={`${hit.term}-${hit.pinyin}`}
                    onClick={() => openLookup(hit.term)}
                    className="w-full text-left px-4 py-2 hover:bg-pink-50 flex flex-col gap-0.5"
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-base font-bold text-slate-800 font-['Noto_Serif_SC']">{hit.term}</span>
                      <span className="text-[11px] font-mono text-blue-600">{hit.pinyin}</span>
                      <span className="ml-auto px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] font-bold whitespace-nowrap">
                        {hskLabel(hit.hsk_level)}
                      </span>
                    </span>
                    {hit.preview && <span className="text-[11px] text-slate-500 truncate">{hit.preview}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Upload Button */}
          <button
            onClick={onOpenUpload}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-pink-500 to-rose-400 text-white text-xs font-semibold shadow-xs hover:shadow-md hover:scale-105 transition-all"
            title="Tải ảnh manhua cần dịch"
          >
            <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
            <span>Dịch ảnh</span>
          </button>

          {/* Streak Indicator Pill */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#dce9ff] shadow-xs whitespace-nowrap shrink-0">
            <span className="flex items-center gap-1 text-xs font-semibold text-slate-800 whitespace-nowrap shrink-0">
              {streakDays} ngày <span className="text-[#a43073] text-[15px] leading-none">🔥</span>
            </span>
            {/* TODO(M16): XP chưa có API (GĐ6.5); giữ hiển thị như thiết kế. */}
            <span className="hidden sm:inline text-[11px] text-[#0060ac] font-bold whitespace-nowrap shrink-0">
              +50 XP
            </span>
          </div>

          {isLoggedIn && <NotificationBell />}

          {/* User Profile / Auth Toggle */}
          {isLoggedIn ? (
            <button
              onClick={() => setActiveTab('profile')}
              className={`flex items-center rounded-full p-0.5 transition-all ring-2 ${
                activeTab === 'profile' ? 'ring-[#a43073]' : 'ring-pink-200 hover:ring-[#a43073]'
              }`}
              title="Hồ sơ cá nhân"
            >
              <ProfileAvatar
                serverUrl={userAvatarUrl}
                fallbackSrc={userAvatar || 'https://lh3.googleusercontent.com/aida-public/AB6AXuDouZjBIU9lI8mNPf-eu9v9WtamqAGj2p9GPjLNQt-W3hkLMoboWClFeN1wnO4reJTt623UqgtV7sJWTBZNtrFULAAXa_41CVt1ROrHqL64Mt0hCpqhgY5UTLxSAkXf-fdF7PnB-_CsuutWeSJYspalRkRCCKxE8AkIKcYGrOLBFHbjBFp6Ljll9-mSx90EzZUcRzR8Cj7_VM-vjsotklPmMQYldFasjlGLovnzMABNqni9r2ipQklp'}
                alt="User Profile Avatar"
                className="w-8 h-8 rounded-full object-cover"
              />
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onOpenAuth('login')}
                className="px-3 py-1 rounded-full text-xs font-semibold text-[#a43073] hover:bg-pink-50 transition-colors"
              >
                Đăng nhập
              </button>
              <button
                onClick={() => onOpenAuth('register')}
                className="px-3.5 py-1.5 rounded-full text-xs font-bold text-white bg-[#a43073] hover:opacity-95 shadow-sm transition-all"
              >
                Đăng ký
              </button>
            </div>
          )}

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="2xl:hidden p-2 rounded-xl text-slate-600 hover:bg-slate-100"
          >
            <span className="material-symbols-outlined text-[24px]">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="2xl:hidden bg-white/95 backdrop-blur-xl border-b border-pink-100 px-6 py-4 flex flex-col gap-2">
          <button
            onClick={() => { setActiveTab('catalog'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'catalog' ? 'bg-[#f472b6] text-white' : 'text-slate-700'
            }`}
          >
            <span>Trang Chủ (Khám Phá)</span>
            <span className="material-symbols-outlined text-[18px]">explore</span>
          </button>
          <button
            onClick={() => { setActiveTab('leaderboard'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'leaderboard' ? 'bg-[#f472b6] text-white' : 'text-slate-700'
            }`}
          >
            <span>Bảng Vàng Danh Dự</span>
            <span className="material-symbols-outlined text-[18px]">military_tech</span>
          </button>
          <button
            onClick={() => { setActiveTab('reader'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'reader' ? 'bg-[#f472b6] text-white' : 'text-slate-700'
            }`}
          >
            <span>Đọc Truyện Tranh</span>
            <span className="material-symbols-outlined text-[18px]">menu_book</span>
          </button>
          {isLoggedIn && <button
            onClick={() => { setActiveTab('library'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'library' ? 'bg-[#f472b6] text-white' : 'text-slate-700'
            }`}
          >
            <span>Thư Viện Của Bạn</span>
            <span className="material-symbols-outlined text-[18px]">collections_bookmark</span>
          </button>}
          <button
            onClick={() => { setActiveTab('flashcards'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'flashcards' ? 'bg-[#f472b6] text-white' : 'text-slate-700'
            }`}
          >
            <span>Từ Vựng & Flashcard 3D</span>
            <span className="material-symbols-outlined text-[18px]">style</span>
          </button>
          <button
            onClick={() => { setActiveTab('profile'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'profile' ? 'bg-[#f472b6] text-white' : 'text-slate-700'
            }`}
          >
            <span>Hồ Sơ Cá Nhân</span>
            <span className="material-symbols-outlined text-[18px]">person</span>
          </button>
          {isAdmin && <button
            onClick={() => { setActiveTab('admin'); setMobileMenuOpen(false); }}
            className={`px-4 py-2.5 rounded-xl text-left text-sm font-semibold flex items-center justify-between ${
              activeTab === 'admin' ? 'bg-[#f472b6] text-white' : 'text-slate-700'
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
