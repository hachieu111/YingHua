// Phát âm qua máy chủ (M11: F11.01-F11.03, F11.06). Khách dùng được nhưng bị giới hạn độ dài.
import { apiRequest } from './client';

export interface TtsResult {
  audio: Blob;
  voice: string | null;
  rate: number | null;
  /** true khi giọng đã chọn không khả dụng và máy chủ chuyển sang giọng mặc định. */
  voiceFallback: boolean;
  cacheHit: boolean;
}

export interface SynthesizeOptions {
  rate?: number;
  voice?: string;
  signal?: AbortSignal;
}

export const TTS_MIN_RATE = 0.5;
export const TTS_MAX_RATE = 1.5;

export async function synthesize(text: string, options: SynthesizeOptions = {}): Promise<TtsResult> {
  const { rate, voice, signal } = options;
  const body: Record<string, unknown> = { text };
  if (rate !== undefined) body.rate = Math.min(TTS_MAX_RATE, Math.max(TTS_MIN_RATE, rate));
  if (voice) body.voice = voice;

  let headers: Headers | null = null;
  const audio = await apiRequest<Blob>('/tts', {
    method: 'POST',
    body,
    responseType: 'blob',
    signal,
    onResponse: res => {
      headers = res.headers;
    }
  });
  const h = headers as Headers | null;
  const rateHeader = h?.get('X-TTS-Rate');
  return {
    audio,
    voice: h?.get('X-TTS-Voice') ?? null,
    rate: rateHeader ? Number(rateHeader) : null,
    voiceFallback: h?.get('X-TTS-Voice-Fallback') === 'true',
    cacheHit: h?.get('X-TTS-Cache') === 'hit'
  };
}

export interface TtsVoice {
  short_name: string;
  locale: string;
  gender: 'female' | 'male' | string;
  friendly_name: string;
}

export interface TtsVoiceList {
  items: TtsVoice[];
  source: 'service' | 'default' | string;
}

/** Danh sách giọng đọc tiếng Trung khả dụng (M11). */
export const listVoices = (signal?: AbortSignal): Promise<TtsVoiceList> => apiRequest<TtsVoiceList>('/tts/voices', { signal });
