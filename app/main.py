"""FastAPI 应用入口。"""
from __future__ import annotations

import time
import logging

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from . import config
from .asr import ASRService, ModelLoadError
from .audio import AudioDecodeError, EmptyAudioError, load_audio, rms

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Local AI Speech-to-Text", version="1.0.0")

_asr_service: ASRService | None = None


def get_asr_service() -> ASRService:
    """返回 ASR 服务单例（懒加载，测试中可覆盖）。"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService.from_config()
    return _asr_service


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("zh"),
    service: ASRService = Depends(get_asr_service),
) -> dict:
    if language not in config.SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="language 参数仅支持 'zh' 或 'en'")

    data = await file.read()

    if len(data) == 0:
        raise HTTPException(status_code=400, detail="上传的音频文件为空")
    if len(data) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过 {config.MAX_FILE_SIZE // (1024 * 1024)} MB 上限",
        )

    started = time.perf_counter()

    try:
        audio, duration = load_audio(data, file.filename or "")
    except EmptyAudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AudioDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audio_rms = rms(audio)
    try:
        text = service.transcribe(audio, language)
    except ModelLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"语音识别失败: {exc}") from exc

    processing = time.perf_counter() - started

    log = (
        "[transcribe] lang=%s file=%s bytes=%d duration=%.2fs rms=%.5f "
        "text_len=%d processing=%.2fs"
    )
    args = (
        language,
        file.filename or "",
        len(data),
        duration,
        audio_rms,
        len(text),
        processing,
    )
    if not text:
        logger.warning(log + "  <- 无有效语音（音量过低或麦克风未采集到声音）", *args)
    else:
        logger.info(log, *args)

    return {
        "text": text,
        "language": language,
        "duration_seconds": round(duration, 2),
        "processing_seconds": round(processing, 3),
        "audio_rms": round(audio_rms, 5),
    }


app.mount("/", StaticFiles(directory=str(config.STATIC_DIR), html=True), name="static")
