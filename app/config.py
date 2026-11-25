"""应用配置。"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# ASR 模型配置
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")
DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
MODEL_CACHE_DIR = os.environ.get("WHISPER_CACHE_DIR") or None

# 音频采样率（faster-whisper 统一使用 16kHz）
SAMPLE_RATE = 16000

# 静音判定：RMS 低于该阈值视为数字静音，直接返回空结果（避免模型幻觉）。
# 仅用于极端静音，正常/轻声说话由 VAD 判定，避免误杀。可用环境变量覆盖。
SILENCE_RMS_THRESHOLD = float(os.environ.get("SILENCE_RMS_THRESHOLD", "1e-4"))

# 是否启用 VAD 过滤（跳过非语音片段，防止幻觉）。可用 WHISPER_VAD=0 关闭以排查。
VAD_ENABLED = os.environ.get("WHISPER_VAD", "1") not in ("0", "false", "False")

# 请求限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
SUPPORTED_LANGUAGES = {"zh", "en"}

# 语言显示名
LANGUAGE_LABELS = {"zh": "中文", "en": "英语"}
