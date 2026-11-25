"""健康检查与首页测试。"""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "本地语音识别" in resp.text
