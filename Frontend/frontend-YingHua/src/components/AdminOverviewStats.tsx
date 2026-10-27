import React, { useCallback, useEffect, useState } from 'react';
import { Activity, BookOpen, CheckCheck, Users } from 'lucide-react';
import { SystemStats, getSystemStats } from '../api/adminSystem';
import { isAbortedError } from '../api/client';
import { LoadState, Stat, errorMessage, formatDateTime } from './AdminDataParts';

const formatNumber = (value: number): string => value.toLocaleString('vi-VN');
const formatPercent = (rate: number | null): string => (rate === null ? 'Chưa có dữ liệu' : `${(rate * 100).toFixed(1)}%`);
const formatMinutes = (seconds: number): string => `${Math.round(seconds / 60).toLocaleString('vi-VN')} phút`;

const Card: React.FC<{ title: string; icon: React.ReactNode; tone: string; children: React.ReactNode }> = ({ title, icon, tone, children }) => (
  <article className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
    <div className="flex items-center justify-between gap-2">
      <h3 className="text-[11px] font-bold text-slate-500">{title}</h3>
      <span className={`flex h-7 w-7 items-center justify-center rounded-full ${tone}`}>{icon}</span>
    </div>
    <div className="mt-3 grid grid-cols-2 gap-2">{children}</div>
  </article>
);

/** Thống kê toàn hệ thống (F12.03): người dùng, nội dung, xử lý ảnh, hoạt động học. */
export const AdminOverviewStats: React.FC = () => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    getSystemStats(controller.signal)
      .then(result => {
        setStats(result);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err, 'Không tải được thống kê hệ thống'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [tick]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') reload();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [reload]);

  if (!stats) return <div className="mb-4"><LoadState loading={loading} error={error} onRetry={reload} /></div>;

  const { users, content, imaging, activity_today: today, activity_7_days: week } = stats;
  return (
    <div className="mb-5">
      {error && <div className="mb-2"><LoadState loading={false} error={error} onRetry={reload} /></div>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Người dùng" icon={<Users size={16} />} tone="bg-blue-100 text-blue-700">
          <Stat label="Tổng" value={formatNumber(users.total)} />
          <Stat label="Mới 7 ngày" value={formatNumber(users.new_last_7_days)} />
          <Stat label="Quản trị viên" value={formatNumber(users.admins)} />
          <Stat label="Bị khóa" value={formatNumber(users.locked)} />
        </Card>
        <Card title="Nội dung" icon={<BookOpen size={16} />} tone="bg-pink-100 text-pink-700">
          <Stat label="Truyện" value={`${formatNumber(content.series_total)} (${formatNumber(content.series_public)} công khai)`} />
          <Stat label="Chương" value={formatNumber(content.chapters)} />
          <Stat label="Trang" value={formatNumber(content.pages)} />
          <Stat label="Từ đã lưu" value={formatNumber(stats.words_saved_total)} />
        </Card>
        <Card title="Xử lý ảnh (OCR)" icon={<CheckCheck size={16} />} tone="bg-amber-100 text-amber-700">
          <Stat label="Tỉ lệ thành công" value={formatPercent(imaging.ocr_success_rate)} />
          <Stat label="Tỉ lệ lỗi" value={formatPercent(imaging.ocr_failure_rate)} />
          <Stat label="Chờ / đang chạy" value={`${formatNumber(imaging.pages_queued)} / ${formatNumber(imaging.pages_running)}`} />
          <Stat label="Thời gian TB" value={imaging.avg_processing_ms === null ? 'Chưa có dữ liệu' : `${(imaging.avg_processing_ms / 1000).toFixed(1)} giây`} />
        </Card>
        <Card title="Hoạt động học" icon={<Activity size={16} />} tone="bg-rose-100 text-rose-700">
          <Stat label="Học viên hôm nay" value={formatNumber(today.active_users)} />
          <Stat label="Lượt ôn hôm nay" value={formatNumber(today.reviews_count)} />
          <Stat label="Trang đọc 7 ngày" value={formatNumber(week.pages_read)} />
          <Stat label="Thời gian học 7 ngày" value={formatMinutes(week.study_seconds)} />
        </Card>
      </div>
      <p className="mt-2 text-right text-[10px] text-slate-400">Cập nhật {formatDateTime(stats.generated_at)}</p>
    </div>
  );
};
