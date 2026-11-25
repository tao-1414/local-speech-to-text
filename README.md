# Local AI Speech-to-Text Web Application

基于 B/S 架构的本地语音识别系统。用户通过浏览器麦克风录制语音，或上传音频文件，系统使用本地开源 ASR 模型（faster-whisper）将中文或英文语音转换为文字，并在 Web 页面展示结果。

## 功能

- 浏览器麦克风录音（最长 60 秒），支持中文 / 英文识别
- 音频文件上传识别（WAV、WebM、MP3 等）
- 识别结果展示：文本、音频时长、处理耗时，支持一键复制
- 异常处理：权限拒绝、无麦克风、空/损坏文件、格式不支持、模型失败等
- 实时语音识别（加分功能，可开关）
- 本地推理：模型首次联网下载后即可离线运行，CPU 推理，无需 GPU

## 环境要求

| 项目 | 要求 |
| ---- | ---- |
| 操作系统 | Windows 11 x64（macOS / Linux 亦可开发） |
| Python | 3.12 |
| 浏览器 | Chrome / Edge 最新稳定版 |
| 硬件 | 普通 CPU（无需 GPU / CUDA） |

无需 Docker、Node.js、数据库、Redis 或任何云端语音服务。

## 安装与启动

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问：<http://127.0.0.1:8000>

### 模型初始化

首次调用识别接口时会自动从 HuggingFace 下载模型权重（需要联网一次），默认使用 `small` 模型。之后识别过程完全离线运行。

可通过环境变量调整模型：

| 环境变量 | 默认值 | 说明 |
| -------- | ------ | ---- |
| `WHISPER_MODEL` | `small` | 模型大小：`tiny` / `base` / `small` / `medium` |
| `WHISPER_DEVICE` | `cpu` | 推理设备 |
| `WHISPER_COMPUTE_TYPE` | `int8` | 量化类型 |
| `WHISPER_CACHE_DIR` | 默认 | 模型下载目录 |
| `WHISPER_VAD` | `1` | 是否启用 VAD 过滤（`0` 关闭，用于排查） |
| `SILENCE_RMS_THRESHOLD` | `1e-4` | 静音判定阈值（低于视为数字静音，返回空文本） |

> 离线运行：模型权重下载完成（缓存到 HuggingFace 目录）后，识别过程无需联网。若下载受网络限制，可设置 `HF_ENDPOINT=https://hf-mirror.com` 使用镜像。

## 接口

| Method | Endpoint | 说明 |
| ------ | -------- | ---- |
| GET | `/health` | 健康检查，返回 `{"status":"ok"}` |
| POST | `/api/transcribe` | 上传音频并识别（`multipart/form-data`：`file` + `language`） |
| GET | `/` | Web 页面 |

识别响应示例：

```json
{
  "text": "你好，欢迎使用语音识别系统。",
  "language": "zh",
  "duration_seconds": 5.5,
  "processing_seconds": 1.2,
  "audio_rms": 0.08321
}
```

> `audio_rms` 为附加诊断字段（音频音量均方根），用于判断录音是否过轻；无语音时 `text` 为空字符串。

## 测试

常规自动化测试（Mock 模型，不下载模型、不依赖麦克风）：

```bash
python -m pytest -q
```

真实模型测试（需联网下载模型，使用 `samples/` 音频）：

```bash
# Windows PowerShell
$env:RUN_REAL_MODEL="1"
python -m pytest tests/test_real_model.py -q

# macOS / Linux
RUN_REAL_MODEL=1 python -m pytest tests/test_real_model.py -q
```

> `samples/reference.txt` 为两份样本的人工参考文本，可用于比对识别结果。
> 模型缓存完成后，断开网络再次执行上述真实模型测试仍应通过，以验证离线推理。

## 常见问题

- **录音识别不出文字 / 结果为空**：多为麦克风未采集到声音。后端终端会打印
  `[transcribe] ... duration=...s rms=...`，若 `duration` 接近 0 或 `rms` 很小
  （如 < 0.005），请检查系统输入设备、浏览器麦克风权限与输入音量。
  可先用「音频文件上传」选择 `samples/chinese.wav` 验证后端是否正常。
- **识别出「字幕by索兰娅」等无关文本**：这是 Whisper 在静音上的幻觉，已通过
  静音预检 + VAD 过滤规避；如仍有，可用 `WHISPER_VAD=0` 关闭 VAD 对比排查。

## 项目结构

```
local-speech-to-text/
├── app/                 # 后端（FastAPI + ASR 集成）
│   ├── main.py
│   ├── config.py
│   ├── audio.py
│   └── asr.py
├── static/              # 前端（HTML/CSS/JS）
├── tests/               # pytest 自动化测试
├── samples/             # 测试音频（chinese.wav / english.wav / reference.txt）
├── docs/                # 文档（requirements / design / test-report / ai-development）
├── requirements.txt
└── .gitignore
```

## 文档

- [docs/requirements.md](docs/requirements.md) — 需求理解与功能拆分
- [docs/design.md](docs/design.md) — 系统架构与模型选型
- [docs/test-report.md](docs/test-report.md) — 测试报告
- [docs/ai-development.md](docs/ai-development.md) — AI 开发过程记录
