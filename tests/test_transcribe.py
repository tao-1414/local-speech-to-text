"""识别接口正常请求测试。"""
from utils import make_wav_bytes


def test_transcribe_zh(client, fake_asr):
    resp = client.post(
        "/api/transcribe",
        data={"language": "zh"},
        files={"file": ("sample.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "zh"
    assert body["text"] == "你好，欢迎使用语音识别系统。"
    assert body["duration_seconds"] > 0
    assert body["processing_seconds"] >= 0


def test_transcribe_default_language_is_zh(client, fake_asr):
    resp = client.post(
        "/api/transcribe",
        files={"file": ("sample.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 200
    assert resp.json()["language"] == "zh"


def test_transcribe_en(client, fake_asr):
    resp = client.post(
        "/api/transcribe",
        data={"language": "en"},
        files={"file": ("sample.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "en"
    assert body["text"].startswith("Hello")
