"""ASR 服务单元测试（不需要下载模型）。"""
import numpy as np

from app.asr import ASRService


def test_empty_audio_returns_empty():
    service = ASRService()
    assert service.transcribe(np.array([], dtype=np.float32), "zh") == ""


def test_silence_returns_empty_without_loading_model():
    service = ASRService()
    silent = np.zeros(16000, dtype=np.float32)
    assert service.transcribe(silent, "zh") == ""
    assert service._model is None
