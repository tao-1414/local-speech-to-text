# 系统设计文档

## 1. 系统架构

系统采用经典的 B/S 三层结构：浏览器前端 + FastAPI 后端 + 本地 ASR 推理引擎。

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器 (Chrome/Edge)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ 麦克风录音    │  │ 音频文件上传  │  │ 结果展示 / 复制   │   │
│  └──────┬───────┘  └──────┬───────┘  └────────▲─────────┘   │
│         │  MediaRecorder   │ (WebM/Opus 或 WAV)  │           │
└─────────┼──────────────────┼─────────────────────┼───────────┘
          │  HTTP multipart  │                     │ JSON
          ▼                  ▼                     │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端 (Python 3.12)                 │
│  ┌───────────┐   ┌───────────────┐   ┌──────────────────┐   │
│  │ /health   │   │/api/transcribe│   │ 静态文件 / (前端)  │   │
│  └─────┬─────┘   └──────┬────────┘   └──────────────────┘   │
│        │                │ 音频解码 + 校验 (audio.py)          │
│        │                ▼                                     │
│        │         ┌──────────────┐                            │
│        │         │  ASR 服务     │  (asr.py, 懒加载)          │
│        │         └──────┬───────┘                            │
│        │                ▼                                     │
│        │    ┌───────────────────────────┐                    │
│        │    │  faster-whisper (CTranslate2)│                  │
│        │    │  本地开源模型 · CPU 推理     │                   │
│        │    └───────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 设计要点

- **前后端分离**：前端为纯静态 HTML/CSS/JS，由 FastAPI 托管；前后端通过 REST API 交互。
- **单一识别入口**：麦克风录音与文件上传统一调用 `POST /api/transcribe`，共用同一套解码与推理逻辑。
- **模型懒加载**：ASR 模型在首次识别请求时才加载，避免启动慢、避免健康检查触发模型下载。
- **无外部依赖**：不依赖数据库、Redis、Docker、Node.js；模型权重首次联网下载后即可离线运行。
- **可测试性**：ASR 通过 FastAPI 依赖注入提供，测试中可替换为 Mock 实现。

## 2. 核心模块

| 模块 | 文件 | 职责 |
| ---- | ---- | ---- |
| 应用入口 | `app/main.py` | FastAPI 实例、路由、静态托管、异常处理 |
| 配置 | `app/config.py` | 模型大小、设备、文件上限、语言白名单、静音阈值与 VAD 开关等 |
| 音频处理 | `app/audio.py` | 校验、解码为 16kHz 单声道浮点、计算时长 |
| ASR 服务 | `app/asr.py` | 懒加载 faster-whisper 模型、执行推理 |
| 前端 | `static/` | 录音、上传、语言选择、结果展示 |

### 2.1 依赖注入与懒加载

`main.py` 通过 FastAPI 依赖 `get_asr_service()` 暴露 ASR 单例：

```python
_asr_service: ASRService | None = None

def get_asr_service() -> ASRService:
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService.from_config()
    return _asr_service
```

测试中通过 `app.dependency_overrides[get_asr_service] = fake` 替换为 Mock，从而在不下载模型的情况下运行自动化测试。

## 3. 音频处理流程

```
上传字节流
   │
   ├─ 1. 大小校验 (≤ 10MB)                    → 超限返回 413
   ├─ 2. 空文件校验                            → 空返回 400
   ├─ 3. decode_audio (PyAV) 解码为
   │     mono 16kHz float32 numpy             → 解码失败返回 400
   ├─ 4. 计算时长 duration = len / 16000
   │
   ▼
静音预检 (RMS < 阈值 → 直接返回空文本，避免幻觉)
   │
   ▼
ASR 推理 (faster-whisper, language=zh|en, VAD 过滤)
   │
   ├─ 模型未加载 → 懒加载（首次联网下载权重）
   ├─ VAD 过滤非语音，跳过高 no_speech 概率片段
   ├─ 推理失败 → 返回 500（可理解的错误信息）
   ▼
返回 { text, language, duration_seconds, processing_seconds, audio_rms }
```

- 音频解码复用 `faster_whisper.audio.decode_audio`（内部基于 PyAV），无需 ffmpeg，支持 WAV、WebM/Opus（浏览器 MediaRecorder 默认格式）、FLAC、MP3、OGG 等。
- `processing_seconds` 从解码开始到推理结束计时，不含模型首次加载/下载时间。
- `audio_rms` 为附加诊断字段（音频音量均方根），用于判断录音是否过轻。

### 3.1 抗幻觉设计

- **静音预检**：`audio_rms < SILENCE_RMS_THRESHOLD`（默认 `1e-4`）时直接返回空文本，不加载模型，规避 Whisper 在静音上的幻觉（如「字幕by索兰娅」）。
- **VAD 过滤**：`vad_filter=WHISPER_VAD`（默认开启），使用其自带的 `silero_vad_v6.onnx` 去除静音片段。
- **片段过滤**：跳过 `no_speech_prob > 0.6 且 avg_logprob < -1.0` 的片段。
- 以上开关均可经环境变量调整，便于排查。

## 4. ASR 模型选型

### 4.1 选择：faster-whisper（CTranslate2 重实现 Whisper）

模型默认使用 `small`（可经环境变量 `WHISPER_MODEL` 切换为 `tiny/base/medium`）。

选择理由：

1. **中英文原生支持**：Whisper 多语言模型同时支持中文普通话与英语，无需切换模型。
2. **CPU 推理快**：基于 CTranslate2，默认 `int8` 量化，比原版 PyTorch Whisper 快数倍、内存占用更低，适配普通开发电脑 CPU。
3. **语言参数简单**：直接传入 `language="zh"` / `"en"`。
4. **离线可用**：权重首次联网下载到 HuggingFace 缓存后，推理完全离线。
5. **纯 Python、API 简单**：接受 numpy 数组，支持内存中解码，无需临时文件或原生编译依赖（ctranslate2 提供预编译 wheel）。

### 4.2 备选方案对比

| 方案 | 优点 | 未选原因 |
| ---- | ---- | -------- |
| openai/whisper (PyTorch) | 原始实现 | CPU 慢、依赖 torch 体积大 |
| Vosk | 轻量、快 | 中文精度较弱、语言切换需加载不同模型 |
| FunASR (Paraformer) | 中文强 | 英文较弱、依赖较重、部署复杂 |

## 5. 接口设计

| Method | Endpoint | 功能 |
| ------ | -------- | ---- |
| GET | `/health` | 健康检查，返回 `{"status":"ok"}` |
| POST | `/api/transcribe` | `multipart/form-data`（`file` + `language`），返回识别结果 JSON |
| GET | `/` | 返回前端页面 |

错误约定：

- 非法语言 / 空文件 / 无法解码 / 不支持格式 → HTTP 4xx，`detail` 含可理解信息。
- 文件超限 → HTTP 413。
- 模型加载失败 / 推理失败 → HTTP 5xx。

## 6. 前端设计

单页应用（`static/index.html` + `css/style.css` + `js/app.js`）：

- **录音区**：麦克风权限申请、开始/停止录音、时长显示、60 秒上限自动停止。
- **语言选择**：中文 / 英文 单选。
- **上传区**：选择本地音频文件并识别。
- **结果区**：显示状态（就绪/录音中/识别中/完成/错误）、识别文本、音频时长、处理耗时，并提供「复制」按钮。
- **实时识别（加分）**：录音过程中按固定间隔（如 3 秒）将累计音频分片发送后端，持续刷新已识别文本。

## 7. 测试设计

- **Mock 测试**：通过依赖注入替换 ASR 服务，覆盖健康检查、正常请求、非法语言、空/损坏文件、不支持格式、模型失败等，执行 `python -m pytest -q`，不依赖麦克风、不触发模型下载。
- **真实模型测试**：`tests/test_real_model.py` 使用 `samples/` 音频验证中英文真实识别，单独说明执行方式（需先下载模型）。
- **测试音频**：`samples/chinese.wav`、`samples/english.wav`（Windows SAPI TTS 离线合成），`samples/reference.txt` 为人工参考文本。

## 8. 部署与启动

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问 `http://127.0.0.1:8000`。首次识别时自动下载模型权重（联网一次），之后可离线运行。
