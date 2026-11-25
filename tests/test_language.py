"""语言参数测试。"""
from utils import make_wav_bytes


def test_language_zh(client):
    resp = client.post(
        "/api/transcribe",
        data={"language": "zh"},
        files={"file": ("a.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 200


def test_language_en(client):
    resp = client.post(
        "/api/transcribe",
        data={"language": "en"},
        files={"file": ("a.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 200


def test_language_invalid(client):
    resp = client.post(
        "/api/transcribe",
        data={"language": "fr"},
        files={"file": ("a.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 400
    assert "language" in resp.json()["detail"]
