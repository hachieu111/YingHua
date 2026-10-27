import React from 'react';
import { useSystemStatus } from '../utils/useSystemStatus';

/** Băng thông báo bảo trì (F13.05); không chặn thao tác, chỉ báo một số tính năng có thể tạm ngưng. */
export const MaintenanceBanner: React.FC = () => {
  const { maintenance_mode, message } = useSystemStatus();
  if (!maintenance_mode) return null;
  return (
    <div role="status" className="fixed bottom-0 inset-x-0 z-[60] bg-amber-100 text-amber-900 border-t border-amber-300 px-4 py-2 flex items-center justify-center gap-2 text-xs font-semibold">
      <span className="material-symbols-outlined text-[18px]">construction</span>
      <span>{message ?? 'Hệ thống đang bảo trì, một số tính năng tạm thời không dùng được.'}</span>
    </div>
  );
};
