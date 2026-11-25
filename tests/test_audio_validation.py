"""音频校验测试：空文件、损坏文件、超限文件、静音。"""
import io
import wave

from fastapi.testclient import TestClient

from app import config
from app.main import app


def test_empty_file(client):
    resp = client.post(
        "/api/transcribe",
        data={"language": "zh"},
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert resp.status_code == 400


def test_corrupt_file(client):
    resp = client.post(
        "/api/transcribe",
        data={"language": "zh"},
        files={"file": ("bad.wav", b"this-is-not-audio", "audio/wav")},
    )
    assert resp.status_code == 400


def test_oversize_file(client):
    big = b"0" * (config.MAX_FILE_SIZE + 1)
    resp = client.post(
        "/api/transcribe",
        data={"language": "zh"},
        files={"file": ("big.wav", big, "audio/wav")},
    )
    assert resp.status_code == 413


def _silent_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


def test_silence_returns_empty_text():
    with TestClient(app) as c:
        resp = c.post(
            "/api/transcribe",
            data={"language": "zh"},
            files={"file": ("silent.wav", _silent_wav(), "audio/wav")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == ""
    assert body["audio_rms"] < config.SILENCE_RMS_THRESHOLD
