/** Số chương hiển thị: 12 hoặc 12.5. */
export const formatChapterNumber = (value: number): string => (Number.isInteger(value) ? String(value) : value.toFixed(1));

/** "Vừa xong", "3 giờ trước", "Hôm qua"... từ thời điểm ISO 8601. */
export function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Hôm qua';
  if (days < 30) return `${days} ngày trước`;
  return new Date(iso).toLocaleDateString('vi-VN');
}

/** Khoảng cách tới lần ôn kế tiếp: "< 1 phút", "10 phút", "3 giờ", "5 ngày", "2 tháng". */
export function formatInterval(seconds: number): string {
  if (seconds < 60) return '< 1 phút';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} giờ`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} ngày`;
  const months = Math.round(days / 30);
  return months < 12 ? `${months} tháng` : `${Math.round(days / 365)} năm`;
}

/** Ngày giờ ngắn theo múi giờ trình duyệt: "14:05 25/10/2026". */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  const time = date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  return `${time} ${date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })}`;
}
