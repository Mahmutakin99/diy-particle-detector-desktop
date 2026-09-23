"""PySide6 desktop application. Run with: python -m particle_detector.app"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PySide6 import QtCore, QtWidgets
import numpy as np
import pyqtgraph as pg

from .capture import CaptureService, friendly_audio_error
from .i18n import MESSAGES, system_language
from .model import Calibration, default_data_dir
from .signal import PROFILES
from .storage import load_recording


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = system_language()
        self.service = None
        self.calibration = None
        self.setMinimumSize(850, 580)
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_live()
        self._build_records()
        self._build_analysis()
        self._build_settings()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(300)
        self.translate()

    def t(self, key): return MESSAGES[self.language][key]

    def _build_live(self):
        page = QtWidgets.QWidget(); layout = QtWidgets.QVBoxLayout(page); form = QtWidgets.QFormLayout()
        self.profile = QtWidgets.QComboBox(); self.profile.addItems(["electron", "alpha"])
        self.device = QtWidgets.QComboBox(); self.device.addItem("Default")
        try:
            import sounddevice as sd
            self.device.addItems([str(d["name"]) for d in sd.query_devices() if d["max_input_channels"]])
        except Exception:
            pass
        self.threshold = QtWidgets.QSpinBox(); self.threshold.setRange(-32000, -1); self.threshold.setValue(PROFILES["electron"].threshold)
        self.profile.currentTextChanged.connect(lambda p: self.threshold.setValue(PROFILES[p].threshold))
        self.start = QtWidgets.QPushButton(); self.start.clicked.connect(self.start_capture)
        self.stop = QtWidgets.QPushButton(); self.stop.clicked.connect(self.stop_capture); self.stop.setEnabled(False)
        self.status = QtWidgets.QLabel(); self.status.setWordWrap(True)
        self.rate = QtWidgets.QLabel("0 CPS"); self.rate.setAccessibleName("Count rate")
        self.amplitude = QtWidgets.QLabel("—"); self.amplitude.setAccessibleName("Pulse amplitude")
        self.axis = QtWidgets.QLabel(); self.axis.setWordWrap(True)
        form.addRow("profile", self.profile); form.addRow("device", self.device); form.addRow("threshold", self.threshold)
        form.addRow(self.start, self.stop); form.addRow(self.status); form.addRow("rate", self.rate); form.addRow("amplitude", self.amplitude); form.addRow(self.axis)
        self.live_plot = pg.PlotWidget(title="Live waveform")
        self.live_plot.setLabel("left", "Amplitude")
        self.live_plot.setLabel("bottom", "Samples")
        self.live_curve = self.live_plot.plot(pen=pg.mkPen("#0071e3", width=1))
        layout.addLayout(form); layout.addWidget(self.live_plot)
        self.tabs.addTab(page, "")

    def _build_records(self):
        page = QtWidgets.QWidget(); layout = QtWidgets.QVBoxLayout(page)
        self.import_button = QtWidgets.QPushButton(); self.import_button.clicked.connect(self.import_recording)
        self.records_status = QtWidgets.QLabel(); self.records_status.setWordWrap(True)
        self.records_list = QtWidgets.QListWidget()
        layout.addWidget(self.import_button); layout.addWidget(self.records_status); layout.addWidget(self.records_list)
        self.tabs.addTab(page, "")

    def _build_analysis(self):
        page = QtWidgets.QWidget(); layout = QtWidgets.QVBoxLayout(page)
        self.analysis_status = QtWidgets.QLabel(); self.analysis_status.setWordWrap(True)
        self.spectrum_plot = pg.PlotWidget(title="Pulse amplitude spectrum")
        self.spectrum_plot.setLabel("left", "Counts")
        self.spectrum_plot.setLabel("bottom", "Amplitude")
        self.spectrum_curve = self.spectrum_plot.plot(stepMode="center", fillLevel=0, brush=(0, 113, 227, 80))
        layout.addWidget(self.analysis_status); layout.addWidget(self.spectrum_plot); self.tabs.addTab(page, "")

    def _build_settings(self):
        page = QtWidgets.QWidget(); form = QtWidgets.QFormLayout(page)
        self.language_box = QtWidgets.QComboBox(); self.language_box.addItem("Türkçe", "tr"); self.language_box.addItem("English", "en")
        self.language_box.currentIndexChanged.connect(self.change_language)
        self.appearance = QtWidgets.QComboBox(); self.appearance.addItems(["System", "Light", "Dark"]); self.appearance.currentTextChanged.connect(self.change_theme)
        self.reference_amplitudes = [QtWidgets.QDoubleSpinBox(), QtWidgets.QDoubleSpinBox()]
        self.reference_energies = [QtWidgets.QDoubleSpinBox(), QtWidgets.QDoubleSpinBox()]
        for field in self.reference_amplitudes + self.reference_energies:
            field.setRange(0.01, 1_000_000); field.setDecimals(2)
        self.reference_amplitudes[0].setValue(1000); self.reference_energies[0].setValue(1000)
        self.reference_amplitudes[1].setValue(2000); self.reference_energies[1].setValue(2000)
        self.calibrate = QtWidgets.QPushButton(); self.calibrate.clicked.connect(self.apply_calibration)
        self.calibration_status = QtWidgets.QLabel(); self.calibration_status.setWordWrap(True)
        form.addRow("language", self.language_box); form.addRow("appearance", self.appearance)
        form.addRow("reference 1 (amplitude, keV)", self._pair_widget(0)); form.addRow("reference 2 (amplitude, keV)", self._pair_widget(1))
        form.addRow(self.calibrate); form.addRow(self.calibration_status); self.tabs.addTab(page, "")

    def _pair_widget(self, index):
        widget = QtWidgets.QWidget(); layout = QtWidgets.QHBoxLayout(widget); layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.reference_amplitudes[index]); layout.addWidget(QtWidgets.QLabel("→")); layout.addWidget(self.reference_energies[index]); return widget

    def translate(self):
        self.setWindowTitle(self.t("app")); self.tabs.setTabText(0, self.t("live")); self.tabs.setTabText(1, self.t("records")); self.tabs.setTabText(2, self.t("analysis")); self.tabs.setTabText(3, self.t("settings"))
        self.start.setText(self.t("start")); self.stop.setText(self.t("stop")); self.import_button.setText(self.t("choose_file")); self.calibrate.setText(self.t("add_reference"))
        if self.calibration is None:
            self.axis.setText(self.t("uncalibrated")); self.analysis_status.setText(self.t("no_calibration"))
        else:
            self.axis.setText(self.t("energy_axis")); self.analysis_status.setText(self.t("energy_axis"))

    def change_language(self): self.language = self.language_box.currentData(); self.translate()

    def change_theme(self, theme):
        app = QtWidgets.QApplication.instance()
        if theme == "Dark": app.setStyleSheet("QWidget { background:#1e1e1e; color:#f4f4f4; } QPushButton { padding: 8px; }")
        elif theme == "Light": app.setStyleSheet("QPushButton { padding: 8px; }")
        else: app.setStyleSheet("")

    def apply_calibration(self):
        try:
            self.calibration = Calibration([(self.reference_amplitudes[0].value(), self.reference_energies[0].value()), (self.reference_amplitudes[1].value(), self.reference_energies[1].value())])
            self.calibration_status.setText(self.t("energy_axis")); self.translate()
        except ValueError as error:
            self.calibration = None; self.calibration_status.setText(str(error)); self.translate()

    def start_capture(self):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = default_data_dir() / f"recording-{stamp}.pdet"
        self.service = CaptureService(self.profile.currentText(), 48000, self.threshold.value(), path)
        self.service.recording.calibration = self.calibration
        try:
            device = None if self.device.currentIndex() == 0 else self.device.currentText()
            self.service.start(device=device)
        except Exception as error:
            self.status.setText(self.t("audio_" + friendly_audio_error(error)))
            self.service = None; return
        self.start.setEnabled(False); self.stop.setEnabled(True); self.status.setText(path.as_posix())

    def stop_capture(self):
        if not self.service: return
        self.service.stop(); self.service.join(timeout=5)
        if self.service.error:
            self.status.setText(self.t("save_error") if self.service.save_error else self.t("audio_" + friendly_audio_error(self.service.error)))
        else:
            self.records_list.addItem(str(self.service.destination))
        self.start.setEnabled(True); self.stop.setEnabled(False); self.service = None

    def _refresh(self):
        if not self.service: return
        pulses = self.service.recording.pulses
        elapsed = max(0.3, time.monotonic() - (self.service.started_monotonic or time.monotonic()))
        self.rate.setText(f"{len(pulses) / elapsed:.2f} CPS")
        if pulses: self.amplitude.setText(f"{pulses[-1].peak:.0f}")
        if self.service.latest_signal.size:
            self.live_curve.setData(self.service.latest_signal)
        if len(pulses) > 1:
            amplitudes = np.abs([pulse.peak for pulse in pulses])
            counts, edges = np.histogram(amplitudes, bins=min(64, max(8, len(amplitudes))))
            self.spectrum_curve.setData(edges, counts)

    def import_recording(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, self.t("choose_file"), filter="Recordings (*.pdet *.msgp *.pkl)")
        if not filename: return
        path = Path(filename)
        trusted = False
        if path.suffix == ".pkl":
            answer = QtWidgets.QMessageBox.warning(self, self.t("choose_file"), self.t("pickle_warning"), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            trusted = answer == QtWidgets.QMessageBox.Yes
        try:
            recording = load_recording(path, trusted_pickle=trusted, profile=self.profile.currentText())
            self.records_status.setText(f"{len(recording.pulses)} pulses · {recording.profile} · {recording.sample_rate} Hz")
            self.records_list.addItem(str(path))
            if recording.pulses:
                amplitudes = np.abs([pulse.peak for pulse in recording.pulses])
                counts, edges = np.histogram(amplitudes, bins=min(64, max(8, len(amplitudes))))
                self.spectrum_curve.setData(edges, counts)
        except Exception as error:
            self.records_status.setText(str(error))


def main():
    app = QtWidgets.QApplication(sys.argv); app.setStyle("Fusion")
    window = MainWindow(); window.show(); return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
