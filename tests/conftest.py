"""pytest 共享 fixture。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.asr import ModelLoadError
from app.main import app, get_asr_service


class FakeASR:
    """Mock ASR 服务，避免下载模型。"""

    def __init__(self, zh_text: str = "你好，欢迎使用语音识别系统。") -> None:
        self.zh_text = zh_text
        self.load_error = False
        self.fail = False
        self.calls: list[tuple] = []

    def transcribe(self, audio, language: str) -> str:
        self.calls.append((audio, language))
        if self.load_error:
            raise ModelLoadError("模型加载失败: mock")
        if self.fail:
            raise RuntimeError("推理失败: mock")
        if language == "en":
            return "Hello, welcome to the speech recognition system."
        return self.zh_text


@pytest.fixture
def fake_asr() -> FakeASR:
    return FakeASR()


@pytest.fixture
def client(fake_asr: FakeASR):
    app.dependency_overrides[get_asr_service] = lambda: fake_asr
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
