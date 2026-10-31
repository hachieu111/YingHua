import React, { useEffect, useState } from 'react';
import { errorMessage } from '../api/client';
import { listAvatarPresets } from '../api/auth';
import { DEFAULT_AVATAR_PRESET, PRESET_AVATARS } from '../data/avatarPresets';
import { validateImageFile } from '../api/library';
import { ConfirmDialog } from './ConfirmDialog';
import { ProfileAvatar } from './ProfileAvatar';
import { UserProfileData } from '../types';
import { BadgePicker } from './AchievementViews';
import { BadgeChip } from './BadgeChip';
import { useRewards } from '../utils/useRewards';

interface EditProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  userProfile: UserProfileData;
  /** Trả true khi máy chủ đã lưu tên/tên Hán thành công. */
  onSaveProfile: (updated: Partial<UserProfileData>) => Promise<boolean>;
  /** Tải avatar lên máy chủ (F01.10); ném lỗi nếu thất bại. */
  onUploadAvatar: (file: File) => Promise<void>;
  /** Gỡ avatar đã tải lên (F01.10); ném lỗi nếu thất bại. */
  onRemoveAvatar: () => Promise<void>;
  /** Lưu ảnh đại diện có sẵn lên máy chủ (F01.10); ném lỗi nếu thất bại. */
  onSetAvatarPreset: (code: string) => Promise<void>;
  showToast: (msg: string) => void;
}

export const EditProfileModal: React.FC<EditProfileModalProps> = ({
  isOpen,
  onClose,
  userProfile,
  onSaveProfile,
  onUploadAvatar,
  onRemoveAvatar,
  onSetAvatarPreset,
  showToast
}) => {
  const [name, setName] = useState<string>(userProfile?.name || '');
  const [chineseName, setChineseName] = useState<string>(userProfile?.chineseName || '');
  const { me } = useRewards();
  // Mã avatar có sẵn được chọn và ảnh tự tải lên đang chờ lưu lên máy chủ.
  const [presetId, setPresetId] = useState<string | null>(null);
  // Mã máy chủ chấp nhận; null = chưa biết (hiện đủ bộ ảnh).
  const [serverPresetCodes, setServerPresetCodes] = useState<string[] | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingPreview, setPendingPreview] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<boolean>(false);
  const [removing, setRemoving] = useState<boolean>(false);

  // Mỗi lần mở: nạp lại giá trị hiện tại của hồ sơ, bỏ lựa chọn dở dang của lần trước.
  useEffect(() => {
    if (!isOpen) return;
    setName(userProfile?.name || '');
    setChineseName(userProfile?.chineseName || '');
    setPresetId(null);
    setPendingFile(null);
    setAvatarError(null);
    const controller = new AbortController();
    listAvatarPresets(controller.signal)
      .then(items => setServerPresetCodes(items.map(item => item.code)))
      .catch(() => setServerPresetCodes(null));
    return () => controller.abort();
    // Chỉ nạp lại khi mở hộp thoại, không ghi đè lúc người dùng đang gõ.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Ảnh xem trước dùng URL tạm; thu hồi khi đổi ảnh hoặc đóng hộp thoại.
  useEffect(() => {
    if (!pendingFile) {
      setPendingPreview(null);
      return;
    }
    const url = URL.createObjectURL(pendingFile);
    setPendingPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingFile]);

  if (!isOpen) return null;

  const visiblePresets = serverPresetCodes ? PRESET_AVATARS.filter(av => serverPresetCodes.includes(av.id)) : PRESET_AVATARS;
  const presetPreviewUrl = presetId ? PRESET_AVATARS.find(av => av.id === presetId)?.url : undefined;
  const selectedPresetId = presetId ?? (userProfile.avatarUrl ? null : userProfile.avatarPreset ?? DEFAULT_AVATAR_PRESET);

  const handleRemoveAvatar = async () => {
    setRemoving(true);
    setAvatarError(null);
    try {
      await onRemoveAvatar();
      setPendingFile(null);
      setConfirmRemove(false);
      showToast('Đã gỡ ảnh đại diện.');
    } catch (err) {
      setConfirmRemove(false);
      setAvatarError(errorMessage(err));
    } finally {
      setRemoving(false);
    }
  };

  const handleCustomAvatarPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const problem = validateImageFile(file);
    if (problem) {
      setAvatarError(problem);
      return;
    }
    setAvatarError(null);
    setPresetId(null);
    setPendingFile(file);
  };

  const handlePresetPick = (id: string) => {
    setPendingFile(null);
    setAvatarError(null);
    setPresetId(id);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      showToast('Tên hiển thị không được để trống!');
      return;
    }
    setSaving(true);
    setAvatarError(null);
    try {
      if (pendingFile) {
        try {
          await onUploadAvatar(pendingFile);
        } catch (err) {
          setAvatarError(errorMessage(err));
          return;
        }
      }
      if (presetId) {
        try {
          await onSetAvatarPreset(presetId);
        } catch (err) {
          setAvatarError(errorMessage(err));
          return;
        }
      }
      const saved = await onSaveProfile({
        name: name.trim(),
        chineseName: chineseName.trim()
      });
      if (!saved) return;
      showToast('Cập nhật hồ sơ cá nhân thành công!');
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white dark:bg-[#0f172a] w-full max-w-xl rounded-3xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 overflow-hidden flex flex-col my-auto max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 dark:border-slate-700 bg-gradient-to-r from-pink-50/70 via-white to-pink-50/40 dark:from-pink-900/20 dark:via-[#0f172a] dark:to-pink-900/10 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center text-[#a43073] dark:text-pink-400 text-sm font-bold">
              <span className="material-symbols-outlined text-[20px]">edit_note</span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800 dark:text-white">Chỉnh sửa hồ sơ</h3>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                Cập nhật tên, ảnh đại diện và thẻ danh hiệu đang hiển thị
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

        {/* Scrollable Form Body */}
        <form onSubmit={handleSave} className="p-6 overflow-y-auto custom-scrollbar flex flex-col gap-6">
          
          {/* SECTION 1: AVATAR SELECTION */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-[#a43073] dark:text-pink-400">account_circle</span>
              <span>1. Ảnh đại diện (Avatar)</span>
            </span>

            {/* Current Selected Avatar Preview & Upload */}
            <div className="flex items-center gap-4 p-3.5 rounded-2xl bg-[#eff4ff] dark:bg-slate-800 border border-blue-100 dark:border-slate-700">
              <div className="relative shrink-0">
                {pendingPreview || presetPreviewUrl ? (
                  <img
                    src={pendingPreview ?? presetPreviewUrl ?? ''}
                    alt="Avatar Preview"
                    className="w-16 h-16 rounded-full object-cover ring-4 ring-pink-300 dark:ring-pink-900/60 shadow-md dark:shadow-none bg-white dark:bg-[#0f172a]"
                  />
                ) : (
                  <ProfileAvatar
                    serverUrl={userProfile.avatarUrl}
                    fallbackSrc={userProfile.avatar}
                    alt="Avatar Preview"
                    className="w-16 h-16 rounded-full object-cover ring-4 ring-pink-300 dark:ring-pink-900/60 shadow-md dark:shadow-none bg-white dark:bg-[#0f172a]"
                  />
                )}
                <span className="absolute -bottom-1 -right-1 w-5 h-5 bg-[#a43073] text-white rounded-full flex items-center justify-center text-[10px]">
                  ✓
                </span>
              </div>

              <div className="flex flex-col gap-1 flex-1">
                <span className="text-xs font-bold text-slate-800 dark:text-white">Ảnh đang chọn</span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400">
                  Tải ảnh JPG, PNG hoặc WebP (tối đa 10 MB) để lưu lâu dài, hoặc chọn nhân vật gợi ý bên dưới (được lưu vào tài khoản)
                </span>
                {pendingFile && (
                  <span className="text-[11px] text-[#a43073] dark:text-pink-400 font-semibold truncate">Ảnh sẽ được tải lên khi bạn bấm “Lưu thay đổi hồ sơ”: {pendingFile.name}</span>
                )}
                {avatarError && (
                  <span className="text-[11px] text-red-600 dark:text-red-400 font-semibold" role="alert">{avatarError}</span>
                )}
                
                {/* File input button */}
                <label className="mt-1 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-[#1e293b] hover:bg-pink-50 dark:hover:bg-slate-700 text-[#a43073] dark:text-pink-400 border border-pink-200 dark:border-pink-900/40 text-xs font-semibold cursor-pointer w-fit shadow-xs dark:shadow-none transition-colors">
                  <span className="material-symbols-outlined text-[16px]">upload</span>
                  <span>Tải ảnh từ máy tính</span>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleCustomAvatarPick}
                    className="hidden"
                  />
                </label>
                {userProfile.avatarUrl && (
                  <button
                    type="button"
                    onClick={() => setConfirmRemove(true)}
                    disabled={removing || saving}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-[#1e293b] hover:bg-rose-50 dark:hover:bg-rose-900/20 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50 text-xs font-semibold w-fit shadow-xs dark:shadow-none transition-colors disabled:opacity-60"
                  >
                    <span className="material-symbols-outlined text-[16px]">delete</span>
                    <span>Gỡ ảnh đại diện</span>
                  </button>
                )}
              </div>
            </div>

            {confirmRemove && (
              <ConfirmDialog
                title="Gỡ ảnh đại diện?"
                message="Ảnh bạn đã tải lên sẽ bị xóa khỏi máy chủ và hồ sơ quay về ảnh mặc định."
                confirmLabel="Gỡ ảnh"
                busy={removing}
                onConfirm={() => void handleRemoveAvatar()}
                onCancel={() => setConfirmRemove(false)}
              />
            )}

            {/* Avatar Preset Grid */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                Gợi ý avatar manhua & biểu trưng:
              </span>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2.5">
                {visiblePresets.map((av) => {
                  const isSelected = !pendingFile && selectedPresetId === av.id;
                  return (
                    <button
                      type="button"
                      key={av.id}
                      onClick={() => handlePresetPick(av.id)}
                      className={`relative rounded-2xl p-1 flex flex-col items-center gap-1 transition-all ${
                        isSelected
                          ? 'ring-2 ring-[#a43073] dark:ring-pink-400 bg-pink-50 dark:bg-pink-900/20 scale-105'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-100 dark:border-slate-700'
                      }`}
                    >
                      <img
                        src={av.url}
                        alt={av.name}
                        className="w-12 h-12 rounded-full object-cover shadow-xs dark:shadow-none bg-white dark:bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-700 dark:text-slate-200 font-medium truncate max-w-[70px]">
                        {av.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* SECTION 2: NAME EDITING */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-[#0060ac] dark:text-blue-300">badge</span>
              <span>2. Tên hiển thị & Chữ Hán</span>
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  Tên hiển thị học tập
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                    person
                  </span>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Lam Hiên Vũ"
                    className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  Tên chữ Hán (nếu có)
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                    translate
                  </span>
                  <input
                    type="text"
                    value={chineseName}
                    onChange={(e) => setChineseName(e.target.value)}
                    placeholder="轩宇"
                    className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all font-['Noto_Serif_SC'] font-semibold"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 3: ACHIEVEMENT BADGE SELECTION */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px] text-amber-600 dark:text-amber-400">military_tech</span>
                <span>3. Thẻ thành tựu / Danh hiệu trang bị</span>
              </span>
              {me?.equipped_badge ? (
                <BadgeChip badge={me.equipped_badge} className="!py-0.5" />
              ) : (
                <span className="text-[11px] text-slate-400 dark:text-slate-500 font-semibold">Chưa đeo huy hiệu</span>
              )}
            </div>

            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Chọn huy hiệu đã mở khóa để hiển thị bên cạnh tên của bạn (lưu ngay khi bấm; bấm lại để tháo):
            </p>

            <BadgePicker showToast={showToast} />
          </div>

          {/* Footer Actions */}
          <div className="pt-3 border-t border-slate-100 dark:border-slate-700 flex items-center justify-end gap-3 shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-full text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 rounded-full bg-gradient-to-r from-pink-500 to-[#a43073] text-white font-bold text-xs shadow-md hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center gap-1.5 disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-[16px]">save</span>
              <span>{saving ? 'Đang lưu...' : 'Lưu thay đổi hồ sơ'}</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
