# AI 开发过程记录（OpenCode）

本文记录使用 OpenCode 完成「Local AI Speech-to-Text Web Application」的过程，涵盖需求理解、功能开发、测试与问题修复三个阶段。

## 阶段一：需求理解与技术设计

**OpenCode 承担的任务**：

- 阅读考核文档，提炼并结构化功能需求（F1–F6）、接口要求、技术约束与测试要求。
- 输出 `docs/requirements.md`（需求理解、功能拆分、必要假设与边界条件）。
- 输出 `docs/design.md`（系统架构、模块划分、音频处理流程、模型选型）。

**重要技术决策（由我做出）**：

1. **ASR 模型选型**：在 faster-whisper / openai-whisper / Vosk / FunASR 中选择了 **faster-whisper（small）**，理由是中英文原生支持、CPU int8 推理快、纯 Python 且内存占用可控。
2. **音频解码复用 PyAV**：复用 faster-whisper 自带的 `decode_audio`（基于 PyAV），无需 ffmpeg，可同时解码 WAV 与浏览器 WebM/Opus。
3. **模型懒加载 + 依赖注入**：模型延迟到首次识别时加载，且通过 FastAPI 依赖注入暴露，使 Mock 测试不触发模型下载。

## 阶段二：功能开发与集成

**OpenCode 承担的任务**：

- 实现后端 `app/`：`config.py`（配置）、`audio.py`（校验与解码）、`asr.py`（模型封装）、`main.py`（路由与静态托管）。
- 实现前端 `static/`：录音（含 60 秒上限、状态/时长显示）、语言选择、文件上传、结果展示与复制、异常提示、可选实时识别。
- 生成测试音频样本：使用 Windows SAPI TTS（Huihui 中文、Zira 英文）离线合成 `samples/` 下的 WAV 与 `reference.txt`。
- 编写 pytest 测试：健康检查、正常/非法请求、音频校验、语言参数、错误处理、真实模型测试。

## 阶段三：测试与问题修复

**遇到的问题与 AI 辅助解决过程**：

1. **问题**：`python -m pytest` 时全部识别用例返回 400。
   **定位**：直接调用 `load_audio` 复现，发现报错 `av.open() got an unexpected keyword argument 'metadata_errors'`。
   **原因**：pip 解析出 `av==19.0.2`，而该版本移除了 `metadata_errors` 参数，与 `faster-whisper 1.2.1` 不兼容。
   **解决**：固定 `av>=11,<14`（实测 `av==13.1.0` 通过），并写入 `requirements.txt`，保证可复现。

2. **问题**：真实模型测试本应默认跳过，却因 `samples/chinese.wav` 存在而意外执行。
   **解决**：将 `skipif` 条件简化为仅在 `RUN_REAL_MODEL=1` 时运行。

3. **问题**：真实模型下载在受网络限制环境下可能失败。
   **解决**：验证时设置 `HF_ENDPOINT=https://hf-mirror.com` 镜像，并在 README 中说明。

4. **问题**：录音识别出现「字幕by索兰娅」等无关文本。
   **定位**：先用 WebM/Opus 往返测试（`english.wav` 编码为 WebM 再解码，RMS 从 0.0833 到 0.0811、时长一致）排除后端解码问题，判定为 Whisper 在静音/无语音音频上的幻觉。
   **解决**：加入静音预检（RMS 阈值）+ VAD 过滤 + 高 `no_speech_prob` 片段过滤；响应新增 `audio_rms`、后端日志打印时长与音量，便于区分「麦克风没采集到声音」与「模型问题」。

**如何确认 AI 生成的代码满足业务需求**：

- 运行 Mock 测试（16 通过），验证接口、参数校验、异常处理符合需求。
- 运行真实模型测试（2 通过），用 samples 音频验证中英文识别，英文结果与参考完全一致，中文结果仅标点差异。
- 通过 `load_audio` 校验样本可解码、时长正确；通过 WebM/Opus 往返测试验证浏览器录音格式解码正常。

## 7.3 要求要点回答

- **OpenCode 在开发中承担了哪些任务？**
  需求拆解与文档撰写、架构与模块设计、前后端代码生成、测试音频合成、pytest 用例编写、缺陷定位与修复建议，以及 README 等交付文档补全。

- **哪些重要技术决策由自己做出？**
  ASR 选型 faster-whisper（CPU/int8）；复用 PyAV 解码以支持 WAV 与浏览器 WebM/Opus；模型懒加载 + FastAPI 依赖注入以支持 Mock 测试；`av` 版本固定为 `<14`；采用静音预检 + VAD 规避幻觉。

- **遇到过什么问题，如何借助 AI 解决？**
  ① `av>=14` 与 faster-whisper 不兼容导致全部识别 400 —— 通过复现报错、定位 `metadata_errors` 参数移除并固定 `av<14`；② 真实模型测试误执行 —— 修正 `skipif` 条件；③ 模型下载受网络限制 —— 使用 `HF_ENDPOINT` 镜像；④ 静音幻觉「字幕by索兰娅」—— 通过往返测试排除解码问题后，加入静音预检与 VAD。

- **如何确认 AI 生成的代码满足业务需求？**
  以需求文档为基线，逐项对照接口与异常行为；运行 Mock 测试（16 通过）与真实模型测试（2 通过）；用 samples 比对识别文本；用往返测试验证浏览器录音格式解码。

- **如果继续优化系统，会优先改进什么？**
  引入流式/分片增量推理降低实时识别延迟；增加更细的 VAD 与重试策略；补充 Playwright 端到端录音测试；提供模型预热以减少首次识别等待。

## 关键经验与后续优化

- OpenCode 在本项目中承担了需求拆解、架构设计、代码生成、样本生成、测试编写与问题定位的绝大部分工作；模型选型、接口设计等关键决策由我确认。
- 若继续优化，优先方向：
  1. 引入流式推理（如 chunked + 部分结果合并）以降低实时识别延迟；
  2. 增加 VAD（静音检测）以过滤无语音片段、避免空转；
  3. 增加浏览器端到端自动化测试（Playwright）覆盖录音流程。

![image-20261104114329360](C:\Users\TAO\AppData\Roaming\Typora\typora-user-images\image-20261104114329360.png)

![image-20261104114350218](C:\Users\TAO\AppData\Roaming\Typora\typora-user-images\image-20261104114350218.png)
