from datetime import datetime, timezone

import msgpack
import numpy as np
import pytest

from particle_detector.model import Calibration, Pulse, Recording
from particle_detector.storage import decode_pdet, encode_pdet, import_legacy_msgp, import_trusted_pickle
from particle_detector.signal import PulseDetector, PROFILES


def test_pdet_round_trip_and_version_gate():
    session = Recording("alpha", 48000, "2026-09-23T10:00:00Z", [Pulse(1000, -1200, [0, -1200, 0])], Calibration([(1000, 5000), (2000, 6000)]))
    restored = decode_pdet(encode_pdet(session))
    assert restored == session
    assert restored.calibration.energy_kev(1500) == 5500
    raw = msgpack.unpackb(encode_pdet(session))
    raw["version"] = 2
    with pytest.raises(ValueError, match="version"):
        decode_pdet(msgpack.packb(raw))


def test_calibration_requires_distinct_reference_points():
    with pytest.raises(ValueError):
        Calibration([(100, 1000), (100, 2000)])


def test_legacy_msgp_milliseconds_and_waveforms():
    source = msgpack.packb([{"ts": 1_700_000_000_000, "pulse": [0, -500, 0]}])
    recording = import_legacy_msgp(source, "electron", 48000)
    assert recording.pulses[0].timestamp_us == 1_700_000_000_000_000
    assert recording.pulses[0].peak == -500


def test_legacy_pickle_both_dataframe_shapes(tmp_path):
    pd = pytest.importorskip("pandas")
    old = tmp_path / "old.pkl"
    pd.DataFrame([{"ts": datetime(2020, 1, 1, tzinfo=timezone.utc), "ptype": "beta", "pulse": np.array([0, -500, 0])}]).to_pickle(old)
    modern = tmp_path / "modern.pkl"
    pd.DataFrame([{"timestamp": datetime(2020, 1, 1, tzinfo=timezone.utc), "peak": -700.0, "type": "beta", "waveform": np.array([0, -700, 0])}]).to_pickle(modern)
    assert import_trusted_pickle(old, trusted=True).pulses[0].peak == -500
    assert import_trusted_pickle(modern, trusted=True).pulses[0].peak == -700
    with pytest.raises(PermissionError):
        import_trusted_pickle(old, trusted=False)


@pytest.mark.parametrize("profile", ["electron", "alpha"])
def test_detects_two_pulses_across_chunks_without_double_count(profile):
    detector = PulseDetector(profile, 48000, threshold=-200, filter_enabled=False)
    signal = np.zeros(1200, dtype=np.float32)
    signal[200:205] = [-100, -400, -900, -400, -100]
    signal[800:805] = [-100, -400, -1100, -400, -100]
    events = detector.process(signal[:600], 0) + detector.process(signal[600:], 12_500)
    assert len(events) == 2
    assert events[0].peak == -900
    assert PROFILES[profile].window_samples > 0


def test_reports_missing_samples():
    detector = PulseDetector("electron", 48000, threshold=-200, filter_enabled=False)
    detector.process(np.zeros(480, dtype=np.float32), 0)
    detector.process(np.zeros(480, dtype=np.float32), 20_000)
    assert detector.lost_samples >= 400
