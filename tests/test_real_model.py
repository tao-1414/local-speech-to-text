"""真实模型测试（需先下载模型，默认跳过）。

运行方式：
    python -m pytest tests/test_real_model.py -q
或设置环境变量 RUN_REAL_MODEL=1：
    RUN_REAL_MODEL=1 python -m pytest -q

依赖 samples/ 下的测试音频。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

REAL_MODEL = os.environ.get("RUN_REAL_MODEL", "0") == "1"


def _read(name: str) -> bytes:
    return (SAMPLES_DIR / name).read_bytes()


@pytest.mark.skipif(not REAL_MODEL, reason="需要真实模型，设置 RUN_REAL_MODEL=1 运行")
class TestRealModel:
    def test_chinese_real(self):
        with TestClient(app) as client:
            resp = client.post(
                "/api/transcribe",
                data={"language": "zh"},
                files={"file": ("chinese.wav", _read("chinese.wav"), "audio/wav")},
            )
        assert resp.status_code == 200
        assert resp.json()["language"] == "zh"
        assert resp.json()["text"].strip() != ""

    def test_english_real(self):
        with TestClient(app) as client:
            resp = client.post(
                "/api/transcribe",
                data={"language": "en"},
                files={"file": ("english.wav", _read("english.wav"), "audio/wav")},
            )
        assert resp.status_code == 200
        assert resp.json()["language"] == "en"
        assert resp.json()["text"].strip() != ""
