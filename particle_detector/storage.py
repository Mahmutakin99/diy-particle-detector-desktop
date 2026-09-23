"""Portable MessagePack sessions and explicitly trusted legacy imports."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import msgpack

from .model import Calibration, Pulse, Recording, now_iso


def encode_pdet(recording: Recording) -> bytes:
    data = {
        "format": "pdet", "version": 1,
        "session": {
            "started_at": recording.started_at,
            "sample_rate": recording.sample_rate,
            "profile": recording.profile,
            "lost_samples": recording.lost_samples,
            "calibration": recording.calibration.points if recording.calibration else None,
        },
        "pulses": [
            {"timestamp_us": p.timestamp_us, "peak": p.peak, "waveform": p.waveform}
            for p in recording.pulses
        ],
    }
    return msgpack.packb(data, use_bin_type=True)


def decode_pdet(raw: bytes) -> Recording:
    data = msgpack.unpackb(raw, raw=False)
    if not isinstance(data, dict) or data.get("format") != "pdet":
        raise ValueError("Not a .pdet recording")
    if data.get("version") != 1:
        raise ValueError("Unsupported .pdet version")
    header = data["session"]
    calibration = Calibration([tuple(p) for p in header["calibration"]]) if header.get("calibration") else None
    return Recording(
        header["profile"], int(header["sample_rate"]), header["started_at"],
        [Pulse(int(p["timestamp_us"]), float(p["peak"]), list(p.get("waveform", []))) for p in data["pulses"]],
        calibration, int(header.get("lost_samples", 0)),
    )


def save_pdet(path: Path, recording: Recording) -> None:
    """Atomically replace the destination so a failed save keeps the old file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".pdet-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encode_pdet(recording))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _unix_us(value) -> int:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1_000_000)
    if isinstance(value, str):
        return _unix_us(datetime.fromisoformat(value.replace("Z", "+00:00")))
    return int(float(value) * 1_000_000)


def import_legacy_msgp(raw: bytes, profile: str, sample_rate: int) -> Recording:
    rows = msgpack.unpackb(raw, raw=False)
    if not isinstance(rows, list):
        raise ValueError("Expected legacy MessagePack pulse list")
    pulses = []
    for row in rows:
        waveform = list(row["pulse"])
        if not waveform:
            continue
        pulses.append(Pulse(int(row["ts"]) * 1000, float(min(waveform)), waveform))
    return Recording(profile, sample_rate, now_iso(), pulses)


def import_trusted_pickle(path: Path, *, trusted: bool, profile: str = "electron", sample_rate: int = 48000) -> Recording:
    if not trusted:
        raise PermissionError("Pickle can run arbitrary code. Import only a trusted local file.")
    import pandas as pd

    rows = pd.read_pickle(path)  # caller explicitly accepts execution risk
    columns = set(rows.columns)
    if {"ts", "pulse"} <= columns:
        time_key, wave_key, peak_key = "ts", "pulse", None
    elif {"timestamp", "waveform", "peak"} <= columns:
        time_key, wave_key, peak_key = "timestamp", "waveform", "peak"
    else:
        raise ValueError("Unsupported legacy pickle columns")
    pulses = []
    for _, row in rows.iterrows():
        waveform = [float(x) for x in row[wave_key]]
        peak = float(row[peak_key]) if peak_key else float(min(waveform))
        pulses.append(Pulse(_unix_us(row[time_key]), peak, waveform))
    return Recording(profile, sample_rate, now_iso(), pulses)


def load_recording(path: Path, *, trusted_pickle: bool = False, profile: str = "electron", sample_rate: int = 48000) -> Recording:
    path = Path(path)
    if path.suffix == ".pdet":
        return decode_pdet(path.read_bytes())
    if path.suffix == ".msgp":
        return import_legacy_msgp(path.read_bytes(), profile, sample_rate)
    if path.suffix == ".pkl":
        return import_trusted_pickle(path, trusted=trusted_pickle, profile=profile, sample_rate=sample_rate)
    raise ValueError("Unsupported recording format")
