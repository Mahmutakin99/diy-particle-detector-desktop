import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from particle_detector.app import MainWindow


def test_desktop_has_live_and_analysis_visualizations():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.live_plot is not None
    assert window.spectrum_plot is not None
    assert window.records_list is not None
    window.close()
