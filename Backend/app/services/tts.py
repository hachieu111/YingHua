"""Phát âm bằng edge-tts (giọng neural Microsoft Edge, miễn phí) + cache file mp3 trong DB."""

import hashlib

import edge_tts
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import StoredFile, TtsCache
from . import storage

VOICES = {
    "zh-CN-XiaoxiaoNeural": "Nữ (Xiaoxiao)",
    "zh-CN-YunxiNeural": "Nam (Yunxi)",
    "zh-CN-XiaoyiNeural": "Nữ (Xiaoyi)",
    "zh-CN-YunjianNeural": "Nam (Yunjian)",
}


async def synthesize(text: str, voice: str, rate: str = "+0%") -> bytes:
    chunks = []
    async for part in edge_tts.Communicate(text, voice, rate=rate).stream():
        if part["type"] == "audio":
            chunks.append(part["data"])
    if not chunks:
        raise RuntimeError("edge-tts không trả về âm thanh")
    return b"".join(chunks)


def cache_key(text: str, rate: str) -> str:
    return hashlib.sha256(f"{rate}|{text}".encode()).hexdigest()


def get_cached(db: Session, text: str, voice: str, rate: str) -> StoredFile | None:
    row = db.execute(select(TtsCache).where(TtsCache.text_sha256 == cache_key(text, rate),
                                            TtsCache.voice == voice)).scalar_one_or_none()
    if row is None:
        return None
    f = db.get(StoredFile, row.file_id)
    if f is None or not storage.file_path(f).exists():
        db.delete(row)
        db.commit()
        return None
    return f


def store(db: Session, text: str, voice: str, rate: str, audio: bytes) -> StoredFile:
    f = storage.save_bytes(db, audio, "audio", "audio/mpeg")
    key = cache_key(text, rate)
    exists = db.execute(select(TtsCache).where(TtsCache.text_sha256 == key, TtsCache.voice == voice)
                        ).scalar_one_or_none()
    if exists is None:
        db.add(TtsCache(text_sha256=key, voice=voice, file_id=f.id))
    db.commit()
    return f
