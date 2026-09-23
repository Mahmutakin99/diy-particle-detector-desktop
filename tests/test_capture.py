import time

import numpy as np

from particle_detector.capture import CaptureService, friendly_audio_error
from particle_detector.storage import load_recording


def test_capture_runs_in_worker_and_saves_session(tmp_path):
    destination = tmp_path / "test.pdet"
    service = CaptureService("electron", 48000, -200, destination, filter_enabled=False)
    service.start(use_audio=False)
    samples = np.zeros(800, dtype=np.float32)
    samples[200:205] = [-100, -400, -800, -400, -100]
    service.submit(samples, 0)
    service.stop()
    service.join(timeout=5)
    assert not service.is_alive()
    assert load_recording(destination).pulses[0].peak == -800


def test_capture_overflow_counts_lost_samples(tmp_path):
    service = CaptureService("electron", 48000, -200, tmp_path / "test.pdet", filter_enabled=False, queue_size=1)
    service.submit(np.zeros(128), 0)
    service.submit(np.zeros(128), 3000)
    assert service.dropped_samples == 128


def test_audio_error_categories():
    assert friendly_audio_error(PermissionError("denied")) == "permission"
    assert friendly_audio_error(RuntimeError("Invalid device")) == "device"
    assert friendly_audio_error(RuntimeError("Invalid sample rate")) == "sample_rate"


def test_capture_reports_save_error(tmp_path):
    service = CaptureService("electron", 48000, -200, tmp_path, filter_enabled=False)
    service.start(use_audio=False)
    service.stop()
    service.join(timeout=5)
    assert service.error is not None
    assert service.save_error
