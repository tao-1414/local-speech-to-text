"""测试工具函数。"""
from __future__ import annotations

import io
import math
import struct
import wave


def make_wav_bytes(seconds: float = 0.5, rate: int = 16000, freq: int = 440) -> bytes:
    """生成一段有效 WAV 音频字节（单声道 16bit PCM 正弦波）。"""
    n = int(rate * seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            val = int(0.4 * 32767 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))
    return buf.getvalue()
