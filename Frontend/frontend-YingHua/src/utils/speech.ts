// Phát âm tiếng Trung: ưu tiên TTS máy chủ (F11.01), dự phòng Web Speech của trình duyệt (F11.06).
import { synthesize, TTS_MAX_RATE, TTS_MIN_RATE } from '../api/tts';

const MAX_CACHED_AUDIO = 40;
const FALLBACK_NOTICE = 'Không phát được âm thanh máy chủ, đang dùng giọng của trình duyệt';
const VOICE_FALLBACK_NOTICE = 'Giọng đã chọn không khả dụng, đã chuyển sang giọng mặc định';

type NoticeListener = (message: string) => void;

let noticeListener: NoticeListener | null = null;
const shownNotices = new Set<string>();

/** Đăng ký nơi hiển thị thông báo nhẹ (toast). Trả về hàm hủy đăng ký. */
export function setSpeechNoticeListener(listener: NoticeListener | null): () => void {
  noticeListener = listener;
  return () => {
    if (noticeListener === listener) noticeListener = null;
  };
}

// Mỗi thông báo chỉ hiện một lần để không làm phiền khi bấm nghe liên tục.
function noticeOnce(message: string): void {
  if (shownNotices.has(message)) return;
  shownNotices.add(message);
  noticeListener?.(message);
}

/** Bộ nhớ đệm đối tượng URL theo (văn bản, tốc độ); xóa mục cũ nhất khi đầy. */
const audioCache = new Map<string, string>();

const cacheKey = (text: string, rate: number) => `${rate.toFixed(2)}|${text}`;

function rememberAudio(key: string, url: string): void {
  audioCache.set(key, url);
  while (audioCache.size > MAX_CACHED_AUDIO) {
    const oldest = audioCache.keys().next().value as string;
    URL.revokeObjectURL(audioCache.get(oldest) as string);
    audioCache.delete(oldest);
  }
}

let currentAudio: HTMLAudioElement | null = null;
let currentStop: (() => void) | null = null;
let playToken = 0;

/** Dừng mọi âm thanh đang phát (cả máy chủ lẫn trình duyệt). */
export function stopSpeaking(): void {
  playToken += 1;
  currentStop?.();
  currentStop = null;
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel();
}

function playUrl(url: string, token: number): Promise<boolean> {
  return new Promise(resolve => {
    const audio = new Audio(url);
    currentAudio = audio;
    const finish = (ok: boolean) => {
      if (currentAudio === audio) currentAudio = null;
      if (currentStop === stop) currentStop = null;
      resolve(ok);
    };
    // Bị thay bởi lần phát mới: coi như đã xử lý, không dự phòng.
    const stop = () => finish(true);
    currentStop = stop;
    audio.onended = () => finish(true);
    audio.onerror = () => finish(token !== playToken);
    audio.play().catch(() => finish(token !== playToken));
  });
}

function speakWithBrowser(text: string, rate: number): Promise<boolean> {
  return new Promise(resolve => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      resolve(false);
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = rate;
      const chineseVoice = window.speechSynthesis.getVoices().find(v => v.lang.startsWith('zh'));
      if (chineseVoice) utterance.voice = chineseVoice;
      utterance.onend = () => resolve(true);
      utterance.onerror = event => resolve(event.error === 'canceled' || event.error === 'interrupted');
      window.speechSynthesis.speak(utterance);
    } catch {
      resolve(false);
    }
  });
}

/**
 * Đọc to một đoạn tiếng Trung. Trả về true nếu đã phát được (máy chủ hoặc trình duyệt),
 * false nếu cả hai đều không phát được. Không bao giờ ném lỗi.
 */
export async function speakChinese(text: string, rate: number = 0.85): Promise<boolean> {
  if (typeof window === 'undefined' || !text.trim()) return true;
  stopSpeaking();
  const token = playToken;
  const clamped = Math.min(TTS_MAX_RATE, Math.max(TTS_MIN_RATE, rate));
  const key = cacheKey(text, clamped);

  let url = audioCache.get(key);
  if (!url) {
    try {
      const result = await synthesize(text, { rate: clamped });
      if (token !== playToken) return true;
      url = URL.createObjectURL(result.audio);
      rememberAudio(key, url);
      if (result.voiceFallback) noticeOnce(VOICE_FALLBACK_NOTICE);
    } catch {
      if (token !== playToken) return true;
      noticeOnce(FALLBACK_NOTICE);
      return speakWithBrowser(text, rate);
    }
  }

  const played = await playUrl(url, token);
  if (played) return true;
  noticeOnce(FALLBACK_NOTICE);
  return speakWithBrowser(text, rate);
}
