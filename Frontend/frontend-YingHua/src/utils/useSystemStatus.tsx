import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { MAINTENANCE_EVENT } from '../api/client';
import { SystemStatus, getSystemStatus } from '../api/system';
import { setTtsAvailable } from './speech';

// Khi chưa biết trạng thái (đang tải hoặc máy chủ chưa trả lời) coi như bình thường để không khóa tính năng oan.
const DEFAULT_STATUS: SystemStatus = {
  maintenance_mode: false,
  message: null,
  llm_enabled: true,
  tts_enabled: true,
  sample_page_available: false
};

const SystemStatusContext = createContext<SystemStatus>(DEFAULT_STATUS);

/** Trạng thái hệ thống lấy từ máy chủ; tải lại khi quay lại tab và khi API báo đang bảo trì. */
export const SystemStatusProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<SystemStatus>(DEFAULT_STATUS);

  useEffect(() => {
    let controller = new AbortController();
    const load = () => {
      controller.abort();
      controller = new AbortController();
      const { signal } = controller;
      getSystemStatus(signal)
        .then(setStatus)
        .catch(() => undefined); // Mất mạng: giữ trạng thái cũ, không coi là bảo trì.
    };
    const onVisible = () => {
      if (document.visibilityState === 'visible') load();
    };
    load();
    window.addEventListener('focus', onVisible);
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener(MAINTENANCE_EVENT, load);
    return () => {
      controller.abort();
      window.removeEventListener('focus', onVisible);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener(MAINTENANCE_EVENT, load);
    };
  }, []);

  useEffect(() => setTtsAvailable(status.tts_enabled), [status.tts_enabled]);

  const value = useMemo(() => status, [status]);
  return <SystemStatusContext.Provider value={value}>{children}</SystemStatusContext.Provider>;
};

export const useSystemStatus = (): SystemStatus => useContext(SystemStatusContext);
