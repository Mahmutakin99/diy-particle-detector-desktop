import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from particle_detector.app import MainWindow
from particle_detector.model import Pulse, Recording
from particle_detector.storage import save_pdet


def test_desktop_has_live_and_analysis_visualizations():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.live_plot is not None
    assert window.spectrum_plot is not None
    assert window.records_list is not None
    window.close()


def test_open_recording_shows_pulse_count_and_spectrum(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "sample.pdet"
    save_pdet(path, Recording("electron", 48000, "2026-09-24T00:00:00Z", [Pulse(1000, -800, [0, -800, 0])]))
    window = MainWindow()
    window.open_recording(path)
    assert "1 pulses" in window.records_status.text()
    assert window.records_list.count() == 1
    assert len(window.spectrum_curve.xData) > 0
    window.close()


def test_packaged_entrypoint_smoke_opens_sample_recording(tmp_path):
    path = tmp_path / "sample.pdet"
    result_path = tmp_path / "smoke-result.txt"
    save_pdet(path, Recording("alpha", 48000, "2026-09-24T00:00:00Z", [Pulse(1000, -950, [0, -950, 0])]))
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PDET_SMOKE_RECORDING": str(path), "PDET_SMOKE_OUTPUT": str(result_path)}
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "desktop_app.py")],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result_path.read_text() == "pulses=1 profile=alpha\n"
