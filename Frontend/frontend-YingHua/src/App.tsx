import React, { Suspense, lazy, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from 'react-router';
import { NavigationTab, ReaderTarget, UserProfileData } from './types';
import { CURRENT_USER } from './data/mockData';
import { ApiUser, getMe, hasStoredSession, logout, logoutAllDevices, removeAvatar, setAvatarPreset, updateMe, uploadAvatar } from './api/auth';
import { ApiError, SESSION_EXPIRED_EVENT } from './api/client';
import { ApiSettings, getSettings } from './api/settings';
import { avatarFields, toUserProfile } from './api/profile';
import { ResetPasswordModal } from './components/ResetPasswordModal';
import { Navbar } from './components/Navbar';
import { StreakProvider } from './utils/useStreak';
import { RewardsProvider } from './utils/useRewards';
import { SystemStatusProvider } from './utils/useSystemStatus';
import { TourProvider } from './tour/TourProvider';
import { MaintenanceBanner } from './components/MaintenanceBanner';
import { Footer } from './components/Footer';
import { LoginRequiredPage } from './components/LoginRequiredPage';
import { NotFoundPage } from './components/NotFoundPage';
import { AuthModals } from './components/AuthModals';
import { UploadModal } from './components/UploadModal';
import { AccountSettingsModal } from './components/AccountSettingsModal';
import { EditProfileModal } from './components/EditProfileModal';
import { AccountSettingsTab } from './components/AccountSettingsModal';
import { WordLookupModal } from './components/WordLookupModal';
import { SeriesManagerModal } from './components/SeriesManagerModal';
import { ApiPage } from './api/library';
import { setSpeechNoticeListener } from './utils/speech';
import { useDocumentTitle } from './utils/useDocumentTitle';
import { BLADE_GAME_PATH, LEGACY_RADICAL_GAME_PATH, QUIZ_SECTION_PARAM, QUIZ_SECTION_VALUE, REWARD_SHOP_PATH, SAMPLE_PAGE_PATH, TAB_PATHS, readerPath, tabFromPathname } from './routes';

// Tách mã theo trang: mỗi trang lớn chỉ tải khi người dùng mở tới.
const CatalogPage = lazy(() => import('./components/CatalogPage').then(m => ({ default: m.CatalogPage })));
const LibraryPage = lazy(() => import('./components/LibraryPage').then(m => ({ default: m.LibraryPage })));
const LeaderboardPage = lazy(() => import('./components/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })));
const ProfilePage = lazy(() => import('./components/ProfilePage').then(m => ({ default: m.ProfilePage })));
const AdminDashboard = lazy(() => import('./components/AdminDashboard').then(m => ({ default: m.AdminDashboard })));
const ReaderRoute = lazy(() => import('./components/ReaderRoute').then(m => ({ default: m.ReaderRoute })));
const SamplePage = lazy(() => import('./components/SamplePage').then(m => ({ default: m.SamplePage })));
const FlashcardsRoute = lazy(() => import('./components/FlashcardsRoute').then(m => ({ default: m.FlashcardsRoute })));
const RewardShopPage = lazy(() => import('./components/RewardShopPage').then(m => ({ default: m.RewardShopPage })));
const PhiKiemPage = lazy(() => import('./components/PhiKiemPage').then(m => ({ default: m.PhiKiemPage })));

const OTHER_PAGE_TITLES: Record<string, string> = {
  [SAMPLE_PAGE_PATH]: 'Trang mẫu',
  [REWARD_SHOP_PATH]: 'Cửa hàng đổi thưởng',
  [BLADE_GAME_PATH]: 'Phi Kiếm Trảm Tự'
};

const PAGE_TITLES: Record<NavigationTab, string> = {
  catalog: 'Trang chủ',
  reader: 'Đọc truyện',
  library: 'Thư viện',
  flashcards: 'Từ vựng',
  leaderboard: 'Bảng xếp hạng',
  profile: 'Hồ sơ',
  admin: 'Quản trị'
};

const PageFallback: React.FC = () => (
  <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-500 dark:text-slate-400">
    <span className="w-5 h-5 border-2 border-pink-300 border-t-transparent rounded-full animate-spin"></span>
    Đang tải...
  </div>
);

const RESET_TOKEN_PARAM = 'reset_token';
// Thử khôi phục phiên khi máy chủ tạm không phản hồi lúc mở trang.
const SESSION_RETRY_DELAYS_MS = [2000, 4000, 8000];

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  // Mục đang chọn suy ra từ URL; null ở trang 404.
  const activeTab = tabFromPathname(location.pathname);
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [userProfile, setUserProfile] = useState<UserProfileData>(CURRENT_USER);
  // Chờ khôi phục phiên đăng nhập đã lưu để không nhấp nháy trang "Yêu cầu đăng nhập".
  const [authReady, setAuthReady] = useState<boolean>(() => !hasStoredSession());
  const [resetToken, setResetToken] = useState<string | null>(() => searchParams.get(RESET_TOKEN_PARAM));
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register' | null>(null);
  const [authPrompt, setAuthPrompt] = useState<string | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);
  const [accountSettingsOpen, setAccountSettingsOpen] = useState<boolean>(false);
  const [accountSettingsTab, setAccountSettingsTab] = useState<AccountSettingsTab>('email');
  const [editProfileOpen, setEditProfileOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [lookupTerm, setLookupTerm] = useState<string | null>(null);
  // Đường dẫn trình đọc gần nhất để mục "Đọc truyện" quay lại đúng chương; Khách vẫn mở được chương đọc thử (F03.03, F05.04).
  const [lastReaderPath, setLastReaderPath] = useState<string | null>(null);
  // Tăng lên khi tải ảnh hoặc tạo truyện xong để Trang Chủ/Thư viện tải lại dữ liệu.
  const [dataVersion, setDataVersion] = useState<number>(0);
  const [managerState, setManagerState] = useState<{ open: boolean; seriesId: number | null }>({ open: false, seriesId: null });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  useDocumentTitle(activeTab ? PAGE_TITLES[activeTab] : (OTHER_PAGE_TITLES[location.pathname] ?? 'Không tìm thấy trang'));

  // Sang trang khác thì cuộn về đầu trang.
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [location.pathname]);

  // Mã đặt lại mật khẩu đã được giữ trong state: xóa khỏi thanh địa chỉ ngay để không rò rỉ qua lịch sử/Referer (F01.06).
  useEffect(() => {
    if (!searchParams.has(RESET_TOKEN_PARAM)) return;
    setSearchParams(
      previous => {
        const next = new URLSearchParams(previous);
        next.delete(RESET_TOKEN_PARAM);
        return next;
      },
      { replace: true }
    );
  }, [searchParams, setSearchParams]);

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
    setUserProfile(toUserProfile(user, settings));
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
    setLastReaderPath(null);
    navigate(TAB_PATHS.catalog); // Trở về trang chủ khi không còn phiên
  };

  // Khôi phục phiên khi tải lại trang (F01.03).
  useEffect(() => {
    if (!hasStoredSession()) return;
    let cancelled = false;
    let restored = false;
    let attempt = 0;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    // Máy chủ tạm không phản hồi (đang khởi động lại, mất mạng) thì mã phiên vẫn còn: thử lại thay vì để người dùng
    // ở trạng thái "chưa đăng nhập". Phiên hỏng thật (401 không làm mới được) thì client đã dọn mã, dừng thử.
    const restore = () => {
      if (cancelled || restored || !hasStoredSession()) return;
      if (retryTimer) clearTimeout(retryTimer);
      getMe()
        .then(user => {
          if (cancelled) return;
          restored = true;
          applySession(user);
        })
        .catch(err => {
          // Bảo trì (503) cũng chỉ là tạm thời: giữ phiên và thử lại, không coi là đăng xuất.
          if (cancelled || !(err instanceof ApiError) || (err.code !== 'NETWORK_ERROR' && err.code !== 'MAINTENANCE_MODE')) return;
          if (attempt < SESSION_RETRY_DELAYS_MS.length) retryTimer = setTimeout(restore, SESSION_RETRY_DELAYS_MS[attempt++]);
        })
        .finally(() => {
          if (!cancelled) setAuthReady(true);
        });
    };
    const retryWhenBack = () => {
      if (document.visibilityState === 'visible') restore();
    };
    restore();
    window.addEventListener('online', restore);
    window.addEventListener('focus', retryWhenBack);
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      window.removeEventListener('online', restore);
      window.removeEventListener('focus', retryWhenBack);
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
  }, [navigate]);

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
    navigate(tab === 'reader' && lastReaderPath ? lastReaderPath : TAB_PATHS[tab]);
  };

  // Mở trình đọc đúng chương/trang. Khách được mở: máy chủ chỉ cho đọc chương đọc thử và báo lỗi nếu không được phép.
  const handleOpenReader = (target: ReaderTarget) => {
    navigate(readerPath(target));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleRequireLogin = (message: string) => {
    setAuthPrompt(message);
    setAuthModalMode('login');
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
    setUserProfile(prev => ({ ...prev, ...avatarFields(user) }));
  };

  // Chọn ảnh đại diện có sẵn (F01.10): máy chủ lưu mã, Navbar và hồ sơ đổi theo.
  const handleSetAvatarPreset = async (code: string) => {
    const user = await setAvatarPreset(code);
    setUserProfile(prev => ({ ...prev, ...avatarFields(user) }));
  };

  // Gỡ avatar đã tải lên (F01.10): Navbar và hồ sơ dùng chung avatarUrl nên tự quay về ảnh mặc định.
  const handleRemoveAvatar = async () => {
    const user = await removeAvatar();
    setUserProfile(prev => ({ ...prev, ...avatarFields(user) }));
  };

  // Tên hiển thị, tên tiếng Trung và avatar tải lên được lưu ở máy chủ; huy hiệu chỉ giữ trong phiên này.
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

  const requestLogin = (message: string) => {
    setAuthPrompt(message);
    setAuthModalMode('login');
  };

  const requestRegister = () => {
    setAuthPrompt(null);
    setAuthModalMode('register');
  };

  const loginRequiredPage = (
    <LoginRequiredPage
      onLogin={() => requestLogin('Vui lòng đăng nhập để truy cập trang này!')}
      onRegister={requestRegister}
      onGoHome={() => handleNavigate('catalog')}
    />
  );

  if (!authReady) {
    return <div className="min-h-screen bg-[#f8f9ff] dark:bg-[#020617] flex items-center justify-center text-sm text-slate-500 dark:text-slate-400">Đang tải...</div>;
  }

  return (
    <SystemStatusProvider>
    <StreakProvider isLoggedIn={isLoggedIn}>
    <RewardsProvider isLoggedIn={isLoggedIn}>
    <TourProvider isLoggedIn={isLoggedIn}>
      <MaintenanceBanner />
    <div className="min-h-screen bg-[#f8f9ff] dark:bg-[#020617] text-[#0b1c30] dark:text-slate-200 flex flex-col font-['Inter'] selection:bg-[#ffd8e7] selection:text-[#3d0026] transition-colors duration-300">
      
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

      {/* Main Screen Content: mỗi trang có URL riêng (xem src/routes.ts) */}
      <main className={`flex-1 w-full ${activeTab === 'admin' ? '' : 'pt-20'}`}>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route
              path={TAB_PATHS.catalog}
              element={
                <CatalogPage
                  isLoggedIn={isLoggedIn}
                  onOpenReader={handleOpenReader}
                  onRequireLogin={handleRequireLogin}
                  onNavigateToFlashcards={() => handleNavigate('flashcards')}
                  onLookupWord={setLookupTerm}
                  showToast={showToast}
                  refreshKey={dataVersion}
                />
              }
            />

            <Route
              path={TAB_PATHS.leaderboard}
              element={
                <LeaderboardPage
                  isLoggedIn={isLoggedIn}
                  onNavigateToReader={() => handleNavigate('reader')}
                  onNavigateToFlashcards={() => handleNavigate('flashcards')}
                  onRequireLogin={handleRequireLogin}
                  onOpenPrivacySettings={() => openAccountSettings('privacy')}
                  onStartQuiz={() => {
                    if (!isLoggedIn) {
                      handleNavigate('flashcards');
                      return;
                    }
                    navigate({ pathname: TAB_PATHS.flashcards, search: `?${QUIZ_SECTION_PARAM}=${QUIZ_SECTION_VALUE}` });
                  }}
                />
              }
            />

            {['', '/:chapterId', '/anh/:pageId'].map(suffix => (
              <Route
                key={suffix}
                path={`${TAB_PATHS.reader}${suffix}`}
                element={
                  <ReaderRoute
                    isLoggedIn={isLoggedIn}
                    onOpenUpload={handleOpenUpload}
                    onBrowse={() => handleNavigate('catalog')}
                    onOpenReader={handleOpenReader}
                    refreshKey={dataVersion}
                    onRequireLogin={handleRequireLogin}
                    onLookupWord={setLookupTerm}
                    onOpenLearningSettings={() => openAccountSettings('learning')}
                    onLogin={() => requestLogin('Vui lòng đăng nhập để truy cập trang này!')}
                    onRegister={requestRegister}
                    onGoHome={() => handleNavigate('catalog')}
                    onPathChange={setLastReaderPath}
                  />
                }
              />
            ))}

            <Route
              path={TAB_PATHS.library}
              element={
                isLoggedIn ? (
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
                ) : loginRequiredPage
              }
            />

            <Route
              path={TAB_PATHS.flashcards}
              element={
                isLoggedIn ? (
                  <FlashcardsRoute
                    onNavigateToReader={() => handleNavigate('reader')}
                    onOpenReader={handleOpenReader}
                    showToast={showToast}
                  />
                ) : loginRequiredPage
              }
            />

            <Route
              path={TAB_PATHS.profile}
              element={
                isLoggedIn ? (
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
                ) : loginRequiredPage
              }
            />

            <Route
              path={TAB_PATHS.admin}
              element={
                isAdmin ? (
                  <AdminDashboard onOpenLearnerView={() => handleNavigate('catalog')} currentUserEmail={userProfile.email} />
                ) : (
                  <div className="mx-auto max-w-xl px-4 py-20 text-center text-slate-600">Bạn không có quyền truy cập khu vực quản trị.</div>
                )
              }
            />

            <Route path={REWARD_SHOP_PATH} element={isLoggedIn ? <RewardShopPage showToast={showToast} /> : loginRequiredPage} />

            <Route path={BLADE_GAME_PATH} element={isLoggedIn ? <PhiKiemPage /> : loginRequiredPage} />

            <Route path={LEGACY_RADICAL_GAME_PATH} element={<Navigate to={BLADE_GAME_PATH} replace />} />

            <Route path={SAMPLE_PAGE_PATH} element={isLoggedIn ? <SamplePage onLookupWord={setLookupTerm} /> : loginRequiredPage} />

            <Route path="*" element={<NotFoundPage onGoHome={() => handleNavigate('catalog')} />} />
          </Routes>
        </Suspense>
      </main>

      {/* Global Toast Alert */}
      {toastMessage && (
        <div className="fixed top-24 right-6 z-50 bg-white/95 dark:bg-slate-800/95 backdrop-blur-md px-4 py-3 rounded-2xl shadow-floating dark:shadow-none border border-pink-200 dark:border-pink-900/40 text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 animate-bounce">
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
        onSetAvatarPreset={handleSetAvatarPreset}
        showToast={showToast}
      />

      {/* Đặt lại mật khẩu từ liên kết trong email (F01.06) */}
      {resetToken && (
        <ResetPasswordModal
          token={resetToken}
          onClose={() => {
            setResetToken(null);
          }}
          onDone={() => {
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
    </TourProvider>
    </RewardsProvider>
    </StreakProvider>
    </SystemStatusProvider>
  );
}
