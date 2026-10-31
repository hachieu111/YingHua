import React, { useEffect, useState } from 'react';
import { changePassword } from '../api/auth';
import { ApiError } from '../api/client';
import { ApiSettings } from '../api/settings';
import { useTour } from '../tour/TourProvider';
import { LeaderboardPrivacyToggle } from './LeaderboardPrivacyToggle';
import { LearningSettingsPanel } from './LearningSettingsPanel';

const MIN_PASSWORD_LENGTH = 8;

export type AccountSettingsTab = 'email' | 'password' | 'privacy' | 'learning' | 'logout';

interface AccountSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentEmail: string;
  showEmail: boolean;
  showJoinDate: boolean;
  onUpdateVisibility: (setting: 'showEmail' | 'showJoinDate', visible: boolean) => void;
  onLogout: () => void;
  onLogoutAll: () => Promise<void>;
  /** Mục mở sẵn khi hiển thị (vd. 'learning' khi bấm từ Thư viện). */
  initialTab?: AccountSettingsTab;
  onSettingsSaved: (settings: ApiSettings) => void;
  showToast: (msg: string) => void;
}

export const AccountSettingsModal: React.FC<AccountSettingsModalProps> = ({
  isOpen,
  onClose,
  currentEmail,
  showEmail,
  showJoinDate,
  onUpdateVisibility,
  onLogout,
  onLogoutAll,
  initialTab = 'email',
  onSettingsSaved,
  showToast
}) => {
  const [activeTab, setActiveTab] = useState<AccountSettingsTab>(initialTab);
  const { replay } = useTour();

  // Mỗi lần mở lại thì về đúng mục được yêu cầu.
  useEffect(() => {
    if (isOpen) setActiveTab(initialTab);
  }, [isOpen, initialTab]);

  // Change Email state
  const [newEmail, setNewEmail] = useState<string>('');
  const [emailPasswordConfirm, setEmailPasswordConfirm] = useState<string>('');

  // Change Password state
  const [oldPassword, setOldPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showPasswords, setShowPasswords] = useState<boolean>(false);

  if (!isOpen) return null;

  // Password strength calculation
  const getPasswordStrength = () => {
    if (!newPassword || newPassword.length === 0) return { label: 'Chưa nhập', level: 0, color: 'text-slate-400 dark:text-slate-500' };
    if (newPassword.length < 6) return { label: 'Yếu', level: 1, color: 'text-rose-600 dark:text-rose-400' };
    if (newPassword.length < 10) return { label: 'Trung bình', level: 2, color: 'text-amber-600 dark:text-amber-400' };
    return { label: 'Rất mạnh', level: 3, color: 'text-[#a43073] dark:text-pink-400 font-bold' };
  };

  const strength = getPasswordStrength();

  // SRS chưa có chức năng đổi email (email là định danh đăng nhập), nên không giả vờ đổi thành công.
  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    showToast('Chức năng đổi email chưa được hỗ trợ. Vui lòng liên hệ quản trị viên nếu cần đổi.');
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!oldPassword) {
      showToast('Vui lòng nhập mật khẩu hiện tại!');
      return;
    }
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      showToast(`Mật khẩu mới phải có tối thiểu ${MIN_PASSWORD_LENGTH} ký tự!`);
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast('Xác nhận mật khẩu mới không khớp!');
      return;
    }
    try {
      await changePassword(oldPassword, newPassword);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Không thể đổi mật khẩu, vui lòng thử lại.');
      return;
    }
    showToast('Đổi mật khẩu thành công! Các thiết bị khác đã bị đăng xuất.');
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white dark:bg-[#0f172a] w-full max-w-lg rounded-3xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 overflow-hidden flex flex-col">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 dark:border-slate-700 bg-gradient-to-r from-pink-50/70 via-white to-blue-50/40 dark:from-pink-900/20 dark:via-[#0f172a] dark:to-blue-900/20">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center text-[#a43073] dark:text-pink-400 text-sm font-bold">
              <span className="material-symbols-outlined text-[20px]">tune</span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800 dark:text-white">Cài đặt tài khoản</h3>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                Quản lý bảo mật, thư điện tử và phiên đăng nhập
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-300 flex items-center justify-center transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Tab Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-5 items-center gap-2 p-3 bg-[#eff4ff] dark:bg-slate-800 border-b border-blue-100 dark:border-slate-700 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('email')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'email'
                ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs font-bold'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">mail</span>
            <span>Đổi Email</span>
          </button>

          <button
            onClick={() => setActiveTab('password')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'password'
                ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs font-bold'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">lock_reset</span>
            <span>Đổi Mật Khẩu</span>
          </button>

          <button
            onClick={() => setActiveTab('privacy')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'privacy'
                ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs font-bold'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">visibility</span>
            <span>Riêng tư</span>
          </button>

          <button
            onClick={() => setActiveTab('learning')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'learning'
                ? 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs font-bold'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">school</span>
            <span>Học tập</span>
          </button>

          <button
            onClick={() => setActiveTab('logout')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'logout'
                ? 'bg-rose-500 text-white shadow-xs font-bold'
                : 'text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">logout</span>
            <span>Đăng Xuất</span>
          </button>
        </div>

        {/* Tab Body */}
        <div className="p-6">
          
          {/* TAB: CÀI ĐẶT HỌC TẬP (F02.01-F02.03) */}
          {activeTab === 'learning' && <LearningSettingsPanel onSaved={onSettingsSaved} showToast={showToast} />}

          {/* TAB 1: CHANGE EMAIL */}
          {activeTab === 'email' && (
            <form onSubmit={handleEmailSubmit} className="flex flex-col gap-4">
              <div className="p-3 rounded-2xl bg-blue-50/70 dark:bg-blue-900/20 border border-blue-100 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase font-bold block">
                    Email hiện tại
                  </span>
                  <span className="font-bold text-slate-800 dark:text-white text-sm">{currentEmail}</span>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-400 text-[10px] font-bold">
                  Đã xác thực
                </span>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                  Địa chỉ Email mới
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                    alternate_email
                  </span>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="ví dụ: hienvu.new@yinghua.vn"
                    className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                  Nhập mật khẩu hiện tại để xác nhận
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                    key
                  </span>
                  <input
                    type="password"
                    value={emailPasswordConfirm}
                    onChange={(e) => setEmailPasswordConfirm(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-full text-xs font-semibold text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">check</span>
                  <span>Cập nhật Email</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 2: CHANGE PASSWORD */}
          {activeTab === 'password' && (
            <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-3.5">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                  Mật khẩu hiện tại
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                    lock
                  </span>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="Mật khẩu đang sử dụng"
                    className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-10 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswords(!showPasswords)}
                    className="absolute right-3.5 text-slate-400 dark:text-slate-500 hover:text-[#a43073] dark:hover:text-pink-400"
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      {showPasswords ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                  Mật khẩu mới
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                    lock_open
                  </span>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder={`Tối thiểu ${MIN_PASSWORD_LENGTH} ký tự`}
                    className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>

                {/* Password Strength Meter */}
                <div className="flex flex-col gap-1 mt-1">
                  <div className="flex gap-1.5 h-1.5 w-full">
                    <div className={`h-full flex-1 rounded-full transition-colors ${
                      strength.level >= 1 ? (strength.level === 1 ? 'bg-rose-500' : 'bg-amber-400') : 'bg-slate-200 dark:bg-slate-700'
                    }`}></div>
                    <div className={`h-full flex-1 rounded-full transition-colors ${
                      strength.level >= 2 ? (strength.level === 2 ? 'bg-amber-400' : 'bg-[#a43073]') : 'bg-slate-200 dark:bg-slate-700'
                    }`}></div>
                    <div className={`h-full flex-1 rounded-full transition-colors ${
                      strength.level >= 3 ? 'bg-[#a43073]' : 'bg-slate-200 dark:bg-slate-700'
                    }`}></div>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 dark:text-slate-400">
                    <span>Độ bảo mật:</span>
                    <span className={strength.color}>{strength.label}</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                  Xác nhận mật khẩu mới
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                    lock_reset
                  </span>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Nhập lại mật khẩu mới"
                    className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-full text-xs font-semibold text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">save</span>
                  <span>Đổi Mật Khẩu</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: PROFILE VISIBILITY */}
          {activeTab === 'privacy' && (
            <div className="flex flex-col gap-4">
              <div>
                <h4 className="text-sm font-bold text-slate-800 dark:text-white">Thông tin hiển thị trên hồ sơ</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Chọn thông tin bạn muốn người khác nhìn thấy trên trang cá nhân.</p>
              </div>

              {([
                { key: 'showEmail', label: 'Địa chỉ email', detail: currentEmail, visible: showEmail, icon: 'mail' },
                { key: 'showJoinDate', label: 'Ngày tham gia', detail: 'Ngày bạn bắt đầu sử dụng Yinghua', visible: showJoinDate, icon: 'calendar_today' }
              ] as const).map(({ key, label, detail, visible, icon }) => (
                <div key={key} className="flex items-center justify-between gap-4 p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-900/30 text-[#0060ac] dark:text-blue-300 flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-[18px]">{icon}</span>
                    </span>
                    <span className="min-w-0">
                      <span className="block text-xs font-bold text-slate-800 dark:text-white">{label}</span>
                      <span className="block text-[11px] text-slate-500 dark:text-slate-400 truncate">{detail}</span>
                    </span>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={visible}
                    aria-label={`${visible ? 'Ẩn' : 'Hiện'} ${label}`}
                    onClick={() => onUpdateVisibility(key, !visible)}
                    className={`relative w-11 h-6 rounded-full transition-colors shrink-0 ${visible ? 'bg-[#0060ac]' : 'bg-slate-300 dark:bg-slate-600'}`}
                  >
                    <span className={`absolute left-1 top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${visible ? 'translate-x-5' : 'translate-x-0'} dark:bg-slate-800`} />
                  </button>
                </div>
              ))}
              <LeaderboardPrivacyToggle showToast={showToast} />
              <p className="text-[11px] text-slate-400 dark:text-slate-500">Thay đổi được lưu tự động và áp dụng ngay trên hồ sơ của bạn.</p>
            </div>
          )}

          {/* TAB 4: LOGOUT */}
          {activeTab === 'logout' && (
            <div className="flex flex-col items-center text-center gap-4 py-2">
              <div className="w-16 h-16 rounded-full bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 flex items-center justify-center text-2xl shadow-inner">
                <span className="material-symbols-outlined text-[32px]">logout</span>
              </div>

              <div>
                <h4 className="text-base font-bold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">
                  Bạn có chắc chắn muốn đăng xuất?
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mt-1 leading-relaxed">
                  Toàn bộ tiến độ đọc truyện, từ vựng tích lũy và chuỗi ngày học của bạn đã được sao lưu an toàn trên hệ thống đám mây.
                </p>
              </div>

              <div className="flex items-center gap-3 w-full pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 py-2.5 rounded-full text-xs font-bold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                >
                  Ở lại học tiếp
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onLogout();
                    onClose();
                  }}
                  className="flex-1 py-2.5 rounded-full text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 shadow-md transition-all flex items-center justify-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">logout</span>
                  <span>Đăng xuất ngay</span>
                </button>
              </div>

              <button
                type="button"
                onClick={async () => {
                  await onLogoutAll();
                  onClose();
                }}
                className="text-xs font-semibold text-rose-600 dark:text-rose-400 hover:underline"
              >
                Đăng xuất khỏi mọi thiết bị
              </button>
            </div>
          )}

        </div>

        <div className="flex justify-center border-t border-pink-100 dark:border-slate-700 px-6 py-3">
          <button
            type="button"
            onClick={() => {
              onClose();
              replay();
            }}
            className="inline-flex items-center gap-1 text-xs font-semibold text-[#a43073] dark:text-pink-400 hover:underline"
          >
            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">help</span>
            Xem lại hướng dẫn
          </button>
        </div>

      </div>
    </div>
  );
};
