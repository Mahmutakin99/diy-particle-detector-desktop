"""Audio capture isolated from the UI and disk writer."""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

import numpy as np

from .model import Recording, now_iso
from .signal import PulseDetector
from .storage import save_pdet


def friendly_audio_error(error: Exception) -> str:
    message = str(error).lower()
    if isinstance(error, PermissionError) or "permission" in message or "denied" in message:
        return "permission"
    if "sample rate" in message or "samplerate" in message:
        return "sample_rate"
    if "device" in message or "input" in message:
        return "device"
    return "connection"


class CaptureService(threading.Thread):
    """Consumes audio blocks off the callback thread and writes a .pdet on stop."""

    def __init__(self, profile: str, sample_rate: int, threshold: float, destination: Path, *, filter_enabled=True, queue_size=64):
        super().__init__(daemon=True)
        self.profile, self.sample_rate, self.destination = profile, sample_rate, Path(destination)
        self.detector = PulseDetector(profile, sample_rate, threshold=threshold, filter_enabled=filter_enabled)
        self.blocks: queue.Queue[tuple[np.ndarray, int] | None] = queue.Queue(queue_size)
        self.recording = Recording(profile, sample_rate, now_iso())
        self.dropped_samples = 0
        self.error: Exception | None = None
        self.save_error = False
        self.latest_signal = np.array([], dtype=np.float32)
        self._stream = None
        self.started_monotonic: float | None = None

    def start(self, *, use_audio=True, device=None):
        if use_audio:
            try:
                import sounddevice as sd
                self._stream = sd.InputStream(
                    device=device, channels=1, samplerate=self.sample_rate, dtype="float32",
                    callback=self._callback,
                )
                self._stream.start()
            except Exception as error:
                self.error = error
                raise
        self.started_monotonic = time.monotonic()
        super().start()

    def _callback(self, indata, frames, time_info, status):
        if status:
            self.error = RuntimeError(str(status))
        timestamp_us = int(time_info.inputBufferAdcTime * 1_000_000)
        self.submit(indata[:, 0], timestamp_us)

    def submit(self, samples, start_us: int):
        block = (np.asarray(samples, dtype=np.float32).copy(), start_us)
        try:
            self.blocks.put_nowait(block)
        except queue.Full:
            self.dropped_samples += len(block[0])

    def run(self):
        while True:
            block = self.blocks.get()
            if block is None:
                break
            samples, start_us = block
            self.latest_signal = samples
            self.recording.pulses.extend(self.detector.process(samples, start_us))
        self.recording.lost_samples = self.detector.lost_samples + self.dropped_samples
        try:
            save_pdet(self.destination, self.recording)
        except Exception as error:
            self.error = error
            self.save_error = True

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.blocks.put(None)
