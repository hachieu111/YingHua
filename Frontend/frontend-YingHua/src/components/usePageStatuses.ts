import { useCallback, useEffect, useRef, useState } from 'react';
import { PageStatus, getPageStatus } from '../api/imaging';

const POLL_INTERVAL_MS = 5000;
/** Quá thời gian này mà trang vẫn chưa xong thì ngừng hỏi và báo người học (worker có thể chưa chạy). */
const POLL_TIMEOUT_MS = 10 * 60 * 1000;

const isFinished = (status: PageStatus | undefined): boolean =>
  status !== undefined && (status.status === 'done' || status.status === 'failed' || status.status === null);

/**
 * Hỏi trạng thái xử lý các trang định kỳ (F04.02) cho đến khi xong, lỗi hoặc hết thời gian chờ.
 * Dừng ngay khi `enabled` = false hoặc component bị gỡ (vd. đóng cửa sổ tải lên).
 */
export function usePageStatuses(pageIds: number[], enabled: boolean) {
  const [statuses, setStatuses] = useState<Record<number, PageStatus>>({});
  const [timedOut, setTimedOut] = useState(false);
  const [round, setRound] = useState(0);
  const latest = useRef<Record<number, PageStatus>>({});
  const key = pageIds.join(',');

  useEffect(() => {
    if (!enabled || pageIds.length === 0) return;
    const controller = new AbortController();
    const startedAt = Date.now();
    let timer: ReturnType<typeof setTimeout> | undefined;
    setTimedOut(false);

    const poll = async () => {
      const pending = pageIds.filter(id => !isFinished(latest.current[id]));
      if (pending.length === 0) return;
      await Promise.all(
        pending.map(async id => {
          try {
            const status = await getPageStatus(id, controller.signal);
            latest.current = { ...latest.current, [id]: status };
          } catch {
            // Lỗi mạng tạm thời hoặc đã hủy: giữ trạng thái cũ, lượt sau thử lại.
          }
        })
      );
      if (controller.signal.aborted) return;
      setStatuses({ ...latest.current });
      if (pageIds.every(id => isFinished(latest.current[id]))) return;
      if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
        setTimedOut(true);
        return;
      }
      timer = setTimeout(poll, POLL_INTERVAL_MS);
    };

    poll();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled, round]);

  /** Sau khi bấm Dịch lại: coi trang là đang xếp hàng và hỏi lại từ đầu. */
  const restart = useCallback((pageId: number) => {
    const { [pageId]: _removed, ...rest } = latest.current;
    latest.current = rest;
    setStatuses({ ...rest });
    setRound(value => value + 1);
  }, []);

  return { statuses, timedOut, restart };
}
