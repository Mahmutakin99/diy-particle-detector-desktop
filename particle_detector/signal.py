"""Sample based detection, independent of audio capture and the user interface."""

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, find_peaks, sosfilt

from .model import Pulse


@dataclass(frozen=True)
class Profile:
    threshold: float
    low_hz: float
    high_hz: float
    dead_time_ms: float
    window_samples: int


PROFILES = {
    "electron": Profile(-800, 1000, 12000, 2, 256),
    "alpha": Profile(-300, 80, 12000, 2, 2048),
}


class PulseDetector:
    def __init__(self, profile: str, sample_rate: int, *, threshold: float | None = None, filter_enabled: bool = True):
        self.profile = PROFILES[profile]
        self.sample_rate = sample_rate
        self.threshold = self.profile.threshold if threshold is None else threshold
        self.dead_samples = max(1, round(self.profile.dead_time_ms * sample_rate / 1000))
        self.sample_index = 0
        self.last_pulse_index = -self.dead_samples - 1
        self.last_end_us = None
        self.lost_samples = 0
        self.filter_enabled = filter_enabled
        high = min(self.profile.high_hz, sample_rate * 0.45)
        low = min(self.profile.low_hz, high * 0.5)
        self.sos = butter(3, [low, high], btype="bandpass", fs=sample_rate, output="sos")
        self.zi = np.zeros((len(self.sos), 2))
        self.tail_filtered = np.zeros(1)
        self.tail_raw = np.zeros(1)

    def process(self, samples, start_us: int) -> list[Pulse]:
        raw = np.asarray(samples, dtype=np.float64)
        if self.last_end_us is not None:
            gap = start_us - self.last_end_us
            if gap > 1_000_000 / self.sample_rate:
                self.lost_samples += max(0, round(gap * self.sample_rate / 1_000_000))
        self.last_end_us = start_us + round(len(raw) * 1_000_000 / self.sample_rate)
        filtered, self.zi = sosfilt(self.sos, raw, zi=self.zi) if self.filter_enabled else (raw, self.zi)
        combined = np.concatenate((self.tail_filtered, filtered))
        events = []
        peaks, _ = find_peaks(-combined, height=abs(self.threshold))
        for index in peaks:
            if index == 0:
                continue
            offset = index - 1
            absolute = self.sample_index + offset
            if absolute - self.last_pulse_index <= self.dead_samples:
                continue
            self.last_pulse_index = absolute
            half = min(self.profile.window_samples // 2, 128)
            waveform = raw[max(0, offset - half):min(len(raw), offset + half)].tolist()
            events.append(Pulse(start_us + round(offset * 1_000_000 / self.sample_rate), float(raw[offset]), waveform))
        if len(filtered):
            self.tail_filtered = filtered[-1:]
            self.tail_raw = raw[-1:]
        self.sample_index += len(raw)
        return events
