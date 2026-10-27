import { apiRequest, loadTokens, saveTokens } from './client';

export interface ApiUser {
  id: number;
  email: string;
  display_name: string;
  chinese_name: string | null;
  avatar_url: string | null;
  /** Mã ảnh đại diện có sẵn; loại trừ với avatar_url. */
  avatar_preset: string | null;
  role: 'user' | 'admin';
  status: 'active' | 'locked';
  show_email: boolean;
  show_join_date: boolean;
  created_at: string;
}

interface AuthResponse {
  user: ApiUser;
  tokens: { access_token: string; refresh_token: string; expires_in: number; remember_me?: boolean };
}

function adopt(response: AuthResponse): ApiUser {
  saveTokens(
    { accessToken: response.tokens.access_token, refreshToken: response.tokens.refresh_token },
    response.tokens.remember_me ?? true
  );
  return response.user;
}

export const hasStoredSession = (): boolean => loadTokens() !== null;

export async function register(email: string, password: string, displayName: string): Promise<ApiUser> {
  const body: Record<string, string> = { email: email.trim(), password };
  if (displayName.trim()) body.display_name = displayName.trim();
  return adopt(await apiRequest<AuthResponse>('/auth/register', { method: 'POST', body, auth: false }));
}

export async function login(email: string, password: string, rememberMe = true): Promise<ApiUser> {
  return adopt(
    await apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: { email: email.trim(), password, remember_me: rememberMe },
      auth: false
    })
  );
}

/** Đăng xuất thiết bị hiện tại. Luôn xóa mã ở máy dù máy chủ không phản hồi. */
export async function logout(): Promise<void> {
  try {
    await apiRequest<void>('/auth/logout', { method: 'POST' });
  } catch {
    // Mã sẽ tự hết hạn ở máy chủ.
  } finally {
    saveTokens(null);
  }
}

export async function logoutAllDevices(): Promise<number> {
  const { revoked_sessions } = await apiRequest<{ revoked_sessions: number }>('/auth/logout-all', { method: 'POST' });
  saveTokens(null);
  return revoked_sessions;
}

export async function forgotPassword(email: string): Promise<string> {
  const { message } = await apiRequest<{ message: string }>('/auth/forgot-password', {
    method: 'POST',
    body: { email: email.trim() },
    auth: false
  });
  return message;
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await apiRequest<void>('/auth/reset-password', {
    method: 'POST',
    body: { token, new_password: newPassword },
    auth: false
  });
}

export const getMe = (): Promise<ApiUser> => apiRequest<ApiUser>('/account/me');

export const updateMe = (
  changes: Partial<{ display_name: string; chinese_name: string; show_email: boolean; show_join_date: boolean }>
): Promise<ApiUser> => apiRequest<ApiUser>('/account/me', { method: 'PATCH', body: changes });

/** Tải ảnh đại diện (F01.10); ảnh mới thay ảnh cũ. */
export function uploadAvatar(file: File): Promise<ApiUser> {
  const form = new FormData();
  form.append('file', file);
  return apiRequest<ApiUser>('/account/me/avatar', { method: 'POST', body: form });
}

export const changePassword = (currentPassword: string, newPassword: string): Promise<void> =>
  apiRequest<void>('/account/change-password', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword }
  });

/** Gỡ ảnh đại diện đã tải lên (F01.10); trả về hồ sơ đã cập nhật. */
export async function removeAvatar(): Promise<ApiUser> {
  await apiRequest<void>('/account/me/avatar', { method: 'DELETE' });
  return getMe();
}

export interface AvatarPreset {
  code: string;
  name: string;
}

export const listAvatarPresets = async (signal?: AbortSignal): Promise<AvatarPreset[]> =>
  (await apiRequest<{ items: AvatarPreset[] }>('/account/avatar-presets', { signal })).items;

/** Chọn ảnh đại diện có sẵn (F01.10); thay ảnh tải lên nếu có. */
export const setAvatarPreset = (preset: string): Promise<ApiUser> =>
  apiRequest<ApiUser>('/account/me/avatar-preset', { method: 'PUT', body: { preset } });
