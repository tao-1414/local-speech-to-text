(() => {
  "use strict";

  const MAX_RECORD_SECONDS = 60;
  const REALTIME_SLICE_MS = 3000;

  const startBtn = document.getElementById("startBtn");
  const stopBtn = document.getElementById("stopBtn");
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const durationText = document.getElementById("durationText");
  const fileInput = document.getElementById("fileInput");
  const realtimeCheck = document.getElementById("realtimeCheck");
  const resultBox = document.getElementById("resultBox");
  const resultPlaceholder = document.getElementById("resultPlaceholder");
  const resultText = document.getElementById("resultText");
  const resultMeta = document.getElementById("resultMeta");
  const copyBtn = document.getElementById("copyBtn");

  let mediaRecorder = null;
  let stream = null;
  let recordedChunks = [];
  let recordTimer = null;
  let limitTimer = null;
  let recordStartTime = 0;
  let partialSerial = 0;

  function getLanguage() {
    const selected = document.querySelector('input[name="language"]:checked');
    return selected ? selected.value : "zh";
  }

  function setStatus(state, text) {
    statusDot.className = "status-dot " + state;
    statusText.textContent = text;
  }

  function formatDuration(seconds) {
    const s = Math.floor(seconds);
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    return `${mm}:${ss}`;
  }

  function updateDuration() {
    const elapsed = (Date.now() - recordStartTime) / 1000;
    durationText.textContent = formatDuration(elapsed);
  }

  function showResult(text, duration, processing) {
    if (text) {
      resultPlaceholder.style.display = "none";
      resultText.textContent = text;
      resultText.style.display = "block";
    } else {
      resultPlaceholder.style.display = "block";
      resultPlaceholder.textContent = "（未识别到语音内容，请确认麦克风正常并靠近说话）";
      resultText.style.display = "none";
      resultText.textContent = "";
    }
    resultMeta.textContent =
      `语言：${getLanguage() === "zh" ? "中文" : "英语"}  ·  ` +
      `音频时长：${duration != null ? duration + " s" : "—"}  ·  ` +
      `处理耗时：${processing != null ? processing + " s" : "—"}`;
    copyBtn.disabled = !text;
  }

  function showError(message) {
    setStatus("error", "出错");
    resultPlaceholder.style.display = "block";
    resultPlaceholder.textContent = "⚠ " + message;
    resultText.style.display = "none";
    resultText.textContent = "";
    resultMeta.textContent = "";
    copyBtn.disabled = true;
  }

  async function transcribe(blob, { partial = false } = {}) {
    if (!blob || blob.size === 0) return;
    const form = new FormData();
    form.append("file", blob, "audio.webm");
    form.append("language", getLanguage());

    if (!partial) setStatus("transcribing", "识别中...");
    copyBtn.disabled = true;

    try {
      const resp = await fetch("/api/transcribe", { method: "POST", body: form });
      if (!resp.ok) {
        let detail = "请求失败";
        try {
          const body = await resp.json();
          detail = body.detail || detail;
        } catch (_) {
          /* ignore */
        }
        throw new Error(detail);
      }
      const data = await resp.json();
      if (!partial || data.text) {
        showResult(data.text, data.duration_seconds, data.processing_seconds);
      }
      setStatus("done", "识别完成");
      return data;
    } catch (err) {
      if (!partial) showError(err.message || String(err));
      throw err;
    }
  }

  async function startRecording() {
    realtimeCheck.disabled = true;
    recordedChunks = [];
    partialSerial += 1;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showError("当前浏览器不支持麦克风录音，请使用最新版 Chrome 或 Edge。");
      realtimeCheck.disabled = false;
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      realtimeCheck.disabled = false;
      if (err && (err.name === "NotAllowedError" || err.name === "SecurityError")) {
        showError("麦克风权限被拒绝，请在浏览器地址栏允许访问麦克风后重试。");
      } else if (err && err.name === "NotFoundError") {
        showError("未检测到可用麦克风，请检查设备后重试。");
      } else {
        showError("无法访问麦克风：" + (err && err.message ? err.message : err));
      }
      return;
    }

    const mimeType = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "",
    ].find((t) => !t || MediaRecorder.isTypeSupported(t));

    const realtime = realtimeCheck.checked;
    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
        if (realtime && !mediaRecorder.requestingStop) {
          const cumulative = new Blob(recordedChunks, { type: mimeType || "audio/webm" });
          const mySerial = partialSerial;
          transcribe(cumulative, { partial: true })
            .then(() => {
              if (mySerial === partialSerial) setStatus("recording", "录音中（实时识别）");
            })
            .catch(() => {});
        }
      }
    };

    mediaRecorder.onstop = async () => {
      const isManualStop = mediaRecorder.requestingStop !== false;
      durationText.textContent = formatDuration((Date.now() - recordStartTime) / 1000);
      stream && stream.getTracks().forEach((t) => t.stop());
      stream = null;

      const blob = new Blob(recordedChunks, { type: mimeType || "audio/webm" });
      const lastSerial = partialSerial;
      try {
        await transcribe(blob, { partial: realtime });
        if (lastSerial === partialSerial) {
          setStatus("done", "识别完成");
        }
      } catch (_) {
        /* error already shown */
      }
      resetControls();
    };

    mediaRecorder.start(realtime ? REALTIME_SLICE_MS : undefined);
    recordStartTime = Date.now();
    startBtn.disabled = true;
    stopBtn.disabled = false;
    setStatus("recording", realtime ? "录音中（实时识别）" : "录音中...");
    updateDuration();
    recordTimer = setInterval(updateDuration, 250);

    limitTimer = setTimeout(() => {
      if (mediaRecorder && mediaRecorder.state === "recording") {
        setStatus("recording", "已达 60 秒上限，自动停止");
        stopRecording();
      }
    }, MAX_RECORD_SECONDS * 1000);
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.requestingStop = true;
      mediaRecorder.stop();
    }
    if (limitTimer) { clearTimeout(limitTimer); limitTimer = null; }
    if (recordTimer) { clearInterval(recordTimer); recordTimer = null; }
  }

  function resetControls() {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    realtimeCheck.disabled = false;
  }

  startBtn.addEventListener("click", startRecording);
  stopBtn.addEventListener("click", stopRecording);

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    try {
      await transcribe(file, { partial: false });
      setStatus("done", "识别完成");
    } catch (_) {
      /* error already shown */
    } finally {
      fileInput.value = "";
    }
  });

  copyBtn.addEventListener("click", async () => {
    const text = resultText.textContent;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "已复制";
      setTimeout(() => { copyBtn.textContent = "复制文字"; }, 1500);
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      copyBtn.textContent = "已复制";
      setTimeout(() => { copyBtn.textContent = "复制文字"; }, 1500);
    }
  });

  setStatus("idle", "就绪");
})();
