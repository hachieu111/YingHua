import React, { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'yinghua-theme';
const RIPPLE_MS = 950;
const RIPPLE_START_TIMEOUT_MS = 400;
/** Bằng bề rộng viền gợn trong index.css, để vòng lan phủ kín góc xa nhất. */
const RIPPLE_EDGE_PX = 170;
const readStoredTheme = (): Theme | null => {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
};

/** Lựa chọn đã lưu, nếu chưa chọn thì theo cài đặt hệ điều hành. */
export const resolveTheme = (): Theme => {
  const stored = readStoredTheme();
  if (stored) return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

/** Gắn/gỡ class `dark` trên <html>; main.tsx gọi trước khi render để F5 không bị nháy trắng. */
export const applyThemeClass = (theme: Theme): void => {
  document.documentElement.classList.toggle('dark', theme === 'dark');
};

export interface RippleOrigin {
  x: number;
  y: number;
}

/** Tâm vòng lan: chỗ bấm chuột, hoặc giữa nút khi bấm bằng bàn phím (tọa độ sự kiện bằng 0). */
export const rippleOriginOf = (event: React.MouseEvent<HTMLElement>): RippleOrigin => {
  if (event.clientX || event.clientY) return { x: event.clientX, y: event.clientY };
  const box = event.currentTarget.getBoundingClientRect();
  return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
};

/** Giao diện mới lan từ nút bấm như gợn nước, phần viền xử lý bằng mask trong index.css. */
const playThemeRipple = async (origin: RippleOrigin, commit: () => void): Promise<void> => {
  const root = document.documentElement;
  const radius = Math.hypot(
    Math.max(origin.x, window.innerWidth - origin.x),
    Math.max(origin.y, window.innerHeight - origin.y)
  );
  root.style.setProperty('--ripple-x', `${origin.x}px`);
  root.style.setProperty('--ripple-y', `${origin.y}px`);
  // Tắt transition màu trong lúc chụp, nếu không ảnh giao diện mới là khung đầu của lần chuyển màu.
  root.classList.add('theme-rippling');
  let committed = false;
  const commitOnce = () => {
    if (committed) return;
    committed = true;
    commit();
  };
  const transition = document.startViewTransition(commitOnce);
  // Trang không vẽ khung hình (khung nhúng bị ẩn) thì trình duyệt không chạy callback: vẫn phải đổi giao diện.
  const watchdog = window.setTimeout(() => {
    commitOnce();
    transition.skipTransition();
    root.classList.remove('theme-rippling');
  }, RIPPLE_START_TIMEOUT_MS);
  try {
    await transition.ready;
    window.clearTimeout(watchdog);
    root.animate(
      { '--theme-ripple': ['0px', `${radius + RIPPLE_EDGE_PX}px`] },
      // `forwards` giữ bán kính cuối: không có nó mask về 0 một khung trước khi trình duyệt gỡ lớp chuyển,
      // giao diện cũ hiện lại chớp một cái rồi mới sang giao diện mới.
      {
        duration: RIPPLE_MS,
        easing: 'cubic-bezier(0.33, 0, 0.2, 1)',
        fill: 'forwards',
        pseudoElement: '::view-transition-new(root)'
      }
    );
    await transition.finished;
  } catch {
    // Hiệu ứng bị bỏ qua (đổi tab, trình duyệt ngắt): giao diện vẫn được đổi, không cần báo lỗi.
    commitOnce();
  } finally {
    window.clearTimeout(watchdog);
    root.classList.remove('theme-rippling');
  }
};

interface ThemeState {
  theme: Theme;
  toggleTheme: (origin?: RippleOrigin) => void;
}

const ThemeContext = createContext<ThemeState>({ theme: 'light', toggleTheme: () => undefined });

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(resolveTheme);
  const rippling = useRef(false);

  useLayoutEffect(() => {
    applyThemeClass(theme);
  }, [theme]);

  // Đồng bộ giữa các tab và khi hệ điều hành đổi giao diện (chỉ khi người dùng chưa tự chọn).
  useEffect(() => {
    const sync = () => setThemeState(resolveTheme());
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY || event.key === null) sync();
    };
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    window.addEventListener('storage', onStorage);
    media?.addEventListener('change', sync);
    return () => {
      window.removeEventListener('storage', onStorage);
      media?.removeEventListener('change', sync);
    };
  }, []);

  const toggleTheme = useCallback(
    (origin?: RippleOrigin) => {
      if (rippling.current) return;
      const next: Theme = theme === 'dark' ? 'light' : 'dark';
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Trình duyệt chặn lưu trữ: vẫn đổi giao diện trong phiên này.
      }
      const commit = () => {
        flushSync(() => setThemeState(next));
        applyThemeClass(next);
      };
      const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      if (!origin || reduced || !document.startViewTransition) {
        commit();
        return;
      }
      rippling.current = true;
      void playThemeRipple(origin, commit).finally(() => {
        rippling.current = false;
      });
    },
    [theme]
  );

  const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeState => useContext(ThemeContext);
