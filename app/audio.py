"""音频加载与校验。"""
from __future__ import annotations

import io
from typing import Tuple

import numpy as np

from . import config


class AudioDecodeError(Exception):
    """音频无法解码或格式不受支持。"""


class EmptyAudioError(AudioDecodeError):
    """音频为空或没有可识别的数据。"""


def rms(audio: np.ndarray) -> float:
    """计算音频均方根，用于音量/静音判定。"""
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))


def load_audio(data: bytes, filename: str = "") -> Tuple[np.ndarray, float]:
    """将音频字节解码为 16kHz 单声道 float32，并返回音频时长（秒）。"""
    if not data:
        raise EmptyAudioError("上传的音频文件为空")

    try:
        from faster_whisper.audio import decode_audio

        audio = decode_audio(io.BytesIO(data), sampling_rate=config.SAMPLE_RATE)
    except Exception as exc:  # noqa: BLE001
        raise AudioDecodeError(f"无法解码音频文件（格式不支持或文件损坏）: {exc}") from exc

    if isinstance(audio, tuple):
        audio = audio[0]

    if audio is None:
        raise EmptyAudioError("音频中没有可识别的数据")

    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0:
        raise EmptyAudioError("音频中没有可识别的数据")

    duration = float(audio.size) / config.SAMPLE_RATE
    return audio, duration
