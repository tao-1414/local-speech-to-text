# 测试报告

## 1. 测试环境

| 项目 | 值 |
| ---- | ---- |
| 操作系统 | Windows 11 x64 |
| Python | 3.12.7（Anaconda） |
| 依赖 | fastapi 0.162.0、faster-whisper 1.2.1、av 13.1.0、pytest 9.2.0 |
| ASR 模型 | Systran/faster-whisper-small（CPU / int8） |

## 2. 自动化测试（Mock）

统一命令：

```bash
python -m pytest -q
```

结果：`16 passed, 2 skipped`（2 个真实模型测试默认跳过）。

| 用例 | 覆盖范围 | 结果 |
| ---- | -------- | ---- |
| `test_health::test_health` | 健康检查返回 200 与 `{"status":"ok"}` | 通过 |
| `test_health::test_index_page` | 首页返回 200 且包含页面标题 | 通过 |
| `test_transcribe::test_transcribe_zh` | 中文正常识别（Mock） | 通过 |
| `test_transcribe::test_transcribe_default_language_is_zh` | 缺省语言为 zh | 通过 |
| `test_transcribe::test_transcribe_en` | 英文正常识别（Mock） | 通过 |
| `test_language::test_language_zh` | 合法语言 zh | 通过 |
| `test_language::test_language_en` | 合法语言 en | 通过 |
| `test_language::test_language_invalid` | 非法语言返回 400 | 通过 |
| `test_audio_validation::test_empty_file` | 空文件返回 400 | 通过 |
| `test_audio_validation::test_corrupt_file` | 损坏文件返回 400 | 通过 |
| `test_audio_validation::test_oversize_file` | 超过 10MB 返回 413 | 通过 |
| `test_audio_validation::test_silence_returns_empty_text` | 静音返回 200 且文本为空、`audio_rms` 低于阈值 | 通过 |
| `test_errors::test_model_load_failure` | 模型加载失败返回 503 | 通过 |
| `test_errors::test_inference_failure` | 推理失败返回 500 | 通过 |
| `test_asr_service::test_empty_audio_returns_empty` | 空音频返回空文本 | 通过 |
| `test_asr_service::test_silence_returns_empty_without_loading_model` | 静音返回空且不加载模型（防幻觉） | 通过 |

## 3. 真实模型测试

执行方式：

```bash
# Windows PowerShell
$env:RUN_REAL_MODEL="1"; $env:HF_ENDPOINT="https://hf-mirror.com"
python -m pytest tests/test_real_model.py -q
```

结果：`2 passed`（首次自动下载 `small` 模型，耗时约 4 分钟）。

### 3.1 实际识别结果

| 样本 | 语言 | 音频时长 | 处理耗时 | 识别文本 |
| ---- | ---- | -------- | -------- | -------- |
| chinese.wav | zh | 4.03 s | 6.28 s | 你好,欢迎使用语音识别系统。 |
| english.wav | en | 3.76 s | 2.22 s | Hello, welcome to the speech recognition system. |

- 英文识别与参考文本完全一致。
- 中文识别与参考文本一致（仅标点由中文全角逗号转为了半角逗号，属 Whisper 常见行为，不影响语义）。

## 4. 手动验证清单

| 项 | 内容 | 状态 |
| -- | ---- | ---- |
| 1 | 浏览器麦克风录制中文并识别 | 待手动验证（需真实浏览器） |
| 2 | 浏览器麦克风录制英文并识别 | 待手动验证 |
| 3 | 上传中文 WAV 并识别 | 已通过真实模型测试覆盖 |
| 4 | 上传英文 WAV 并识别 | 已通过真实模型测试覆盖 |
| 5 | 麦克风权限被拒绝时的表现 | 前端已处理，待手动验证 |
| 6 | 无外网情况下的识别 | 模型缓存后离线推理（已具备） |

## 5. 问题修复记录

### 5.1 静音幻觉（字幕by索兰娅）

- **现象**：录音识别返回「字幕by索兰娅」等无关文本。
- **原因**：Whisper 在静音 / 无有效语音音频上的典型幻觉。
- **处理**：
  1. **静音预检**：RMS < `SILENCE_RMS_THRESHOLD`（默认 `1e-4`）直接返回空文本，不加载模型；
  2. **VAD 过滤**：启用 faster-whisper 自带 `silero_vad_v6.onnx`（离线可用）过滤非语音；
  3. **片段过滤**：跳过 `no_speech_prob > 0.6 且 avg_logprob < -1.0` 的片段；
  4. **诊断增强**：响应新增 `audio_rms`，后端日志打印时长/RMS，便于定位麦克风问题。
- **验证**：静音样本返回空文本（`test_silence_returns_empty_text` 等用例通过）；中英文样本仍能正确识别。

### 5.2 WebM/Opus 解码往返验证

- 使用 `av` 将 `english.wav` 编码为 WebM/Opus 再解码，RMS `0.0833 → 0.0811`、时长一致，
  证明后端对浏览器录音格式的解码链路正常。

## 6. 已知问题

1. **av 版本约束**：`faster-whisper 1.2.1` 依赖 `av>=11`，但 `av>=14` 移除了 `av.open(metadata_errors=...)` 参数，会导致解码报错。已在 `requirements.txt` 中固定 `av>=11,<14`。
2. **中文标点**：Whisper 输出中文时会把全角标点转换为半角（如 `，`→`,`），属模型行为，不影响识别内容。
3. **Windows 符号链接警告**：HuggingFace 缓存在未启用开发者模式的 Windows 上使用降级缓存，仅产生警告，不影响功能。
4. **WebM/Opus 实时识别**：后端解码链路支持 WebM/Opus，但实时分片流程尚未在真实浏览器中端到端验证（需手动验证）。
5. **首次下载模型需联网**：模型权重约 461MB（small），首次调用需联网；之后可离线运行。
