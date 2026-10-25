import { apiRequest } from './client';

export interface AdminUser {
  id: number;
  email: string;
  display_name: string;
  role: 'user' | 'admin';
  status: 'active' | 'locked';
  locked_reason: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface AdminUserPage {
  items: AdminUser[];
  total: number;
  page: number;
  size: number;
}

export const listUsers = (params: { q?: string; page?: number; size?: number }): Promise<AdminUserPage> => {
  const query = new URLSearchParams();
  if (params.q?.trim()) query.set('q', params.q.trim());
  query.set('page', String(params.page ?? 1));
  query.set('size', String(params.size ?? 20));
  return apiRequest<AdminUserPage>(`/admin/users?${query.toString()}`);
};

export const changeUserRole = (userId: number, role: 'user' | 'admin'): Promise<AdminUser> =>
  apiRequest<AdminUser>(`/admin/users/${userId}/role`, { method: 'PATCH', body: { role } });

export const lockUser = (userId: number, reason?: string): Promise<AdminUser> =>
  apiRequest<AdminUser>(`/admin/users/${userId}/lock`, { method: 'POST', body: { reason: reason ?? null } });

export const unlockUser = (userId: number): Promise<AdminUser> =>
  apiRequest<AdminUser>(`/admin/users/${userId}/unlock`, { method: 'POST' });
