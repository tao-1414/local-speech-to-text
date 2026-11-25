"""本地 ASR 服务（faster-whisper 懒加载封装）。"""
from __future__ import annotations

from typing import Optional

import numpy as np

from . import config
from .audio import rms


class ModelLoadError(Exception):
    """模型加载失败。"""


class ASRService:
    """封装 faster-whisper 模型，延迟到首次使用时加载。"""

    def __init__(
        self,
        model_size: str = config.MODEL_SIZE,
        device: str = config.DEVICE,
        compute_type: str = config.COMPUTE_TYPE,
        cache_dir: Optional[str] = config.MODEL_CACHE_DIR,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.cache_dir = cache_dir
        self._model = None
        self._model_error: Optional[str] = None

    @classmethod
    def from_config(cls) -> "ASRService":
        return cls()

    def _load(self):
        if self._model is not None:
            return self._model
        if self._model_error is not None:
            raise ModelLoadError(self._model_error)
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.cache_dir,
            )
        except Exception as exc:  # noqa: BLE001
            self._model_error = f"模型加载失败: {exc}"
            raise ModelLoadError(self._model_error) from exc
        return self._model

    @staticmethod
    def _rms(audio: np.ndarray) -> float:
        return rms(audio)

    def transcribe(self, audio: np.ndarray, language: str) -> str:
        """对音频执行识别，返回文本（无有效语音时返回空字符串）。"""
        audio = np.asarray(audio, dtype=np.float32)
        if audio.size == 0:
            return ""

        # 静音预检：几乎无声的音频直接返回，避免模型幻觉（如“字幕by索兰娅”）。
        if self._rms(audio) < config.SILENCE_RMS_THRESHOLD:
            return ""

        model = self._load()
        segments, _info = model.transcribe(
            audio,
            language=language,
            beam_size=5,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=config.VAD_ENABLED,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        parts = []
        for segment in segments:
            # 跳过被判定为非语音的高概率幻觉片段。
            if segment.no_speech_prob > 0.6 and segment.avg_logprob < -1.0:
                continue
            parts.append(segment.text)
        return "".join(parts).strip()
