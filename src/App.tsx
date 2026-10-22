import React, { useState } from 'react';
import { NavigationTab, UserProfileData, VocabularyItem } from './types';
import { CURRENT_USER } from './data/mockData';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { ComicReader } from './components/ComicReader';
import { CatalogPage } from './components/CatalogPage';
import { LibraryPage } from './components/LibraryPage';
import { FlashcardsPage } from './components/FlashcardsPage';
import { LeaderboardPage } from './components/LeaderboardPage';
import { ProfilePage } from './components/ProfilePage';
import { AuthModals } from './components/AuthModals';
import { UploadModal } from './components/UploadModal';
import { AccountSettingsModal } from './components/AccountSettingsModal';
import { EditProfileModal } from './components/EditProfileModal';
import { AdminDashboard } from './components/AdminDashboard';

const PROFILE_VISIBILITY_STORAGE_KEY = 'yinghua-profile-visibility';

const getSavedProfileVisibility = (): Pick<UserProfileData, 'showEmail' | 'showJoinDate'> => {
  try {
    const saved = localStorage.getItem(PROFILE_VISIBILITY_STORAGE_KEY);
    if (saved) {
      const visibility = JSON.parse(saved) as Partial<Pick<UserProfileData, 'showEmail' | 'showJoinDate'>>;
      return {
        showEmail: typeof visibility.showEmail === 'boolean' ? visibility.showEmail : true,
        showJoinDate: typeof visibility.showJoinDate === 'boolean' ? visibility.showJoinDate : true
      };
    }
  } catch {
    // Fall back to visible profile details if saved preferences are unavailable.
  }
  return { showEmail: true, showJoinDate: true };
};

export default function App() {
  // Trang Chủ (catalog) is default home page
  const [activeTab, setActiveTab] = useState<NavigationTab>('catalog');
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [userProfile, setUserProfile] = useState<UserProfileData>(() => ({
    ...CURRENT_USER,
    ...getSavedProfileVisibility()
  }));
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register' | null>(null);
  const [authPrompt, setAuthPrompt] = useState<string | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);
  const [accountSettingsOpen, setAccountSettingsOpen] = useState<boolean>(false);
  const [editProfileOpen, setEditProfileOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  // Only Trang Chủ and Bảng Vàng Danh Dự are publicly viewable without authentication
  const isPublicTab = (tab: NavigationTab) => tab === 'catalog' || tab === 'leaderboard' || tab === 'admin';

  const handleNavigate = (tab: NavigationTab) => {
    if (!isLoggedIn && !isPublicTab(tab)) {
      const featureNames: Record<string, string> = {
        reader: 'đọc truyện tranh và tra cứu tương tác',
        library: 'truy cập Thư Viện cá nhân',
        flashcards: 'luyện từ vựng và Flashcard 3D',
        profile: 'xem và quản lý Hồ Sơ cá nhân'
      };
      const featureText = featureNames[tab] || 'sử dụng tính năng này';
      setAuthPrompt(`Vui lòng đăng nhập để ${featureText}!`);
      setAuthModalMode('login');
      showToast('Vui lòng đăng nhập để tiếp tục.');
      return;
    }
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectComic = (_comicId: string) => {
    if (!isLoggedIn) {
      setAuthPrompt('Vui lòng đăng nhập để đọc chương truyện và tra từ tương tác!');
      setAuthModalMode('login');
      showToast('Vui lòng đăng nhập để đọc truyện.');
      return;
    }
    setActiveTab('reader');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenUpload = () => {
    if (!isLoggedIn) {
      setAuthPrompt('Vui lòng đăng nhập để tải ảnh manhua và sử dụng OCR dịch tự động!');
      setAuthModalMode('login');
      showToast('Vui lòng đăng nhập để tải ảnh dịch.');
      return;
    }
    setUploadModalOpen(true);
  };

  const handleUploadSuccess = (_imageSrc: string) => {
    showToast('Tải lên thành công! AI đã phân tích bóng thoại và tạo bản dịch tương tác.');
    setActiveTab('reader');
  };

  const handleUpdateEmail = (newEmail: string) => {
    setUserProfile(prev => ({ ...prev, email: newEmail }));
  };

  const handleUpdateProfileVisibility = (setting: 'showEmail' | 'showJoinDate', visible: boolean) => {
    const updatedVisibility = {
      showEmail: setting === 'showEmail' ? visible : userProfile.showEmail !== false,
      showJoinDate: setting === 'showJoinDate' ? visible : userProfile.showJoinDate !== false
    };
    setUserProfile(prev => ({ ...prev, ...updatedVisibility }));
    try {
      localStorage.setItem(PROFILE_VISIBILITY_STORAGE_KEY, JSON.stringify(updatedVisibility));
    } catch {
      // The current session still updates if browser storage is unavailable.
    }
    showToast(`${setting === 'showEmail' ? 'Email' : 'Ngày tham gia'} đã được ${visible ? 'hiển thị' : 'ẩn'} trên hồ sơ.`);
  };

  const handleSaveProfile = (updated: Partial<UserProfileData>) => {
    setUserProfile(prev => ({ ...prev, ...updated }));
  };

  // Logout handler: Immediately redirects to Trang Chủ (catalog)
  const handleLogout = () => {
    setIsLoggedIn(false);
    setAccountSettingsOpen(false);
    setAuthModalMode(null);
    setAuthPrompt(null);
    setActiveTab('catalog'); // Trở về trang chủ luôn khi đăng xuất
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToast('Bạn đã đăng xuất thành công và trở về Trang Chủ.');
  };

  return (
    <div className="min-h-screen bg-[#f8f9ff] text-[#0b1c30] flex flex-col font-['Inter'] selection:bg-[#ffd8e7] selection:text-[#3d0026]">
      
      {/* Top Navbar */}
      {activeTab !== 'admin' && <Navbar
        activeTab={activeTab}
        setActiveTab={handleNavigate}
        onOpenUpload={handleOpenUpload}
        onOpenAuth={(mode) => {
          setAuthPrompt(null);
          setAuthModalMode(mode);
        }}
        isLoggedIn={isLoggedIn}
        onToggleLogin={isLoggedIn ? handleLogout : () => setAuthModalMode('login')}
        userAvatar={userProfile.avatar}
      />}

      {/* Main Screen Content */}
      <main className={`flex-1 w-full ${activeTab === 'admin' ? '' : 'pt-20'}`}>
        {/* Route Guard Fallback: If not logged in and not on public tab */}
        {activeTab === 'admin' ? (
          <AdminDashboard onOpenLearnerView={() => handleNavigate('catalog')} />
        ) : !isLoggedIn && !isPublicTab(activeTab) ? (
          <div className="w-full max-w-[700px] mx-auto px-4 py-16 flex flex-col items-center text-center gap-6">
            <div className="w-20 h-20 rounded-3xl bg-pink-100 flex items-center justify-center text-[#a43073] shadow-md border border-pink-200">
              <span className="material-symbols-outlined text-[42px]">lock</span>
            </div>
            <div className="flex flex-col gap-2">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-800 font-['Plus_Jakarta_Sans']">
                Yêu cầu đăng nhập tài khoản
              </h2>
              <p className="text-sm text-slate-600 max-w-lg leading-relaxed">
                Trang này dành riêng cho thành viên của Yinghua để lưu tiến độ học tập, đánh dấu từ vựng và xem lịch sử đọc truyện. Trừ <strong>Trang Chủ</strong> và <strong>Bảng Vàng Danh Dự</strong>, vui lòng đăng nhập để trải nghiệm toàn bộ tính năng!
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                onClick={() => {
                  setAuthPrompt('Vui lòng đăng nhập để truy cập trang này!');
                  setAuthModalMode('login');
                }}
                className="px-6 py-3 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs sm:text-sm shadow-md shadow-pink-300/30 transition-all flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">login</span>
                <span>Đăng nhập ngay</span>
              </button>
              <button
                onClick={() => {
                  setAuthPrompt(null);
                  setAuthModalMode('register');
                }}
                className="px-6 py-3 rounded-full bg-white hover:bg-pink-50 text-[#a43073] border border-pink-200 font-bold text-xs sm:text-sm shadow-xs transition-all flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">person_add</span>
                <span>Đăng ký thành viên mới</span>
              </button>
              <button
                onClick={() => handleNavigate('catalog')}
                className="px-5 py-3 rounded-full text-slate-600 hover:text-slate-900 hover:bg-slate-100 text-xs sm:text-sm font-semibold transition-all"
              >
                Về Trang Chủ
              </button>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'catalog' && (
              <CatalogPage
                onSelectComic={handleSelectComic}
                onNavigateToFlashcards={() => handleNavigate('flashcards')}
              />
            )}

            {activeTab === 'leaderboard' && (
              <LeaderboardPage />
            )}

            {activeTab === 'reader' && (
              <ComicReader
                onOpenUpload={handleOpenUpload}
                onSaveVocab={(word: VocabularyItem) => {
                  try {
                    const saved = JSON.parse(localStorage.getItem('yinghua-reader-flashcards') || '[]') as VocabularyItem[];
                    if (!saved.some(item => item.hanzi === word.hanzi)) {
                      localStorage.setItem('yinghua-reader-flashcards', JSON.stringify([...saved, word]));
                    }
                  } catch {
                    showToast('Không thể lưu từ vựng vào bộ nhớ trình duyệt.');
                    return;
                  }
                  showToast(`Đã lưu "${word.hanzi}" vào bộ Flashcard cá nhân!`);
                }}
              />
            )}

            {activeTab === 'library' && (
              <LibraryPage
                onOpenUpload={handleOpenUpload}
                onSelectComic={handleSelectComic}
                onNavigateToFlashcards={() => handleNavigate('flashcards')}
              />
            )}

            {activeTab === 'flashcards' && (
              <FlashcardsPage
                onNavigateToReader={() => handleNavigate('reader')}
              />
            )}

            {activeTab === 'profile' && (
              <ProfilePage
                onNavigateToReader={() => handleNavigate('reader')}
                onNavigateToFlashcards={() => handleNavigate('flashcards')}
                userProfile={userProfile}
                onOpenAccountSettings={() => setAccountSettingsOpen(true)}
                onOpenEditProfile={() => setEditProfileOpen(true)}
              />
            )}
          </>
        )}
      </main>

      {/* Global Toast Alert */}
      {toastMessage && (
        <div className="fixed top-24 right-6 z-50 bg-white/95 backdrop-blur-md px-4 py-3 rounded-2xl shadow-floating border border-pink-200 text-xs font-bold text-slate-800 flex items-center gap-2 animate-bounce">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Auth Modals (Login & Register with Learning Goal Selection) */}
      <AuthModals
        mode={authModalMode}
        promptMessage={authPrompt}
        onClose={() => {
          setAuthModalMode(null);
          setAuthPrompt(null);
        }}
        onSuccess={() => {
          setIsLoggedIn(true);
          setAuthModalMode(null);
          setAuthPrompt(null);
          showToast('Đăng nhập thành công! Chào mừng bạn đến với Yinghua.');
        }}
        onSwitchMode={(newMode) => setAuthModalMode(newMode)}
      />

      {/* Upload Manhua OCR Modal */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Account Settings Modal (Đổi mật khẩu, Đổi mail, Đăng xuất) */}
      <AccountSettingsModal
        isOpen={accountSettingsOpen}
        onClose={() => setAccountSettingsOpen(false)}
        currentEmail={userProfile.email}
        showEmail={userProfile.showEmail !== false}
        showJoinDate={userProfile.showJoinDate !== false}
        onUpdateVisibility={handleUpdateProfileVisibility}
        onUpdateEmail={handleUpdateEmail}
        onLogout={handleLogout}
        showToast={showToast}
      />

      {/* Edit Profile Modal (Đổi tên, Đổi avatar, Đổi thẻ thành tựu) */}
      <EditProfileModal
        isOpen={editProfileOpen}
        onClose={() => setEditProfileOpen(false)}
        userProfile={userProfile}
        onSaveProfile={handleSaveProfile}
        showToast={showToast}
      />

      {/* Unified Footer */}
      {activeTab !== 'admin' && <Footer
        setActiveTab={handleNavigate}
      />}

    </div>
  );
}
