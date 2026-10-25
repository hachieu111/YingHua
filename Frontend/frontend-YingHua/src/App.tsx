import React, { useCallback, useEffect, useState } from 'react';
import { NavigationTab, ReaderTarget, UserProfileData } from './types';
import { CURRENT_USER } from './data/mockData';
import { ApiUser, getMe, hasStoredSession, logout, logoutAllDevices, removeAvatar, updateMe, uploadAvatar } from './api/auth';
import { ApiError, SESSION_EXPIRED_EVENT } from './api/client';
import { ApiSettings, getSettings } from './api/settings';
import { toUserProfile } from './api/profile';
import { ResetPasswordModal } from './components/ResetPasswordModal';
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
import { AccountSettingsTab } from './components/AccountSettingsModal';
import { AdminDashboard } from './components/AdminDashboard';
import { WordLookupModal } from './components/WordLookupModal';
import { SeriesManagerModal } from './components/SeriesManagerModal';
import { ApiPage } from './api/library';
import { setSpeechNoticeListener } from './utils/speech';

const RESET_TOKEN_PARAM = 'reset_token';

// Đọc mã đặt lại mật khẩu từ liên kết trong email (F01.06): /?reset_token=...
const readResetTokenFromUrl = (): string | null => new URLSearchParams(window.location.search).get(RESET_TOKEN_PARAM);

const clearResetTokenFromUrl = () => {
  const url = new URL(window.location.href);
  url.searchParams.delete(RESET_TOKEN_PARAM);
  window.history.replaceState({}, '', url.pathname + url.search + url.hash);
};

export default function App() {
  // Trang Chủ (catalog) is default home page
  const [activeTab, setActiveTab] = useState<NavigationTab>('catalog');
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [userProfile, setUserProfile] = useState<UserProfileData>(CURRENT_USER);
  // Chờ khôi phục phiên đăng nhập đã lưu để không nhấp nháy trang "Yêu cầu đăng nhập".
  const [authReady, setAuthReady] = useState<boolean>(() => !hasStoredSession());
  const [resetToken, setResetToken] = useState<string | null>(readResetTokenFromUrl);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register' | null>(null);
  const [authPrompt, setAuthPrompt] = useState<string | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);
  const [accountSettingsOpen, setAccountSettingsOpen] = useState<boolean>(false);
  const [accountSettingsTab, setAccountSettingsTab] = useState<AccountSettingsTab>('email');
  const [editProfileOpen, setEditProfileOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [lookupTerm, setLookupTerm] = useState<string | null>(null);
  // Chương/trang đang mở trong trình đọc; Khách vẫn mở được chương đọc thử (F03.03, F05.04).
  const [readerTarget, setReaderTarget] = useState<ReaderTarget | null>(null);
  // Tăng lên khi tải ảnh hoặc tạo truyện xong để Trang Chủ/Thư viện tải lại dữ liệu.
  const [dataVersion, setDataVersion] = useState<number>(0);
  const [focusQuiz, setFocusQuiz] = useState<boolean>(false);
  const [managerState, setManagerState] = useState<{ open: boolean; seriesId: number | null }>({ open: false, seriesId: null });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  // Thông báo nhẹ khi phát âm phải dùng phương án dự phòng (F11.06, F02.03).
  useEffect(() => setSpeechNoticeListener(msg => showToast(msg)), []);

  // Đưa người dùng đã xác thực vào ứng dụng: nạp cài đặt rồi dựng hồ sơ hiển thị.
  const applySession = async (user: ApiUser) => {
    let settings: ApiSettings | null = null;
    try {
      settings = await getSettings();
    } catch {
      // Hồ sơ vẫn hiển thị được khi chưa tải được cài đặt.
    }
    setUserProfile(previous => toUserProfile(user, settings, previous));
    setIsAdmin(user.role === 'admin');
    setIsLoggedIn(true);
  };

  const resetSessionState = () => {
    setIsLoggedIn(false);
    setIsAdmin(false);
    setAccountSettingsOpen(false);
    setEditProfileOpen(false);
    setUploadModalOpen(false);
    setManagerState({ open: false, seriesId: null });
    setReaderTarget(null);
    setActiveTab('catalog'); // Trở về trang chủ khi không còn phiên
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Khôi phục phiên khi tải lại trang (F01.03).
  useEffect(() => {
    if (!hasStoredSession()) return;
    let cancelled = false;
    getMe()
      .then(user => (cancelled ? undefined : applySession(user)))
      .catch(() => undefined) // Phiên hỏng: client đã dọn mã, người dùng ở trạng thái chưa đăng nhập.
      .finally(() => {
        if (!cancelled) setAuthReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Phiên bị thu hồi hoặc hết hạn ở máy chủ (đăng xuất thiết bị khác, bị khóa...).
  useEffect(() => {
    const onExpired = () => {
      resetSessionState();
      setAuthPrompt('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.');
      setAuthModalMode('login');
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  // Only Trang Chủ and Bảng Vàng Danh Dự are publicly viewable without authentication
  const isPublicTab = (tab: NavigationTab) => tab === 'catalog' || tab === 'leaderboard';

  const handleNavigate = (tab: NavigationTab) => {
    if (tab === 'admin' && !isAdmin) {
      showToast(isLoggedIn ? 'Chỉ quản trị viên mới có quyền truy cập.' : 'Vui lòng đăng nhập bằng tài khoản quản trị viên.');
      if (!isLoggedIn) setAuthModalMode('login');
      return;
    }
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

  // Mở trình đọc đúng chương/trang. Khách được mở: máy chủ chỉ cho đọc chương đọc thử và báo lỗi nếu không được phép.
  const handleOpenReader = (target: ReaderTarget) => {
    setReaderTarget(target);
    setActiveTab('reader');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleRequireLogin = (message: string) => {
    setAuthPrompt(message);
    setAuthModalMode('login');
  };

  // Trình đọc là trang công khai khi đã có chương được chọn (đọc thử); các trang khác theo quy tắc cũ.
  const canViewTab = (tab: NavigationTab) => isLoggedIn || isPublicTab(tab) || (tab === 'reader' && readerTarget !== null);

  const handleOpenUpload = () => {
    if (!isLoggedIn) {
      setAuthPrompt('Vui lòng đăng nhập để tải ảnh manhua và sử dụng OCR dịch tự động!');
      setAuthModalMode('login');
      showToast('Vui lòng đăng nhập để tải ảnh dịch.');
      return;
    }
    setUploadModalOpen(true);
  };

  // Máy chủ chỉ mới nhận ảnh và xếp hàng xử lý; trạng thái thật hiện trong cửa sổ tải lên và Thư viện.
  const handleUploaded = (pages: ApiPage[]) => {
    setDataVersion(value => value + 1);
    showToast(
      pages.length === 1
        ? 'Đã tải ảnh lên, đang xếp hàng chờ xử lý.'
        : `Đã tải ${pages.length} ảnh lên, đang xếp hàng chờ xử lý.`
    );
  };

  const apiErrorMessage = (err: unknown) => (err instanceof ApiError ? err.message : 'Có lỗi xảy ra, vui lòng thử lại.');

  const handleUpdateProfileVisibility = async (setting: 'showEmail' | 'showJoinDate', visible: boolean) => {
    try {
      const user = await updateMe(setting === 'showEmail' ? { show_email: visible } : { show_join_date: visible });
      setUserProfile(prev => ({ ...prev, showEmail: user.show_email, showJoinDate: user.show_join_date }));
      showToast(`${setting === 'showEmail' ? 'Email' : 'Ngày tham gia'} đã được ${visible ? 'hiển thị' : 'ẩn'} trên hồ sơ.`);
    } catch (err) {
      showToast(apiErrorMessage(err));
    }
  };

  const handleFocusQuizHandled = useCallback(() => setFocusQuiz(false), []);

  const openAccountSettings = (tab: AccountSettingsTab) => {
    setAccountSettingsTab(tab);
    setAccountSettingsOpen(true);
  };

  // Cài đặt học tập đã lưu: cập nhật hồ sơ hiển thị và cho Thư viện tải lại mục tiêu tuần (F02.01-F02.02).
  const handleSettingsSaved = (settings: ApiSettings) => {
    setUserProfile(prev => ({
      ...prev,
      hskLevel: settings.hsk_level ? `Cấp độ HSK ${settings.hsk_level}` : 'Chưa chọn trình độ HSK',
      weeklyProgress: { ...prev.weeklyProgress, target: settings.weekly_page_goal ?? prev.weeklyProgress.target }
    }));
    setDataVersion(version => version + 1);
  };

  // Tải avatar lên máy chủ (F01.10); lỗi được ném lại để hộp thoại hiển thị tại chỗ.
  const handleUploadAvatar = async (file: File) => {
    const user = await uploadAvatar(file);
    setUserProfile(prev => ({ ...prev, avatarUrl: user.avatar_url }));
  };

  // Gỡ avatar đã tải lên (F01.10): Navbar và hồ sơ dùng chung avatarUrl nên tự quay về ảnh mặc định.
  const handleRemoveAvatar = async () => {
    const user = await removeAvatar();
    setUserProfile(prev => ({ ...prev, avatarUrl: user.avatar_url }));
  };

  // Tên hiển thị, tên tiếng Trung và avatar tải lên được lưu ở máy chủ; huy hiệu và avatar gợi ý chỉ giữ trong phiên này.
  const handleSaveProfile = async (updated: Partial<UserProfileData>): Promise<boolean> => {
    try {
      const user = await updateMe({ display_name: updated.name ?? userProfile.name, chinese_name: updated.chineseName ?? '' });
      setUserProfile(prev => ({
        ...prev,
        ...updated,
        name: user.display_name,
        chineseName: user.chinese_name ?? ''
      }));
      return true;
    } catch (err) {
      showToast(apiErrorMessage(err));
      return false;
    }
  };

  const handleAuthSuccess = async (user: ApiUser) => {
    await applySession(user);
    setAuthModalMode(null);
    setAuthPrompt(null);
    showToast('Đăng nhập thành công! Chào mừng bạn đến với Yinghua.');
  };

  // Logout handler: Immediately redirects to Trang Chủ (catalog)
  const handleLogout = async () => {
    setAuthModalMode(null);
    setAuthPrompt(null);
    resetSessionState();
    await logout();
    showToast('Bạn đã đăng xuất thành công và trở về Trang Chủ.');
  };

  const handleLogoutAll = async () => {
    try {
      const devices = await logoutAllDevices();
      resetSessionState();
      showToast(`Đã đăng xuất khỏi ${devices} thiết bị.`);
    } catch (err) {
      showToast(apiErrorMessage(err));
    }
  };

  if (!authReady) {
    return <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center text-sm text-slate-500">Đang tải...</div>;
  }

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
        isAdmin={isAdmin}
        onToggleLogin={isLoggedIn ? handleLogout : () => setAuthModalMode('login')}
        onLookupWord={setLookupTerm}
        userAvatar={userProfile.avatar}
        userAvatarUrl={userProfile.avatarUrl}
      />}

      {/* Main Screen Content */}
      <main className={`flex-1 w-full ${activeTab === 'admin' ? '' : 'pt-20'}`}>
        {/* Route Guard Fallback: If not logged in and not on public tab */}
        {activeTab === 'admin' && isAdmin ? (
          <AdminDashboard onOpenLearnerView={() => handleNavigate('catalog')} currentUserEmail={userProfile.email} />
        ) : activeTab === 'admin' ? (
          <div className="mx-auto max-w-xl px-4 py-20 text-center text-slate-600">Bạn không có quyền truy cập khu vực quản trị.</div>
        ) : !canViewTab(activeTab) ? (
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
                isLoggedIn={isLoggedIn}
                onOpenReader={handleOpenReader}
                onRequireLogin={handleRequireLogin}
                onNavigateToFlashcards={() => handleNavigate('flashcards')}
                onLookupWord={setLookupTerm}
                showToast={showToast}
                refreshKey={dataVersion}
              />
            )}

            {activeTab === 'leaderboard' && (
              <LeaderboardPage
                onStartQuiz={() => {
                  setFocusQuiz(true);
                  handleNavigate('flashcards');
                }}
              />
            )}

            {activeTab === 'reader' && (
              <ComicReader
                target={readerTarget}
                isLoggedIn={isLoggedIn}
                onOpenUpload={handleOpenUpload}
                onBrowse={() => handleNavigate('catalog')}
                onOpenReader={handleOpenReader}
                onRequireLogin={handleRequireLogin}
                onLookupWord={setLookupTerm}
                onOpenLearningSettings={() => openAccountSettings('learning')}
              />
            )}

            {activeTab === 'library' && (
              <LibraryPage
                isAdmin={isAdmin}
                refreshKey={dataVersion}
                onOpenUpload={handleOpenUpload}
                onOpenReader={handleOpenReader}
                onOpenManager={(seriesId) => setManagerState({ open: true, seriesId })}
                onNavigateToFlashcards={() => handleNavigate('flashcards')}
                onOpenLearningSettings={() => openAccountSettings('learning')}
                showToast={showToast}
              />
            )}

            {activeTab === 'flashcards' && (
              <FlashcardsPage
                onNavigateToReader={() => handleNavigate('reader')}
                onOpenReader={handleOpenReader}
                showToast={showToast}
                focusQuiz={focusQuiz}
                onFocusQuizHandled={handleFocusQuizHandled}
              />
            )}

            {activeTab === 'profile' && (
              <ProfilePage
                onNavigateToReader={() => handleNavigate('reader')}
                onNavigateToFlashcards={() => handleNavigate('flashcards')}
                userProfile={userProfile}
                onOpenAccountSettings={() => openAccountSettings('email')}
                onOpenEditProfile={() => setEditProfileOpen(true)}
                onNavigateToCatalog={() => handleNavigate('catalog')}
                onOpenReader={handleOpenReader}
                onRequireLogin={handleRequireLogin}
                showToast={showToast}
                onOpenLearningSettings={() => openAccountSettings('learning')}
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

      {/* Tra từ điển (M06) */}
      <WordLookupModal
        term={lookupTerm}
        isLoggedIn={isLoggedIn}
        onClose={() => setLookupTerm(null)}
        onRequireLogin={() => {
          setAuthPrompt('Vui lòng đăng nhập để xem đầy đủ nghĩa, ví dụ và phân rã chữ Hán!');
          setAuthModalMode('login');
        }}
        showToast={showToast}
      />

      {/* Auth Modals (Login & Register with Learning Goal Selection) */}
      <AuthModals
        mode={authModalMode}
        promptMessage={authPrompt}
        onClose={() => {
          setAuthModalMode(null);
          setAuthPrompt(null);
        }}
        onSuccess={handleAuthSuccess}
        onSwitchMode={(newMode) => setAuthModalMode(newMode)}
      />

      {/* Upload Manhua OCR Modal */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploaded={handleUploaded}
        onOpenReader={handleOpenReader}
        onOpenManager={() => setManagerState({ open: true, seriesId: null })}
      />

      {/* Tạo truyện riêng, thêm chương, tải trang */}
      <SeriesManagerModal
        isOpen={managerState.open}
        seriesId={managerState.seriesId}
        isAdmin={isAdmin}
        onClose={() => setManagerState({ open: false, seriesId: null })}
        onChanged={() => setDataVersion(value => value + 1)}
        showToast={showToast}
      />

      {/* Account Settings Modal (Đổi mật khẩu, Đổi mail, Đăng xuất) */}
      <AccountSettingsModal
        isOpen={accountSettingsOpen}
        onClose={() => setAccountSettingsOpen(false)}
        currentEmail={userProfile.email}
        showEmail={userProfile.showEmail !== false}
        showJoinDate={userProfile.showJoinDate !== false}
        onUpdateVisibility={handleUpdateProfileVisibility}
        onLogout={handleLogout}
        onLogoutAll={handleLogoutAll}
        initialTab={accountSettingsTab}
        onSettingsSaved={handleSettingsSaved}
        showToast={showToast}
      />

      {/* Edit Profile Modal (Đổi tên, Đổi avatar, Đổi thẻ thành tựu) */}
      <EditProfileModal
        isOpen={editProfileOpen}
        onClose={() => setEditProfileOpen(false)}
        userProfile={userProfile}
        onSaveProfile={handleSaveProfile}
        onUploadAvatar={handleUploadAvatar}
        onRemoveAvatar={handleRemoveAvatar}
        showToast={showToast}
      />

      {/* Đặt lại mật khẩu từ liên kết trong email (F01.06) */}
      {resetToken && (
        <ResetPasswordModal
          token={resetToken}
          onClose={() => {
            clearResetTokenFromUrl();
            setResetToken(null);
          }}
          onDone={() => {
            clearResetTokenFromUrl();
            setResetToken(null);
            setAuthPrompt(null);
            setAuthModalMode('login');
            showToast('Đặt lại mật khẩu thành công! Vui lòng đăng nhập bằng mật khẩu mới.');
          }}
        />
      )}

      {/* Unified Footer */}
      {activeTab !== 'admin' && <Footer
        setActiveTab={handleNavigate}
        isLoggedIn={isLoggedIn}
      />}

    </div>
  );
}
