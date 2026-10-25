import React, { useCallback, useEffect, useState } from 'react';
import { getUserOverview, UserOverview } from '../api/adminUserData';
import { errorMessage, formatDateTime, LoadState, Stat } from './AdminDataParts';

/** Tổng quan số liệu của một người dùng (F13.07). */
export const AdminUserOverviewTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [data, setData] = useState<UserOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getUserOverview(userId)
      .then(setData)
      .catch(err => setError(errorMessage(err, 'Không tải được tổng quan')))
      .finally(() => setLoading(false));
  }, [userId]);

  useEffect(load, [load]);

  if (!data) return <LoadState loading={loading} error={error} onRetry={load} />;
  const { user } = data;
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl border border-slate-100 p-4 text-xs text-slate-600 grid sm:grid-cols-2 gap-1">
        <div><b>Email:</b> {user.email}</div>
        <div><b>Vai trò:</b> {user.role === 'admin' ? 'Quản trị viên' : 'Học viên'}</div>
        <div><b>Trạng thái:</b> {user.status === 'locked' ? `Đã khóa${user.locked_reason ? ` (${user.locked_reason})` : ''}` : 'Đang hoạt động'}</div>
        <div><b>Tham gia:</b> {formatDateTime(user.created_at)}</div>
        <div><b>Hoạt động gần nhất:</b> {formatDateTime(data.last_active_at)}</div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <Stat label="Tổng số từ" value={data.vocab_total} />
        <Stat label="Đang học" value={data.vocab_counts.learning} />
        <Stat label="Đã thuộc" value={data.vocab_counts.known} />
        <Stat label="Bỏ qua" value={data.vocab_counts.ignored} />
        <Stat label="Tổng số thẻ" value={data.cards_total} />
        <Stat label="Thẻ đến hạn" value={data.cards_due} />
        <Stat label="Lượt ôn hôm nay" value={data.reviews_today} />
        <Stat label="Tổng lượt ôn" value={data.reviews_total} />
        <Stat label="Truyện riêng" value={data.private_series} />
        <Stat label="Ảnh tải nhanh" value={data.quick_uploads} />
      </div>
    </div>
  );
};
