"""错误处理测试：模型加载失败、推理失败。"""
from utils import make_wav_bytes


def test_model_load_failure(client, fake_asr):
    fake_asr.load_error = True
    resp = client.post(
        "/api/transcribe",
        data={"language": "zh"},
        files={"file": ("a.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 503


def test_inference_failure(client, fake_asr):
    fake_asr.fail = True
    resp = client.post(
        "/api/transcribe",
        data={"language": "zh"},
        files={"file": ("a.wav", make_wav_bytes(0.5), "audio/wav")},
    )
    assert resp.status_code == 500
