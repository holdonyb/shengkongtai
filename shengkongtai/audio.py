"""有界录音缓存，PortAudio 回调不操作 Tk 或运行识别。"""
from __future__ import annotations

import threading


class Recorder:
    def __init__(self, device=None, max_seconds: int = 60):
        self.device = device
        self.max_seconds = max_seconds
        self.stream = None
        self.lock = threading.Lock()
        self.frames = []
        self.count = 0
        self.limit_reached = False
        self.error = ""
        self.sample_rate = 16000

    def start(self):
        import sounddevice as sd
        self.frames = []
        self.count = 0
        self.error = ""
        self.limit_reached = False
        # 采用设备默认采样率，识别入口统一重采样至 16kHz。
        self.sample_rate = int(sd.query_devices(self.device, "input")["default_samplerate"])
        self.stream = sd.InputStream(device=self.device, samplerate=self.sample_rate,
                                     channels=1, dtype="float32", callback=self._callback)
        try:
            self.stream.start()
        except Exception:
            self.stream.close()
            self.stream = None
            raise

    def _callback(self, data, frames, timing, status):
        with self.lock:
            if status:
                self.error = str(status)
            remaining = max(0, self.max_seconds * self.sample_rate - self.count)
            take = min(frames, remaining)
            if take:
                self.frames.append(data[:take, 0].copy())
                self.count += take
            if self.count >= self.max_seconds * self.sample_rate:
                self.limit_reached = True

    def stop(self):
        import numpy as np
        stream, self.stream = self.stream, None
        if stream:
            try:
                stream.stop()
            finally:
                stream.close()
        with self.lock:
            samples = np.concatenate(self.frames) if self.frames else np.empty(0, dtype=np.float32)
            self.frames = []
        return samples, self.sample_rate
